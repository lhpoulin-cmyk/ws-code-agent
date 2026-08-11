"""Tests for the bounded Task 7 read-only repository executor spine."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.readonly_executor import (  # noqa: E402
    CompareStatus,
    ExecutorFact,
    ExecutorOperationError,
    ReadOnlyExecutor,
)


def git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def commit_all(root: Path, message: str) -> None:
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Calibration Test",
        "-c",
        "user.email=calibration@example.invalid",
        "commit",
        "-m",
        message,
    )


def create_repository(root: Path) -> None:
    git(root, "init", "-q")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("needle = 'base'\n", encoding="utf-8")
    (root / "README.md").write_text("Synthetic repository\n", encoding="utf-8")
    (root / "operator.txt").write_text("operator base\n", encoding="utf-8")
    commit_all(root, "initial")


class ReadOnlyExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "synthetic-repository"
        self.root.mkdir()
        create_repository(self.root)
        self.executor = ReadOnlyExecutor()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def observe(self):
        return self.executor.observe_repository(self.root).snapshot

    def test_clean_snapshot_is_stable_and_observation_is_non_mutating(self) -> None:
        before_status = git(self.root, "status", "--porcelain=v1").stdout
        first = self.observe()
        second = self.observe()
        self.assertEqual(first.snapshot_identity, second.snapshot_identity)
        self.assertEqual(before_status, git(self.root, "status", "--porcelain=v1").stdout)
        self.assertEqual("executor", self.executor.observe_repository(self.root).fact.origin)

    def test_head_change_changes_snapshot_and_compare_is_stale(self) -> None:
        snapshot = self.observe()
        (self.root / "README.md").write_text("Changed commit\n", encoding="utf-8")
        commit_all(self.root, "change head")
        current = self.observe()
        self.assertNotEqual(snapshot.head_commit, current.head_commit)
        self.assertNotEqual(snapshot.snapshot_identity, current.snapshot_identity)
        self.assertEqual(CompareStatus.STALE, self.executor.compare_snapshot(snapshot).status)

    def test_tracked_worktree_change_changes_snapshot_without_head_change(self) -> None:
        snapshot = self.observe()
        (self.root / "src" / "app.py").write_text("needle = 'dirty'\n", encoding="utf-8")
        current = self.observe()
        self.assertEqual(snapshot.head_commit, current.head_commit)
        self.assertNotEqual(snapshot.tracked_worktree_identity, current.tracked_worktree_identity)
        self.assertNotEqual(snapshot.snapshot_identity, current.snapshot_identity)

    def test_staged_index_change_changes_snapshot_without_head_change(self) -> None:
        snapshot = self.observe()
        (self.root / "operator.txt").write_text("staged operator work\n", encoding="utf-8")
        git(self.root, "add", "operator.txt")
        current = self.observe()
        self.assertEqual(snapshot.head_commit, current.head_commit)
        self.assertNotEqual(snapshot.index_identity, current.index_identity)
        self.assertNotEqual(snapshot.snapshot_identity, current.snapshot_identity)

    def test_untracked_creation_content_change_and_removal_change_snapshot(self) -> None:
        base = self.observe()
        draft = self.root / "draft.txt"
        draft.write_text("first\n", encoding="utf-8")
        created = self.observe()
        draft.write_text("second\n", encoding="utf-8")
        changed = self.observe()
        draft.unlink()
        removed = self.observe()
        self.assertNotEqual(base.untracked_identity, created.untracked_identity)
        self.assertNotEqual(created.untracked_identity, changed.untracked_identity)
        self.assertNotEqual(changed.untracked_identity, removed.untracked_identity)

    def test_c03_dirty_operator_state_survives_read_only_operations_byte_for_byte(self) -> None:
        """C03 pressure: staged and untracked operator state remain untouched."""
        (self.root / "operator.txt").write_bytes(b"operator staged revision\n")
        git(self.root, "add", "operator.txt")
        draft = self.root / "operator-draft.txt"
        draft.write_bytes(b"untracked operator draft\n")
        staged_before = (self.root / "operator.txt").read_bytes()
        draft_before = draft.read_bytes()
        status_before = git(self.root, "status", "--porcelain=v1").stdout
        snapshot = self.observe()
        self.executor.read_file(snapshot, "src/app.py")
        self.executor.search(snapshot, "needle", scope="src", result_limit=5)
        self.assertEqual(staged_before, (self.root / "operator.txt").read_bytes())
        self.assertEqual(draft_before, draft.read_bytes())
        self.assertEqual(status_before, git(self.root, "status", "--porcelain=v1").stdout)
        self.assertEqual(CompareStatus.MATCH, self.executor.compare_snapshot(snapshot).status)

    def test_c04_external_mutation_produces_stale(self) -> None:
        """C04 pressure: X followed by external X-prime is observed as stale."""
        snapshot_x = self.observe()
        (self.root / "README.md").write_text("External mutation creates X prime\n", encoding="utf-8")
        comparison = self.executor.compare_snapshot(snapshot_x)
        self.assertEqual(CompareStatus.STALE, comparison.status)
        self.assertTrue(comparison.fact.success)

    def test_read_file_bound_to_stale_snapshot_returns_no_new_content(self) -> None:
        """A READ_FILE fact for X must never carry bytes from external X-prime."""
        snapshot_x = self.observe()
        target = self.root / "src" / "app.py"
        target.write_text("needle = 'external X prime'\n", encoding="utf-8")

        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.read_file(snapshot_x, "src/app.py")

        self.assertEqual("STATE_STALE", raised.exception.fact.error_classification)
        self.assertNotIn("content_sha256", raised.exception.fact.observed_result)
        self.assertEqual("needle = 'external X prime'\n", target.read_text(encoding="utf-8"))

    def test_search_bound_to_stale_snapshot_returns_no_new_matches(self) -> None:
        """SEARCH against X fails rather than returning X-prime matches as X evidence."""
        snapshot_x = self.observe()
        target = self.root / "src" / "app.py"
        target.write_text("fresh-only-token = True\n", encoding="utf-8")

        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.search(snapshot_x, "fresh-only-token", scope="src")

        self.assertEqual("STATE_STALE", raised.exception.fact.error_classification)
        self.assertNotIn("matches", raised.exception.fact.observed_result)
        self.assertEqual("fresh-only-token = True\n", target.read_text(encoding="utf-8"))

    def test_read_file_denies_traversal_absolute_and_symlink_escape(self) -> None:
        snapshot = self.observe()
        self.assertEqual(b"needle = 'base'\n", self.executor.read_file(snapshot, "src/app.py").content)
        for attempted_path in ("../outside", os.fspath(Path("/tmp") / "outside")):
            with self.assertRaises(ExecutorOperationError) as raised:
                self.executor.read_file(snapshot, attempted_path)
            self.assertEqual("PATH_ESCAPE_DENIED", raised.exception.fact.error_classification)
        outside = Path(self.temporary_directory.name) / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        os.symlink(outside, self.root / "outside-link")
        snapshot = self.observe()
        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.read_file(snapshot, "outside-link")
        self.assertEqual("PATH_ESCAPE_DENIED", raised.exception.fact.error_classification)

    def test_read_distinguishes_bounded_absence_non_regular_and_escape(self) -> None:
        snapshot = self.observe()
        self.assertEqual(b"needle = 'base'\n", self.executor.read_file(snapshot, "src/app.py").content)
        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.read_file(snapshot, "src/missing.py")
        self.assertEqual("PATH_NOT_FOUND", raised.exception.fact.error_classification)
        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.read_file(snapshot, "src")
        self.assertEqual("NOT_A_REGULAR_FILE", raised.exception.fact.error_classification)

        outside = Path(self.temporary_directory.name) / "outside-directory"
        outside.mkdir()
        os.symlink(outside, self.root / "parent-link")
        os.symlink("missing-target", self.root / "dangling-link")
        snapshot = self.observe()
        for attempted_path in (
            "../outside",
            os.fspath(Path("/tmp") / "outside"),
            "parent-link/missing.py",
            "dangling-link",
            ".git/config",
        ):
            with self.assertRaises(ExecutorOperationError) as raised:
                self.executor.read_file(snapshot, attempted_path)
            self.assertEqual("PATH_ESCAPE_DENIED", raised.exception.fact.error_classification)

    def test_search_is_local_literal_bounded_and_denies_escape(self) -> None:
        snapshot = self.observe()
        (self.root / "src" / "second.py").write_text("needle = 'second'\n", encoding="utf-8")
        snapshot = self.observe()
        result = self.executor.search(snapshot, "needle", scope="src", result_limit=1)
        self.assertEqual(1, len(result.matches))
        self.assertTrue(result.matches[0].relative_path.startswith("src/"))
        self.assertEqual("executor", result.fact.origin)
        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.search(snapshot, "needle", scope="../", result_limit=1)
        self.assertEqual("PATH_ESCAPE_DENIED", raised.exception.fact.error_classification)
        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.search(snapshot, "", scope="src")
        self.assertEqual("MALFORMED_SEARCH_REQUEST", raised.exception.fact.error_classification)

    def test_search_distinguishes_missing_non_directory_and_escape_scope(self) -> None:
        snapshot = self.observe()
        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.search(snapshot, "needle", scope="missing")
        self.assertEqual("SEARCH_SCOPE_NOT_FOUND", raised.exception.fact.error_classification)
        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.search(snapshot, "needle", scope="README.md")
        self.assertEqual("SEARCH_SCOPE_NOT_DIRECTORY", raised.exception.fact.error_classification)

        outside = Path(self.temporary_directory.name) / "search-outside"
        outside.mkdir()
        os.symlink(outside, self.root / "search-link")
        snapshot = self.observe()
        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.search(snapshot, "needle", scope="search-link")
        self.assertEqual("PATH_ESCAPE_DENIED", raised.exception.fact.error_classification)

    def test_repository_replacement_at_same_path_changes_identity(self) -> None:
        original = self.observe()
        shutil.rmtree(self.root / ".git")
        (self.root / "src" / "app.py").write_text("replacement = True\n", encoding="utf-8")
        git(self.root, "init", "-q")
        commit_all(self.root, "replacement")
        replacement = self.observe()
        self.assertNotEqual(original.repository_identity, replacement.repository_identity)
        self.assertEqual(CompareStatus.STALE, self.executor.compare_snapshot(original).status)

    def test_empty_repository_returns_executor_error_fact(self) -> None:
        empty = Path(self.temporary_directory.name) / "empty-repository"
        empty.mkdir()
        git(empty, "init", "-q")
        with self.assertRaises(ExecutorOperationError) as raised:
            self.executor.observe_repository(empty)
        self.assertFalse(raised.exception.fact.success)
        self.assertEqual("GIT_COMMAND_FAILED", raised.exception.fact.error_classification)

    def test_executor_fact_cannot_be_constructed_as_model_origin(self) -> None:
        fact = ExecutorFact(operation="OBSERVE_REPOSITORY", success=True, observed_result={})
        self.assertEqual("executor", fact.origin)
        with self.assertRaises(TypeError):
            ExecutorFact(operation="MODEL", success=True, observed_result={}, origin="model")


if __name__ == "__main__":
    unittest.main()
