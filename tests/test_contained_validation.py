"""Real systemd containment checks; skipped only where the fixed host gate is absent."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch as mock_patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.contained_validation import ContainmentUnavailable, ORACLE_SOURCE, ORACLE_STAGE_ROOT, SystemdContainedValidationRunner, WRAPPER
from ws_code_agent.isolated_patch import IsolatedPatchExecutor, PatchProposal
from ws_code_agent.readonly_executor import ReadOnlyExecutor
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationDescriptor, ValidationRole, ValidationStatus


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


@unittest.skipUnless(WRAPPER.is_file() and ORACLE_SOURCE.is_file(), "fixed Task 10A containment host gate unavailable")
class ContainedValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ws-code-agent-isolated-")
        self.root = Path(self.tmp.name) / "repository"
        self.root.mkdir(); git(self.root, "init", "-q")
        (self.root / "src").mkdir(); (self.root / "tests").mkdir()
        (self.root / "src" / "parity.py").write_text("def is_even(number: int) -> bool:\n    return number % 2 == 1\n", encoding="utf-8")
        (self.root / "tests" / "test_parity.py").write_text(
            "import errno, os, socket, unittest\nfrom pathlib import Path\nfrom src.parity import is_even\n"
            "class ContainedC01(unittest.TestCase):\n"
            " def test_c01_and_boundaries(self):\n"
            "  self.assertTrue(is_even(2)); self.assertFalse(is_even(3))\n"
            "  s=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.close()\n"
            "  for f in (socket.AF_INET, socket.AF_INET6):\n"
            "   with self.assertRaises(OSError) as e: socket.socket(f, socket.SOCK_STREAM)\n"
            "   self.assertEqual(errno.EAFNOSUPPORT, e.exception.errno)\n"
            "  for p in ('/home/louis/lab-root-trust','/home/louis/.local/share/ws-code-agent/alpha-private','/home/louis/src/ws-code-agent'):\n"
            "   with self.assertRaises(OSError): os.stat(p)\n"
            "  with self.assertRaises(OSError): Path('write-sentinel').write_text('x')\n",
            encoding="utf-8",
        )
        git(self.root, "add", "."); git(self.root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "initial")
        self.observer, self.patcher = ReadOnlyExecutor(), IsolatedPatchExecutor()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _prepared(self):
        x = self.observer.observe_repository(self.root).snapshot
        context = self.patcher.build_isolated_copy(x)
        patch = b"diff --git a/src/parity.py b/src/parity.py\n--- a/src/parity.py\n+++ b/src/parity.py\n@@ -1,2 +1,2 @@\n def is_even(number: int) -> bool:\n-    return number % 2 == 1\n+    return number % 2 == 0\n"
        applied = self.patcher.apply_patch_isolated(context, PatchProposal.create(x, patch, ("src/parity.py",)), ("src/parity.py",))
        self.assertEqual("SUCCESS", applied.status.value)
        return x, context, applied.result_snapshot

    @staticmethod
    def _stage_names() -> set[Path]:
        return set(ORACLE_STAGE_ROOT.glob("run-*")) if ORACLE_STAGE_ROOT.exists() else set()

    def _synthetic_oracle(self, body: str) -> Path:
        oracle = Path(self.tmp.name) / "synthetic-private-oracle.py"
        oracle.write_text(body, encoding="utf-8")
        return oracle

    @staticmethod
    def _oracle_descriptor(oracle: Path, timeout: float = 10) -> ValidationDescriptor:
        return ValidationDescriptor(
            "C01-oracle", "v1", "/usr/bin/python3", ("-B", str(oracle)), ".", timeout,
            ValidationRole.HIDDEN_ORACLE, True, containment_required=True,
        )

    def test_c01_visible_and_hidden_oracle_are_contained(self) -> None:
        x, context, y = self._prepared()
        stages_before = self._stage_names()
        try:
            visible = ValidationDescriptor("C01-visible", "v1", "/usr/bin/python3", ("-B", "-m", "unittest", "discover", "-s", "tests"), ".", 10, ValidationRole.VISIBLE, True, containment_required=True)
            hidden = ValidationDescriptor("C01-oracle", "v1", "/usr/bin/python3", ("-B", str(ORACLE_SOURCE)), ".", 10, ValidationRole.HIDDEN_ORACLE, True, containment_required=True)
            executor = DescriptorValidationExecutor({"C01-visible": visible, "C01-oracle": hidden}, self.observer, SystemdContainedValidationRunner())
            visible_run = executor.run_validation(context, y, "C01-visible", ("C01-visible",))
            self.assertEqual(ValidationStatus.VALIDATION_PASS, visible_run.status, visible_run.stderr)
            self.assertEqual("systemd-transient", visible_run.containment_evidence["CONTAINMENT_MECHANISM"])
            self.assertEqual("AF_UNIX_ONLY;PrivateNetwork=yes", visible_run.containment_evidence["CONTAINMENT_NETWORK"])
            hidden_run = executor.run_validation(context, y, "C01-oracle", ("C01-oracle",))
            self.assertEqual(ValidationStatus.VALIDATION_PASS, hidden_run.status, hidden_run.stderr)
            self.assertEqual("single-artifact-directory", hidden_run.containment_evidence["CONTAINMENT_ORACLE_PROJECTION"])
            self.assertEqual(64, len(hidden_run.containment_evidence["CONTAINMENT_ORACLE_SHA256"]))
            self.assertEqual(x.snapshot_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
        finally:
            self.patcher.cleanup(context)
        stages_after = self._stage_names()
        self.assertEqual(stages_before, stages_after)

    def test_hidden_oracle_projection_is_single_artifact_and_private_paths_are_hidden(self) -> None:
        _, context, y = self._prepared()
        oracle = self._synthetic_oracle(
            "import errno, os, socket\n"
            "from pathlib import Path\n"
            "assert [item.name for item in Path('/run/ws-code-agent/oracle').iterdir()] == ['oracle.py']\n"
            "assert Path('/run/ws-code-agent/oracle/oracle.py').is_file()\n"
            "for path in ('/home/louis/.local/share/ws-code-agent/alpha-private', '/home/louis/lab-root-trust', '/home/louis/src/ws-code-agent'):\n"
            " try: os.stat(path)\n"
            " except OSError: pass\n"
            " else: raise AssertionError(path)\n"
            "socket.socket(socket.AF_UNIX, socket.SOCK_STREAM).close()\n"
            "for family in (socket.AF_INET, socket.AF_INET6):\n"
            " try: socket.socket(family, socket.SOCK_STREAM)\n"
            " except OSError as error: assert error.errno == errno.EAFNOSUPPORT\n"
            " else: raise AssertionError(family)\n",
        )
        stages_before = self._stage_names()
        try:
            descriptor = self._oracle_descriptor(oracle)
            run = DescriptorValidationExecutor({"C01-oracle": descriptor}, self.observer, SystemdContainedValidationRunner(oracle_source=oracle)).run_validation(context, y, "C01-oracle", ("C01-oracle",))
            self.assertEqual(ValidationStatus.VALIDATION_PASS, run.status, run.stderr)
        finally:
            self.patcher.cleanup(context)
        self.assertEqual(stages_before, self._stage_names())

    def test_oracle_stage_cleanup_after_failure_timeout_and_launcher_error(self) -> None:
        _, context, y = self._prepared()
        stages_before = self._stage_names()
        try:
            failed = self._synthetic_oracle("raise SystemExit(7)\n")
            descriptor = self._oracle_descriptor(failed)
            run = DescriptorValidationExecutor({"C01-oracle": descriptor}, self.observer, SystemdContainedValidationRunner(oracle_source=failed)).run_validation(context, y, "C01-oracle", ("C01-oracle",))
            self.assertEqual(ValidationStatus.VALIDATION_FAIL, run.status, run.stderr)
            self.assertEqual(stages_before, self._stage_names())

            timed_out = self._synthetic_oracle("import time\ntime.sleep(30)\n")
            descriptor = self._oracle_descriptor(timed_out, timeout=0.3)
            run = DescriptorValidationExecutor({"C01-oracle": descriptor}, self.observer, SystemdContainedValidationRunner(oracle_source=timed_out)).run_validation(context, y, "C01-oracle", ("C01-oracle",))
            self.assertEqual(ValidationStatus.VALIDATION_TIMEOUT, run.status, run.stderr)
            self.assertEqual(stages_before, self._stage_names())

            launcher_error = self._synthetic_oracle("raise SystemExit(0)\n")
            descriptor = self._oracle_descriptor(launcher_error)
            with mock_patch("ws_code_agent.contained_validation.subprocess.run", side_effect=OSError("launcher unavailable")):
                with self.assertRaises(ContainmentUnavailable):
                    SystemdContainedValidationRunner(oracle_source=launcher_error).run(context, descriptor)
            self.assertEqual(stages_before, self._stage_names())
        finally:
            self.patcher.cleanup(context)

    def test_contained_timeout_reaps_descendant_and_collects_unit(self) -> None:
        (self.root / "tests" / "test_timeout.py").write_text(
            "import subprocess,sys,time,unittest\n"
            "class Timeout(unittest.TestCase):\n"
            " def test_timeout(self):\n"
            "  child=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(30)'])\n"
            "  print(f'CHILD_PID={child.pid}', flush=True); time.sleep(30)\n",
            encoding="utf-8",
        )
        git(self.root, "add", "."); git(self.root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "timeout")
        x = self.observer.observe_repository(self.root).snapshot; context = self.patcher.build_isolated_copy(x)
        patch = b"diff --git a/src/parity.py b/src/parity.py\n--- a/src/parity.py\n+++ b/src/parity.py\n@@ -1,2 +1,2 @@\n def is_even(number: int) -> bool:\n-    return number % 2 == 1\n+    return number % 2 == 0\n"
        applied = self.patcher.apply_patch_isolated(context, PatchProposal.create(x, patch, ("src/parity.py",)), ("src/parity.py",))
        descriptor = ValidationDescriptor("C01-visible", "v1", "/usr/bin/python3", ("-B", "-m", "unittest", "discover", "-s", "tests"), ".", 0.3, ValidationRole.VISIBLE, True, containment_required=True)
        try:
            run = DescriptorValidationExecutor({"C01-visible": descriptor}, self.observer, SystemdContainedValidationRunner()).run_validation(context, applied.result_snapshot, "C01-visible", ("C01-visible",))
            self.assertEqual(ValidationStatus.VALIDATION_TIMEOUT, run.status, run.stderr)
            child = int(next(line.split("=", 1)[1] for line in run.stdout.splitlines() if line.startswith("CHILD_PID=")))
            deadline = time.monotonic() + 2
            while Path(f"/proc/{child}").exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertFalse(Path(f"/proc/{child}").exists())
            unit = subprocess.run(["systemctl", "show", run.containment_evidence["CONTAINMENT_UNIT"], "--property=LoadState"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual("LoadState=not-found", unit.stdout.strip())
        finally:
            self.patcher.cleanup(context)
