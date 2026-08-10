"""Task 8 isolated patch tests; all authoritative repositories are temporary."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.isolated_patch import ApplicationStatus, IsolatedPatchExecutor, PatchProposal  # noqa: E402
from ws_code_agent.readonly_executor import ReadOnlyExecutor  # noqa: E402


def git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *arguments], text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True)


def commit_all(root: Path, message: str) -> None:
    git(root, "add", ".")
    git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", message)


def make_repo(root: Path, value: str = "base") -> None:
    git(root, "init", "-q")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text(f"value = '{value}'\n", encoding="utf-8")
    (root / "operator.txt").write_text("operator base\n", encoding="utf-8")
    commit_all(root, "initial")


def patch(path: str, old: str, new: str) -> bytes:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    ).encode()


class IsolatedPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "source"
        self.root.mkdir()
        make_repo(self.root)
        self.observer = ReadOnlyExecutor()
        self.executor = IsolatedPatchExecutor(self.observer)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def proposal(self, snapshot, content: bytes, paths=("src/app.py",)):
        return PatchProposal.create(snapshot, content, tuple(paths))

    def test_success_isolated_and_authoritative_source_is_unchanged(self) -> None:
        source_x = self.observer.observe_repository(self.root).snapshot
        proposal = self.proposal(source_x, patch("src/app.py", "value = 'base'", "value = 'patched'"))
        context = self.executor.build_isolated_copy(source_x)
        self.assertNotIn(Path(context.isolated_root), self.root.parents)
        self.assertNotIn(self.root.resolve(), Path(context.isolated_root).resolve().parents)
        result = self.executor.apply_patch_isolated(context, proposal, ("src/app.py",))
        self.assertEqual(ApplicationStatus.SUCCESS, result.status)
        self.assertEqual(("src/app.py",), result.actual_changed_paths)
        self.assertNotEqual(context.initial_snapshot.snapshot_identity, result.result_snapshot.snapshot_identity)
        self.assertEqual(source_x.snapshot_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
        self.assertEqual("value = 'base'\n", (self.root / "src" / "app.py").read_text())
        self.executor.cleanup(context)
        self.assertFalse(Path(context.workspace_root).exists())

    def test_c01_patch_applies_only_in_temporary_copy_without_validation(self) -> None:
        fixture = Path(__file__).resolve().parents[1] / "benchmarks/alpha-calibration/cases/C01-simple-patch/target"
        shutil.copytree(fixture, self.root / "c01")
        c01 = self.root / "c01"
        git(c01, "init", "-q")
        commit_all(c01, "c01 baseline")
        source_x = self.observer.observe_repository(c01).snapshot
        proposal = PatchProposal.create(
            source_x,
            b"diff --git a/src/parity.py b/src/parity.py\n"
            b"--- a/src/parity.py\n"
            b"+++ b/src/parity.py\n"
            b"@@ -1,3 +1,3 @@\n"
            b" def is_even(number: int) -> bool:\n"
            b"     \"\"\"Return whether number is even.\"\"\"\n"
            b"-    return number % 2 == 1\n"
            b"+    return number % 2 == 0\n",
            ("src/parity.py",),
        )
        context = self.executor.build_isolated_copy(source_x)
        result = self.executor.apply_patch_isolated(context, proposal, ("src/parity.py",))
        self.assertEqual(ApplicationStatus.SUCCESS, result.status)
        self.assertEqual("    return number % 2 == 1\n", (c01 / "src/parity.py").read_text().splitlines(True)[2])
        self.assertEqual(source_x.snapshot_identity, self.observer.observe_repository(c01).snapshot.snapshot_identity)
        self.executor.cleanup(context)

    def test_stale_source_blocks_application_without_isolated_patch(self) -> None:
        source_x = self.observer.observe_repository(self.root).snapshot
        context = self.executor.build_isolated_copy(source_x)
        (self.root / "operator.txt").write_text("external drift\n", encoding="utf-8")
        proposal = self.proposal(source_x, patch("src/app.py", "value = 'base'", "value = 'patched'"))
        result = self.executor.apply_patch_isolated(context, proposal, ("src/app.py",))
        self.assertEqual(ApplicationStatus.STATE_STALE, result.status)
        self.assertEqual(context.initial_snapshot.snapshot_identity, self.observer.observe_repository(context.isolated_root).snapshot.snapshot_identity)
        self.executor.cleanup(context)

    def test_scope_traversal_absolute_and_multi_file_denials_leave_copy_unchanged(self) -> None:
        source_x = self.observer.observe_repository(self.root).snapshot
        context = self.executor.build_isolated_copy(source_x)
        cases = [
            (patch("src/app.py", "value = 'base'", "value = 'patched'") + patch("operator.txt", "operator base", "bad"), ("src/app.py",), ApplicationStatus.PATH_SCOPE_DENIED),
            (patch("../escape", "x", "y"), ("../escape",), ApplicationStatus.PATH_ESCAPE_DENIED),
            (patch("/tmp/escape", "x", "y"), ("/tmp/escape",), ApplicationStatus.PATH_ESCAPE_DENIED),
        ]
        for content, paths, status in cases:
            result = self.executor.apply_patch_isolated(context, self.proposal(source_x, content, paths), paths)
            self.assertEqual(status, result.status)
            self.assertEqual(context.initial_snapshot.snapshot_identity, self.observer.observe_repository(context.isolated_root).snapshot.snapshot_identity)
            self.assertEqual(source_x.snapshot_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
        self.executor.cleanup(context)

    def test_header_target_mismatch_is_denied_before_patch_application(self) -> None:
        """The actual +++ target, not an allowed diff header, controls scope."""
        source_x = self.observer.observe_repository(self.root).snapshot
        context = self.executor.build_isolated_copy(source_x)
        mismatched = (
            b"diff --git a/src/app.py b/src/app.py\n"
            b"--- a/src/app.py\n"
            b"+++ b/operator.txt\n"
            b"@@ -1 +1 @@\n"
            b"-operator base\n"
            b"+forbidden change\n"
        )
        proposal = self.proposal(source_x, mismatched, ("operator.txt",))
        result = self.executor.apply_patch_isolated(context, proposal, ("src/app.py",))
        self.assertEqual(ApplicationStatus.PATCH_REJECTED, result.status)
        self.assertIn("supported diff header", result.fact.observed_result["detail"])
        self.assertEqual(
            context.initial_snapshot.snapshot_identity,
            self.observer.observe_repository(context.isolated_root).snapshot.snapshot_identity,
        )
        self.assertEqual(source_x.snapshot_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
        self.executor.cleanup(context)

    def test_symlink_escape_and_context_mismatch_are_rejected(self) -> None:
        outside = Path(self.temporary.name) / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        os.symlink(outside, self.root / "src" / "link.py")
        commit_all(self.root, "symlink")
        source_x = self.observer.observe_repository(self.root).snapshot
        context = self.executor.build_isolated_copy(source_x)
        symlink_result = self.executor.apply_patch_isolated(context, self.proposal(source_x, patch("src/link.py", "outside", "changed"), ("src/link.py",)), ("src/link.py",))
        self.assertEqual(ApplicationStatus.SYMLINK_DENIED, symlink_result.status)
        bad = self.executor.apply_patch_isolated(context, self.proposal(source_x, patch("src/app.py", "not present", "patched")), ("src/app.py",))
        self.assertEqual(ApplicationStatus.PATCH_REJECTED, bad.status)
        self.assertEqual(context.initial_snapshot.snapshot_identity, self.observer.observe_repository(context.isolated_root).snapshot.snapshot_identity)
        self.executor.cleanup(context)

    def test_c03_dirty_index_and_untracked_state_reconstruct_and_survive_patch(self) -> None:
        (self.root / "operator.txt").write_bytes(b"staged operator work\n")
        git(self.root, "add", "operator.txt")
        draft = self.root / "operator-draft.txt"
        draft.write_bytes(b"untracked draft\n")
        source_x = self.observer.observe_repository(self.root).snapshot
        context = self.executor.build_isolated_copy(source_x)
        self.assertEqual(b"staged operator work\n", (Path(context.isolated_root) / "operator.txt").read_bytes())
        self.assertEqual(b"untracked draft\n", (Path(context.isolated_root) / "operator-draft.txt").read_bytes())
        result = self.executor.apply_patch_isolated(context, self.proposal(source_x, patch("src/app.py", "value = 'base'", "value = 'patched'")), ("src/app.py",))
        self.assertEqual(ApplicationStatus.SUCCESS, result.status)
        self.assertEqual(b"staged operator work\n", (Path(context.isolated_root) / "operator.txt").read_bytes())
        self.assertEqual(b"untracked draft\n", (Path(context.isolated_root) / "operator-draft.txt").read_bytes())
        self.assertEqual(source_x.snapshot_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
        self.executor.cleanup(context)

    def test_c05_proposal_cannot_cross_repository_context(self) -> None:
        other = Path(self.temporary.name) / "other"
        other.mkdir()
        make_repo(other, "other")
        source_a = self.observer.observe_repository(self.root).snapshot
        source_b = self.observer.observe_repository(other).snapshot
        context_b = self.executor.build_isolated_copy(source_b)
        proposal_a = self.proposal(source_a, patch("src/app.py", "value = 'base'", "value = 'patched'"))
        result = self.executor.apply_patch_isolated(context_b, proposal_a, ("src/app.py",))
        self.assertEqual(ApplicationStatus.REPOSITORY_MISMATCH, result.status)
        self.assertEqual(source_b.snapshot_identity, self.observer.observe_repository(other).snapshot.snapshot_identity)
        self.executor.cleanup(context_b)

    def test_malformed_patch_and_cleanup_after_rejection(self) -> None:
        source_x = self.observer.observe_repository(self.root).snapshot
        context = self.executor.build_isolated_copy(source_x)
        proposal = self.proposal(source_x, b"not a patch\n", ())
        result = self.executor.apply_patch_isolated(context, proposal, ())
        self.assertEqual(ApplicationStatus.PATCH_REJECTED, result.status)
        self.assertEqual(source_x.snapshot_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
        self.executor.cleanup(context)
        self.assertFalse(Path(context.workspace_root).exists())

    def test_executor_error_after_sandbox_creation_preserves_source_and_allows_cleanup(self) -> None:
        source_x = self.observer.observe_repository(self.root).snapshot
        context = self.executor.build_isolated_copy(source_x)
        (Path(context.isolated_root) / "src" / "app.py").write_text("tampered sandbox\n", encoding="utf-8")
        result = self.executor.apply_patch_isolated(
            context,
            self.proposal(source_x, patch("src/app.py", "value = 'base'", "value = 'patched'")),
            ("src/app.py",),
        )
        self.assertEqual(ApplicationStatus.EXECUTOR_ERROR, result.status)
        self.assertEqual(source_x.snapshot_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
        self.executor.cleanup(context)
        self.assertFalse(Path(context.workspace_root).exists())


if __name__ == "__main__":
    unittest.main()
