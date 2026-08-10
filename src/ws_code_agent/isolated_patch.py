"""Bounded patch application in disposable copies; never in source repositories."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import os
from pathlib import Path, PurePath
import shutil
import subprocess
import tempfile
from typing import Mapping

from .readonly_executor import (
    CompareStatus,
    ExecutorFact,
    ExecutorOperationError,
    ReadOnlyExecutor,
    RepositorySnapshot,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ApplicationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    STATE_STALE = "STATE_STALE"
    REPOSITORY_MISMATCH = "REPOSITORY_MISMATCH"
    PATCH_REJECTED = "PATCH_REJECTED"
    PATCH_PARTIAL = "PATCH_PARTIAL"
    PATH_SCOPE_DENIED = "PATH_SCOPE_DENIED"
    PATH_ESCAPE_DENIED = "PATH_ESCAPE_DENIED"
    SYMLINK_DENIED = "SYMLINK_DENIED"
    EXECUTOR_ERROR = "EXECUTOR_ERROR"


@dataclass(frozen=True)
class PatchProposal:
    """Untrusted proposer-originated mutation; it is never application evidence."""

    proposal_identity: str
    source_snapshot_identity: str
    target_repository_identity: str
    patch_content: bytes
    patch_content_identity: str
    proposed_paths: tuple[str, ...]
    originating_actor: str = field(default="proposer", init=False)

    @classmethod
    def create(
        cls, snapshot: RepositorySnapshot, patch_content: bytes, proposed_paths: tuple[str, ...]
    ) -> "PatchProposal":
        normalized_paths = tuple(sorted(proposed_paths))
        content_identity = _sha256(patch_content)
        proposal_identity = _sha256(
            "\0".join((snapshot.snapshot_identity, snapshot.repository_identity, content_identity, *normalized_paths)).encode()
        )
        return cls(
            proposal_identity=proposal_identity,
            source_snapshot_identity=snapshot.snapshot_identity,
            target_repository_identity=snapshot.repository_identity,
            patch_content=patch_content,
            patch_content_identity=content_identity,
            proposed_paths=normalized_paths,
        )


@dataclass(frozen=True)
class IsolatedContext:
    source_snapshot: RepositorySnapshot
    workspace_root: str
    isolated_root: str
    initial_snapshot: RepositorySnapshot
    initial_manifest: Mapping[str, str]
    build_fact: ExecutorFact


@dataclass(frozen=True)
class PatchApplicationResult:
    status: ApplicationStatus
    proposal: PatchProposal
    context: IsolatedContext | None
    result_snapshot: RepositorySnapshot | None
    actual_changed_paths: tuple[str, ...]
    fact: ExecutorFact


class IsolatedPatchExecutor:
    """Fixed, non-interactive ``git apply --index`` in disposable state only."""

    def __init__(self, observer: ReadOnlyExecutor | None = None) -> None:
        self._observer = observer or ReadOnlyExecutor()

    def build_isolated_copy(self, snapshot: RepositorySnapshot) -> IsolatedContext:
        comparison = self._observer.compare_snapshot(snapshot)
        if comparison.status is CompareStatus.STALE:
            raise self._error("BUILD_ISOLATED_COPY", ApplicationStatus.STATE_STALE, "source snapshot is stale", snapshot)
        if comparison.status is CompareStatus.ERROR:
            raise self._error("BUILD_ISOLATED_COPY", ApplicationStatus.EXECUTOR_ERROR, "source cannot be compared", snapshot)
        if snapshot.submodule_identity != _sha256(b""):
            raise self._error("BUILD_ISOLATED_COPY", ApplicationStatus.EXECUTOR_ERROR, "submodules unsupported in v1", snapshot)
        source = Path(snapshot.canonical_root)
        git_dir = source / ".git"
        if not git_dir.is_dir() or git_dir.is_symlink():
            raise self._error("BUILD_ISOLATED_COPY", ApplicationStatus.EXECUTOR_ERROR, "linked worktrees unsupported in v1", snapshot)
        workspace = Path(tempfile.mkdtemp(prefix="ws-code-agent-isolated-"))
        isolated = workspace / "repository"
        try:
            self._assert_isolated(source, isolated)
            isolated.mkdir()
            shutil.copytree(git_dir, isolated / ".git", symlinks=True)
            for relative in self._material_paths(source):
                self._copy_material_path(source, isolated, relative)
            initial = self._observer.observe_repository(isolated).snapshot
            if not self._same_material_state(snapshot, initial):
                raise self._error("BUILD_ISOLATED_COPY", ApplicationStatus.EXECUTOR_ERROR, "snapshot reconstruction mismatch", snapshot)
            manifest = self._manifest(isolated)
        except Exception:
            self._safe_cleanup(workspace, source)
            raise
        fact = ExecutorFact(
            operation="BUILD_ISOLATED_COPY",
            success=True,
            observed_result={
                "source_snapshot_identity": snapshot.snapshot_identity,
                "isolated_root": str(isolated),
                "initial_snapshot_identity": initial.snapshot_identity,
            },
            snapshot_identity=snapshot.snapshot_identity,
        )
        return IsolatedContext(snapshot, str(workspace), str(isolated), initial, manifest, fact)

    def apply_patch_isolated(
        self, context: IsolatedContext, proposal: PatchProposal, allowed_paths: tuple[str, ...]
    ) -> PatchApplicationResult:
        operation = "APPLY_PATCH_ISOLATED"
        source = context.source_snapshot
        if proposal.source_snapshot_identity != source.snapshot_identity or proposal.target_repository_identity != source.repository_identity:
            return self._result(ApplicationStatus.REPOSITORY_MISMATCH, proposal, context, None, (), operation, source, "proposal binding mismatch")
        comparison = self._observer.compare_snapshot(source)
        if comparison.status is not CompareStatus.MATCH:
            return self._result(ApplicationStatus.STATE_STALE, proposal, context, None, (), operation, source, "source snapshot is stale")
        try:
            patch_paths = self._patch_paths(proposal.patch_content)
            if tuple(sorted(patch_paths)) != proposal.proposed_paths:
                return self._result(ApplicationStatus.PATH_SCOPE_DENIED, proposal, context, None, (), operation, source, "proposal paths do not match patch")
            allowed = set(allowed_paths)
            if not patch_paths <= allowed:
                return self._result(ApplicationStatus.PATH_SCOPE_DENIED, proposal, context, None, (), operation, source, "patch path outside scope")
            self._assert_patch_paths_safe(Path(context.isolated_root), patch_paths)
        except ExecutorOperationError as error:
            status = ApplicationStatus.SYMLINK_DENIED if error.fact.error_classification == "SYMLINK_DENIED" else ApplicationStatus.PATH_ESCAPE_DENIED
            return self._result(status, proposal, context, None, (), operation, source, str(error))
        except ValueError as error:
            return self._result(ApplicationStatus.PATCH_REJECTED, proposal, context, None, (), operation, source, str(error))

        before = self._observer.observe_repository(context.isolated_root).snapshot
        if not self._same_material_state(context.initial_snapshot, before):
            return self._result(ApplicationStatus.EXECUTOR_ERROR, proposal, context, before, (), operation, source, "isolated state changed before apply")
        process = subprocess.run(
            ["git", "-C", context.isolated_root, "apply", "--index", "--whitespace=nowarn", "-"],
            input=proposal.patch_content,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        after = self._observer.observe_repository(context.isolated_root).snapshot
        changed = tuple(sorted(self._changed_paths(context.initial_manifest, self._manifest(Path(context.isolated_root)))))
        stdout = process.stdout.decode("utf-8", errors="replace")
        stderr = process.stderr.decode("utf-8", errors="replace")
        if process.returncode != 0:
            status = ApplicationStatus.PATCH_REJECTED if self._same_material_state(before, after) else ApplicationStatus.PATCH_PARTIAL
            return self._result(status, proposal, context, after, changed, operation, source, "git apply rejected", stdout, stderr, process.returncode)
        if not set(changed) <= set(allowed_paths) or not set(changed) <= set(proposal.proposed_paths):
            return self._result(ApplicationStatus.PATH_SCOPE_DENIED, proposal, context, after, changed, operation, source, "observed paths outside scope", stdout, stderr, process.returncode)
        return self._result(ApplicationStatus.SUCCESS, proposal, context, after, changed, operation, source, "patch applied in isolation", stdout, stderr, process.returncode, True)

    def cleanup(self, context: IsolatedContext) -> None:
        workspace = Path(context.workspace_root)
        source = Path(context.source_snapshot.canonical_root)
        if Path(context.isolated_root).parent != workspace:
            raise self._error("CLEANUP_ISOLATED_COPY", ApplicationStatus.EXECUTOR_ERROR, "workspace relationship ambiguous", context.source_snapshot)
        self._safe_cleanup(workspace, source)

    def _result(self, status, proposal, context, result_snapshot, changed, operation, source, detail, stdout="", stderr="", exit_code=None, success=False):
        return PatchApplicationResult(
            status, proposal, context, result_snapshot, changed,
            ExecutorFact(operation=operation, success=success, snapshot_identity=source.snapshot_identity,
                         error_classification=None if success else status.value,
                         observed_result={"proposal_identity": proposal.proposal_identity, "detail": detail,
                                          "result_snapshot_identity": result_snapshot.snapshot_identity if result_snapshot else None,
                                          "actual_changed_paths": changed, "stdout": stdout, "stderr": stderr, "exit_code": exit_code}),
        )

    @staticmethod
    def _same_material_state(left: RepositorySnapshot, right: RepositorySnapshot) -> bool:
        return (left.head_commit, left.branch, left.index_identity, left.tracked_worktree_identity,
                left.untracked_identity, left.submodule_identity, left.ignored_file_policy) == (
                right.head_commit, right.branch, right.index_identity, right.tracked_worktree_identity,
                right.untracked_identity, right.submodule_identity, right.ignored_file_policy)

    def _material_paths(self, root: Path) -> set[str]:
        tracked = self._git_paths(root, "ls-files", "-z")
        untracked = self._git_paths(root, "ls-files", "--others", "--exclude-standard", "-z")
        return set(tracked) | set(untracked)

    @staticmethod
    def _git_paths(root: Path, *arguments: str) -> list[str]:
        result = subprocess.run(["git", "-C", str(root), *arguments], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
        return [item.decode("utf-8", errors="surrogateescape") for item in result.stdout.split(b"\0") if item]

    @staticmethod
    def _copy_material_path(source: Path, destination: Path, relative: str) -> None:
        source_path = source / relative
        destination_path = destination / relative
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_symlink():
            os.symlink(os.readlink(source_path), destination_path)
        else:
            shutil.copy2(source_path, destination_path, follow_symlinks=False)

    def _manifest(self, root: Path) -> Mapping[str, str]:
        manifest: dict[str, str] = {}
        for relative in self._material_paths(root):
            path = root / relative
            if path.is_symlink():
                manifest[relative] = "symlink:" + os.readlink(path)
            elif path.is_file():
                manifest[relative] = "file:" + _sha256(path.read_bytes())
            else:
                manifest[relative] = "other"
        return manifest

    @staticmethod
    def _changed_paths(before: Mapping[str, str], after: Mapping[str, str]) -> set[str]:
        return {path for path in set(before) | set(after) if before.get(path) != after.get(path)}

    @staticmethod
    def _assert_isolated(source: Path, isolated: Path) -> None:
        source_real, isolated_real = source.resolve(), isolated.resolve(strict=False)
        if source_real == isolated_real or source_real in isolated_real.parents or isolated_real in source_real.parents:
            raise RuntimeError("isolated root overlaps authoritative root")

    def _assert_patch_paths_safe(self, root: Path, paths: set[str]) -> None:
        for relative in paths:
            path = PurePath(relative)
            if path.is_absolute() or ".." in path.parts or relative.startswith(".git/"):
                raise self._error("APPLY_PATCH_ISOLATED", ApplicationStatus.PATH_ESCAPE_DENIED, relative, None)
            candidate = root / path
            for parent in (candidate.parent, *candidate.parents):
                if parent == root.parent:
                    break
                if parent.exists() and parent.is_symlink():
                    raise self._error("APPLY_PATCH_ISOLATED", ApplicationStatus.SYMLINK_DENIED, relative, None)
                if parent == root:
                    break
            if candidate.exists() and candidate.is_symlink():
                raise self._error("APPLY_PATCH_ISOLATED", ApplicationStatus.SYMLINK_DENIED, relative, None)

    @staticmethod
    def _patch_paths(patch: bytes) -> set[str]:
        paths: set[str] = set()
        for line in patch.decode("utf-8", errors="strict").splitlines():
            if line.startswith("diff --git "):
                parts = line.split(" ")
                if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
                    raise ValueError("unsupported patch path syntax")
                left, right = parts[2][2:], parts[3][2:]
                if left != right:
                    paths.update((left, right))
                else:
                    paths.add(left)
        if not paths:
            raise ValueError("patch contains no supported diff header")
        return paths

    @staticmethod
    def _safe_cleanup(workspace: Path, source: Path) -> None:
        workspace_real, source_real = workspace.resolve(strict=False), source.resolve()
        if workspace_real == source_real or source_real in workspace_real.parents or workspace_real in source_real.parents:
            raise RuntimeError("refusing ambiguous workspace cleanup")
        if workspace.exists():
            shutil.rmtree(workspace)

    @staticmethod
    def _error(operation: str, status: ApplicationStatus, detail: str, snapshot: RepositorySnapshot | None) -> ExecutorOperationError:
        return ExecutorOperationError(detail, ExecutorFact(operation=operation, success=False, error_classification=status.value,
            snapshot_identity=snapshot.snapshot_identity if snapshot else None, observed_result={"detail": detail}))
