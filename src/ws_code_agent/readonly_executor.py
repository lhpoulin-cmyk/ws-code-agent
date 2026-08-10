"""Read-only Git working-tree observation with executor-originated evidence.

This module deliberately exposes no generic command, write, validation, network,
or Git-write operation. Fixed Git plumbing is an implementation detail used only
to observe a repository supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePath
import subprocess
from typing import Any, Mapping


COMPONENT_ID = "ws-code-agent-readonly-executor/v1"
SNAPSHOT_VERSION = "repository-snapshot/v1"
IGNORED_FILE_POLICY = "exclude-standard; ignored files are not represented in v1"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class RepositorySnapshot:
    """A deterministic v1 observation of a Git working tree.

    Ignored files are explicitly excluded under ``ignored_file_policy``. This is
    a deliberate v1 limitation, not a claim that ignored files are immaterial to
    every future task.
    """

    version: str
    repository_identity: str
    canonical_root: str
    git_common_dir: str
    head_commit: str
    branch: str
    index_identity: str
    tracked_worktree_identity: str
    untracked_inventory: tuple[tuple[str, str, str], ...]
    untracked_identity: str
    submodule_identity: str
    ignored_file_policy: str
    snapshot_identity: str

    def material_state(self) -> Mapping[str, Any]:
        return {
            "version": self.version,
            "repository_identity": self.repository_identity,
            "canonical_root": self.canonical_root,
            "git_common_dir": self.git_common_dir,
            "head_commit": self.head_commit,
            "branch": self.branch,
            "index_identity": self.index_identity,
            "tracked_worktree_identity": self.tracked_worktree_identity,
            "untracked_inventory": self.untracked_inventory,
            "untracked_identity": self.untracked_identity,
            "submodule_identity": self.submodule_identity,
            "ignored_file_policy": self.ignored_file_policy,
        }


@dataclass(frozen=True)
class ExecutorFact:
    """Evidence created only by this executor component.

    ``origin`` is fixed and cannot be supplied through the public constructor,
    preventing this type from representing model-originated content.
    """

    operation: str
    success: bool
    observed_result: Mapping[str, Any]
    snapshot_identity: str | None = None
    error_classification: str | None = None
    component: str = COMPONENT_ID
    origin: str = field(default="executor", init=False)


class ExecutorOperationError(RuntimeError):
    """Fail-closed operation error carrying executor-originated evidence."""

    def __init__(self, message: str, fact: ExecutorFact) -> None:
        super().__init__(message)
        self.fact = fact


class CompareStatus(str, Enum):
    MATCH = "MATCH"
    STALE = "STALE"
    ERROR = "ERROR"


@dataclass(frozen=True)
class ObservationResult:
    snapshot: RepositorySnapshot
    fact: ExecutorFact


@dataclass(frozen=True)
class CompareResult:
    status: CompareStatus
    expected_snapshot: RepositorySnapshot
    current_snapshot: RepositorySnapshot | None
    fact: ExecutorFact


@dataclass(frozen=True)
class ReadResult:
    relative_path: str
    content: bytes
    fact: ExecutorFact


@dataclass(frozen=True)
class SearchMatch:
    relative_path: str
    line_number: int
    line_text: str


@dataclass(frozen=True)
class SearchResult:
    matches: tuple[SearchMatch, ...]
    fact: ExecutorFact


class ReadOnlyExecutor:
    """The Task 7 bounded read-only operation surface."""

    def observe_repository(self, repository_root: str | os.PathLike[str]) -> ObservationResult:
        operation = "OBSERVE_REPOSITORY"
        try:
            root = self._repository_root(repository_root)
            snapshot = self._capture_snapshot(root)
        except ExecutorOperationError:
            raise
        except OSError as error:
            raise self._error(operation, "OBSERVATION_ERROR", str(error)) from error
        return ObservationResult(
            snapshot=snapshot,
            fact=self._fact(
                operation,
                True,
                {"repository_identity": snapshot.repository_identity,
                 "snapshot_identity": snapshot.snapshot_identity},
                snapshot.snapshot_identity,
            ),
        )

    def compare_snapshot(self, expected: RepositorySnapshot) -> CompareResult:
        operation = "COMPARE_SNAPSHOT"
        try:
            current = self.observe_repository(expected.canonical_root).snapshot
        except ExecutorOperationError as error:
            return CompareResult(
                status=CompareStatus.ERROR,
                expected_snapshot=expected,
                current_snapshot=None,
                fact=self._fact(
                    operation,
                    False,
                    {"expected_snapshot_identity": expected.snapshot_identity},
                    expected.snapshot_identity,
                    error.fact.error_classification or "OBSERVATION_ERROR",
                ),
            )
        status = (
            CompareStatus.MATCH
            if current.snapshot_identity == expected.snapshot_identity
            else CompareStatus.STALE
        )
        return CompareResult(
            status=status,
            expected_snapshot=expected,
            current_snapshot=current,
            fact=self._fact(
                operation,
                True,
                {
                    "expected_snapshot_identity": expected.snapshot_identity,
                    "current_snapshot_identity": current.snapshot_identity,
                    "status": status.value,
                },
                expected.snapshot_identity,
            ),
        )

    def read_file(self, snapshot: RepositorySnapshot, relative_path: str) -> ReadResult:
        operation = "READ_FILE"
        path = self._resolve_inside(snapshot, relative_path, operation)
        try:
            if not path.is_file():
                raise self._error(operation, "NOT_A_REGULAR_FILE", relative_path, snapshot.snapshot_identity)
            content = path.read_bytes()
        except ExecutorOperationError:
            raise
        except OSError as error:
            raise self._error(operation, "READ_ERROR", str(error), snapshot.snapshot_identity) from error
        return ReadResult(
            relative_path=relative_path,
            content=content,
            fact=self._fact(
                operation,
                True,
                {"relative_path": relative_path, "byte_count": len(content), "content_sha256": _digest(content)},
                snapshot.snapshot_identity,
            ),
        )

    def search(
        self,
        snapshot: RepositorySnapshot,
        literal: str,
        *,
        scope: str = ".",
        result_limit: int = 100,
    ) -> SearchResult:
        operation = "SEARCH"
        if not isinstance(literal, str) or not literal:
            raise self._error(operation, "MALFORMED_SEARCH_REQUEST", "literal must be non-empty", snapshot.snapshot_identity)
        if not isinstance(result_limit, int) or result_limit < 1 or result_limit > 1000:
            raise self._error(operation, "MALFORMED_SEARCH_REQUEST", "result_limit must be 1..1000", snapshot.snapshot_identity)
        root = self._resolve_inside(snapshot, scope, operation)
        if not root.is_dir():
            raise self._error(operation, "SEARCH_SCOPE_NOT_DIRECTORY", scope, snapshot.snapshot_identity)

        repository_root = Path(snapshot.canonical_root)
        matches: list[SearchMatch] = []
        try:
            for directory, directories, filenames in os.walk(root, followlinks=False):
                directories[:] = sorted(name for name in directories if not (Path(directory) / name).is_symlink())
                for filename in sorted(filenames):
                    candidate = Path(directory) / filename
                    if candidate.is_symlink() or not candidate.is_file():
                        continue
                    resolved = candidate.resolve(strict=True)
                    try:
                        resolved.relative_to(repository_root)
                    except ValueError:
                        continue
                    for line_number, line in enumerate(
                        candidate.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
                    ):
                        if literal in line:
                            matches.append(
                                SearchMatch(
                                    relative_path=candidate.relative_to(repository_root).as_posix(),
                                    line_number=line_number,
                                    line_text=line,
                                )
                            )
                            if len(matches) >= result_limit:
                                return self._search_result(snapshot, literal, scope, matches)
        except OSError as error:
            raise self._error(operation, "SEARCH_ERROR", str(error), snapshot.snapshot_identity) from error
        return self._search_result(snapshot, literal, scope, matches)

    def _search_result(
        self, snapshot: RepositorySnapshot, literal: str, scope: str, matches: list[SearchMatch]
    ) -> SearchResult:
        return SearchResult(
            matches=tuple(matches),
            fact=self._fact(
                "SEARCH",
                True,
                {"literal": literal, "scope": scope, "match_count": len(matches)},
                snapshot.snapshot_identity,
            ),
        )

    def _repository_root(self, repository_root: str | os.PathLike[str]) -> Path:
        operation = "OBSERVE_REPOSITORY"
        requested = Path(repository_root)
        try:
            canonical_requested = requested.resolve(strict=True)
        except OSError as error:
            raise self._error(operation, "REPOSITORY_UNAVAILABLE", str(error)) from error
        if not canonical_requested.is_dir():
            raise self._error(operation, "NOT_A_GIT_WORKTREE", "repository root is not a directory")
        toplevel = self._git(canonical_requested, "rev-parse", "--show-toplevel", operation=operation).decode().strip()
        canonical_root = Path(toplevel).resolve(strict=True)
        if canonical_root != canonical_requested:
            raise self._error(operation, "UNSUPPORTED_REPOSITORY_ROOT", "root must be the Git worktree root")
        return canonical_root

    def _capture_snapshot(self, root: Path) -> RepositorySnapshot:
        operation = "OBSERVE_REPOSITORY"
        common_dir_raw = self._git(root, "rev-parse", "--git-common-dir", operation=operation).decode().strip()
        common_dir = (root / common_dir_raw).resolve(strict=True) if not os.path.isabs(common_dir_raw) else Path(common_dir_raw).resolve(strict=True)
        common_stat = common_dir.stat()
        object_format = self._git(root, "rev-parse", "--show-object-format", operation=operation).decode().strip()
        root_commits = sorted(
            line for line in self._git(root, "rev-list", "--max-parents=0", "HEAD", operation=operation).decode().splitlines() if line
        )
        repository_identity_payload = {
            "canonical_root": str(root),
            "common_dir": str(common_dir),
            "common_dir_device": common_stat.st_dev,
            "common_dir_inode": common_stat.st_ino,
            "object_format": object_format,
            "root_commits": root_commits,
        }
        repository_identity = _digest(_canonical_json(repository_identity_payload))
        head_commit = self._git(root, "rev-parse", "HEAD", operation=operation).decode().strip()
        branch_result = self._git_result(root, "symbolic-ref", "--quiet", "--short", "HEAD")
        if branch_result.returncode == 0:
            branch = branch_result.stdout.decode().strip()
        elif branch_result.returncode == 1:
            branch = "DETACHED"
        else:
            self._raise_git_failure(operation, branch_result)

        index_identity = _digest(self._git(root, "ls-files", "--stage", "-z", operation=operation))
        tracked_worktree_identity = _digest(
            self._git(root, "diff", "--no-ext-diff", "--no-color", "--binary", "--ignore-submodules=none", "--", operation=operation)
        )
        untracked_inventory = self._untracked_inventory(root, operation)
        untracked_identity = _digest(_canonical_json(untracked_inventory))
        submodule_identity = _digest(self._git(root, "submodule", "status", "--recursive", operation=operation))
        material_state = {
            "version": SNAPSHOT_VERSION,
            "repository_identity": repository_identity,
            "canonical_root": str(root),
            "git_common_dir": str(common_dir),
            "head_commit": head_commit,
            "branch": branch,
            "index_identity": index_identity,
            "tracked_worktree_identity": tracked_worktree_identity,
            "untracked_inventory": untracked_inventory,
            "untracked_identity": untracked_identity,
            "submodule_identity": submodule_identity,
            "ignored_file_policy": IGNORED_FILE_POLICY,
        }
        snapshot_fields = dict(material_state)
        snapshot_fields["untracked_inventory"] = tuple(tuple(item) for item in untracked_inventory)
        return RepositorySnapshot(
            **snapshot_fields,
            snapshot_identity=_digest(_canonical_json(material_state)),
        )

    def _untracked_inventory(self, root: Path, operation: str) -> list[tuple[str, str, str]]:
        listed = self._git(root, "ls-files", "--others", "--exclude-standard", "-z", operation=operation)
        entries: list[tuple[str, str, str]] = []
        for raw_path in listed.split(b"\0"):
            if not raw_path:
                continue
            relative = raw_path.decode("utf-8", errors="surrogateescape")
            candidate = root / relative
            try:
                stat_result = candidate.lstat()
            except OSError as error:
                raise self._error(operation, "STATE_OBSERVATION_ERROR", str(error)) from error
            if os.path.islink(candidate):
                kind, identity = "symlink", os.readlink(candidate)
            elif os.path.isfile(candidate):
                kind, identity = "file", _digest(candidate.read_bytes())
            else:
                kind, identity = f"other:{stat_result.st_mode:o}", ""
            entries.append((relative, kind, identity))
        return sorted(entries)

    def _resolve_inside(self, snapshot: RepositorySnapshot, relative_path: str, operation: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path:
            raise self._error(operation, "MALFORMED_PATH", "path must be a non-empty relative string", snapshot.snapshot_identity)
        candidate_input = PurePath(relative_path)
        if candidate_input.is_absolute() or ".." in candidate_input.parts:
            raise self._error(operation, "PATH_ESCAPE_DENIED", relative_path, snapshot.snapshot_identity)
        root = Path(snapshot.canonical_root)
        try:
            candidate = (root / candidate_input).resolve(strict=True)
            candidate.relative_to(root)
        except (OSError, ValueError) as error:
            raise self._error(operation, "PATH_ESCAPE_DENIED", relative_path, snapshot.snapshot_identity) from error
        return candidate

    def _git(self, root: Path, *arguments: str, operation: str) -> bytes:
        result = self._git_result(root, *arguments)
        if result.returncode != 0:
            self._raise_git_failure(operation, result)
        return result.stdout

    @staticmethod
    def _git_result(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "-C", os.fspath(root), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def _raise_git_failure(self, operation: str, result: subprocess.CompletedProcess[bytes]) -> None:
        detail = result.stderr.decode("utf-8", errors="replace").strip() or f"git exited {result.returncode}"
        raise self._error(operation, "GIT_COMMAND_FAILED", detail)

    @staticmethod
    def _fact(
        operation: str,
        success: bool,
        observed_result: Mapping[str, Any],
        snapshot_identity: str | None = None,
        error_classification: str | None = None,
    ) -> ExecutorFact:
        return ExecutorFact(
            operation=operation,
            success=success,
            observed_result=dict(observed_result),
            snapshot_identity=snapshot_identity,
            error_classification=error_classification,
        )

    def _error(
        self,
        operation: str,
        classification: str,
        detail: str,
        snapshot_identity: str | None = None,
    ) -> ExecutorOperationError:
        return ExecutorOperationError(
            detail,
            self._fact(
                operation,
                False,
                {"detail": detail},
                snapshot_identity,
                classification,
            ),
        )
