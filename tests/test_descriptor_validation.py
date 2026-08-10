from __future__ import annotations
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ws_code_agent.isolated_patch import IsolatedPatchExecutor, PatchProposal
from ws_code_agent.readonly_executor import ReadOnlyExecutor
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationDescriptor, ValidationRole, ValidationStatus

def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
def commit(root):
    git(root, "add", "."); git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "initial")
def patch(path, old, new):
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{old}\n+{new}\n".encode()

class DescriptorValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name) / "repo"; self.root.mkdir(); git(self.root, "init", "-q")
        (self.root / "src").mkdir(); (self.root / "src" / "app.py").write_text("value = 'base'\n"); (self.root / "check.py").write_text("print('ok')\n")
        (self.root / "fail.py").write_text("import sys\nprint('diagnostic', file=sys.stderr)\nsys.exit(3)\n")
        (self.root / "timeout.py").write_text("import time\ntime.sleep(2)\n")
        (self.root / "write.py").write_text("open('generated.txt', 'w').write('x')\n")
        commit(self.root)
        self.observer, self.patch_executor = ReadOnlyExecutor(), IsolatedPatchExecutor()
    def tearDown(self): self.tmp.cleanup()
    def prepared(self):
        x = self.observer.observe_repository(self.root).snapshot; context = self.patch_executor.build_isolated_copy(x)
        proposal = PatchProposal.create(x, patch("src/app.py", "value = 'base'", "value = 'patched'"), ("src/app.py",))
        applied = self.patch_executor.apply_patch_isolated(context, proposal, ("src/app.py",)); self.assertEqual("SUCCESS", applied.status.value)
        return x, context, applied.result_snapshot
    def descriptor(self, identifier="local", args=("-B", "check.py"), **kwargs):
        timeout = kwargs.pop("timeout_seconds", 1)
        return ValidationDescriptor(identifier, "v1", sys.executable, args, ".", timeout, ValidationRole.VISIBLE, True, **kwargs)
    def test_pass_fail_streams_unknown_and_wrong_snapshot(self):
        x, context, y = self.prepared(); good = self.descriptor(); executor = DescriptorValidationExecutor({"local": good})
        run = executor.run_validation(context, y, "local", ("local",)); self.assertEqual(ValidationStatus.VALIDATION_PASS, run.status); self.assertIn("ok", run.stdout)
        unknown = executor.run_validation(context, y, "other", ("other",)); self.assertEqual(ValidationStatus.EXECUTOR_ERROR, unknown.status)
        wrong = executor.run_validation(context, context.initial_snapshot, "local", ("local",)); self.assertEqual(ValidationStatus.EXECUTOR_ERROR, wrong.status)
        self.assertEqual(x.snapshot_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity); self.patch_executor.cleanup(context)
    def test_fail_stderr_unavailable_timeout_and_effect_violation(self):
        x, context, y = self.prepared(); root = Path(context.isolated_root)
        descriptors = {
            "fail": self.descriptor("fail", ("-B", "fail.py")),
            "missing": ValidationDescriptor("missing", "v1", "/no/such/executable", (), ".", 1, ValidationRole.VISIBLE, True),
            "timeout": self.descriptor("timeout", ("-B", "timeout.py"), timeout_seconds=0.05),
            "write": self.descriptor("write", ("-B", "write.py")),
        }; executor = DescriptorValidationExecutor(descriptors)
        failed = executor.run_validation(context, y, "fail", ("fail",)); self.assertEqual(ValidationStatus.VALIDATION_FAIL, failed.status); self.assertIn("diagnostic", failed.stderr)
        unavailable = executor.run_validation(context, y, "missing", ("missing",)); self.assertEqual(ValidationStatus.VALIDATION_UNAVAILABLE, unavailable.status)
        timeout = executor.run_validation(context, y, "timeout", ("timeout",)); self.assertEqual(ValidationStatus.VALIDATION_TIMEOUT, timeout.status)
        # Timeout/fail did not mutate Y; the write descriptor then proves exit 0 is not clean validation.
        effect = executor.run_validation(context, y, "write", ("write",)); self.assertEqual(ValidationStatus.EFFECT_VIOLATION, effect.status); self.assertTrue((root / "generated.txt").exists())
        self.assertEqual(x.snapshot_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity); self.patch_executor.cleanup(context)
    def test_c01_visible_and_hidden_oracle_pass_without_authoritative_mutation(self):
        fixture = Path(__file__).resolve().parents[1] / "benchmarks/alpha-calibration/cases/C01-simple-patch/target"; shutil.copytree(fixture, self.root / "c01"); root = self.root / "c01"; git(root, "init", "-q"); commit(root)
        x = self.observer.observe_repository(root).snapshot; context = self.patch_executor.build_isolated_copy(x)
        content = b'diff --git a/src/parity.py b/src/parity.py\n--- a/src/parity.py\n+++ b/src/parity.py\n@@ -1,3 +1,3 @@\n def is_even(number: int) -> bool:\n     """Return whether number is even."""\n-    return number % 2 == 1\n+    return number % 2 == 0\n'
        applied = self.patch_executor.apply_patch_isolated(context, PatchProposal.create(x, content, ("src/parity.py",)), ("src/parity.py",)); y = applied.result_snapshot
        oracle = Path.home() / ".local/share/ws-code-agent/alpha-private/C01-oracle.py"
        visible = self.descriptor("C01-visible", ("-B", "-m", "unittest", "discover", "-s", "tests"))
        hidden = ValidationDescriptor("C01-oracle", "v1", sys.executable, ("-B", str(oracle)), ".", 1, ValidationRole.HIDDEN_ORACLE, True, isolated_pythonpath=True)
        executor = DescriptorValidationExecutor({"C01-visible": visible, "C01-oracle": hidden})
        self.assertEqual(ValidationStatus.VALIDATION_PASS, executor.run_validation(context, y, "C01-visible", ("C01-visible",)).status)
        self.assertEqual(ValidationStatus.VALIDATION_PASS, executor.run_validation(context, y, "C01-oracle", ("C01-oracle",)).status)
        self.assertEqual(x.snapshot_identity, self.observer.observe_repository(root).snapshot.snapshot_identity); self.patch_executor.cleanup(context)

if __name__ == "__main__": unittest.main()
