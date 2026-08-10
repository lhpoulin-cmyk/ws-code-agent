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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.contained_validation import ORACLE_SOURCE, ORACLE_STAGE_ROOT, SystemdContainedValidationRunner, WRAPPER
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

    def test_c01_visible_and_hidden_oracle_are_contained(self) -> None:
        x, context, y = self._prepared()
        stages_before = set(ORACLE_STAGE_ROOT.glob("run-*")) if ORACLE_STAGE_ROOT.exists() else set()
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
        stages_after = set(ORACLE_STAGE_ROOT.glob("run-*")) if ORACLE_STAGE_ROOT.exists() else set()
        self.assertEqual(stages_before, stages_after)

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
