"""Deterministic exact-text replacement in an isolated candidate workspace.

The model owns the path and both text values.  This executor supplies only the
mechanical transport: exact matching, isolated replacement, observed effects,
and a canonical review diff.  It is not wired to a live supervised lane.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from typing import Mapping

from .isolated_patch import IsolatedContext, IsolatedPatchExecutor
from .readonly_executor import CompareStatus, ExecutorFact, ReadOnlyExecutor, RepositorySnapshot


COMPONENT_ID = "ws-code-agent-structured-text-replacement/v1"
OPERATION = "APPLY_TEXT_REPLACEMENT_ISOLATED"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


class TextReplacementStatus(str, Enum):
    STRUCTURED_EDIT_ACCEPTED = "STRUCTURED_EDIT_ACCEPTED"
    TEXT_MATCH_ZERO = "TEXT_MATCH_ZERO"
    TEXT_MATCH_MULTIPLE = "TEXT_MATCH_MULTIPLE"
    TEXT_REPLACEMENT_NO_EFFECT = "TEXT_REPLACEMENT_NO_EFFECT"
    TEXT_ENCODING_UNSUPPORTED = "TEXT_ENCODING_UNSUPPORTED"
    DENIED_AUTHORITY = "DENIED_AUTHORITY"
    STATE_STALE = "STATE_STALE"
    REPOSITORY_MISMATCH = "REPOSITORY_MISMATCH"
    EXECUTOR_ERROR = "EXECUTOR_ERROR"


@dataclass(frozen=True)
class StructuredTextReplacement:
    """Exact parsed model values bound to one immutable source snapshot."""

    structured_request_sha256: str
    raw_request_sha256: str
    source_snapshot_identity: str
    target_repository_identity: str
    path: str
    old_text: str
    new_text: str
    path_sha256: str
    old_text_sha256: str
    new_text_sha256: str
    originating_actor: str = field(default="model", init=False)

    @classmethod
    def create(
        cls,
        snapshot: RepositorySnapshot,
        *,
        raw_request_sha256: str,
        path: str,
        old_text: str,
        new_text: str,
    ) -> "StructuredTextReplacement":
        if not all(isinstance(value, str) for value in (path, old_text, new_text)):
            raise TypeError("structured replacement values must be strings")
        if not old_text:
            raise ValueError("old_text must be non-empty")
        if (
            len(raw_request_sha256) != 64
            or any(character not in "0123456789abcdef" for character in raw_request_sha256)
        ):
            raise ValueError("raw request SHA-256 must be lowercase hexadecimal")
        try:
            path_bytes = path.encode("utf-8")
            old_bytes = old_text.encode("utf-8")
            new_bytes = new_text.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("structured replacement values must be UTF-8") from error
        arguments = {"path": path, "old_text": old_text, "new_text": new_text}
        request = {
            "request_type": "PROPOSE_TEXT_REPLACEMENT",
            "arguments": arguments,
        }
        return cls(
            structured_request_sha256=_sha256(_canonical_json(request)),
            raw_request_sha256=raw_request_sha256,
            source_snapshot_identity=snapshot.snapshot_identity,
            target_repository_identity=snapshot.repository_identity,
            path=path,
            old_text=old_text,
            new_text=new_text,
            path_sha256=_sha256(path_bytes),
            old_text_sha256=_sha256(old_bytes),
            new_text_sha256=_sha256(new_bytes),
        )


@dataclass(frozen=True)
class StructuredTextReplacementResult:
    status: TextReplacementStatus
    proposal: StructuredTextReplacement
    context: IsolatedContext | None
    result_snapshot: RepositorySnapshot | None
    actual_changed_paths: tuple[str, ...]
    exact_match_count: int | None
    before_file_sha256: str | None
    after_file_sha256: str | None
    canonical_diff: bytes | None
    canonical_diff_sha256: str | None
    candidate_identity: str | None
    fact: ExecutorFact


class StructuredTextReplacementExecutor:
    """Apply one exactly-once UTF-8 replacement outside the source repository."""

    def __init__(self, observer: ReadOnlyExecutor | None = None) -> None:
        self._observer = observer or ReadOnlyExecutor()
        self._workspace = IsolatedPatchExecutor(self._observer)

    def build_isolated_copy(self, snapshot: RepositorySnapshot) -> IsolatedContext:
        return self._workspace.build_isolated_copy(snapshot)

    def cleanup(self, context: IsolatedContext) -> None:
        self._workspace.cleanup(context)

    def apply_text_replacement_isolated(
        self,
        context: IsolatedContext,
        proposal: StructuredTextReplacement,
        allowed_paths: tuple[str, ...],
    ) -> StructuredTextReplacementResult:
        source = context.source_snapshot
        if (
            proposal.source_snapshot_identity != source.snapshot_identity
            or proposal.target_repository_identity != source.repository_identity
        ):
            return self._result(
                TextReplacementStatus.REPOSITORY_MISMATCH,
                proposal,
                context,
                detail="structured request binding mismatch",
            )
        if self._observer.compare_snapshot(source).status is not CompareStatus.MATCH:
            return self._result(
                TextReplacementStatus.STATE_STALE,
                proposal,
                context,
                detail="source snapshot is stale",
            )
        if not self._authorized_path(proposal.path, allowed_paths):
            return self._result(
                TextReplacementStatus.DENIED_AUTHORITY,
                proposal,
                context,
                detail="path is unsafe or outside explicit patch authority",
            )

        root = Path(context.isolated_root)
        target = root / PurePosixPath(proposal.path)
        if not self._safe_existing_regular_file(root, target):
            return self._result(
                TextReplacementStatus.DENIED_AUTHORITY,
                proposal,
                context,
                detail="path is not an existing non-symlink file inside the candidate",
            )
        before_snapshot = self._observer.observe_repository(root).snapshot
        if not self._same_material_state(context.initial_snapshot, before_snapshot):
            return self._result(
                TextReplacementStatus.EXECUTOR_ERROR,
                proposal,
                context,
                result_snapshot=before_snapshot,
                detail="isolated candidate changed before replacement",
            )
        before_manifest = self._material_manifest(root)
        before_bytes = target.read_bytes()
        try:
            before_text = before_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return self._result(
                TextReplacementStatus.TEXT_ENCODING_UNSUPPORTED,
                proposal,
                context,
                exact_match_count=None,
                before_file_sha256=_sha256(before_bytes),
                detail="V1 supports UTF-8 text only",
            )
        if b"\0" in before_bytes:
            return self._result(
                TextReplacementStatus.TEXT_ENCODING_UNSUPPORTED,
                proposal,
                context,
                exact_match_count=None,
                before_file_sha256=_sha256(before_bytes),
                detail="V1 does not support NUL-bearing text",
            )
        if "\0" in proposal.old_text or "\0" in proposal.new_text:
            return self._result(
                TextReplacementStatus.TEXT_ENCODING_UNSUPPORTED,
                proposal,
                context,
                exact_match_count=None,
                before_file_sha256=_sha256(before_bytes),
                detail="V1 does not support NUL-bearing replacement text",
            )
        count = self._exact_occurrence_count(before_text, proposal.old_text)
        if count == 0:
            return self._result(
                TextReplacementStatus.TEXT_MATCH_ZERO,
                proposal,
                context,
                exact_match_count=0,
                before_file_sha256=_sha256(before_bytes),
                detail="old_text has no exact occurrence",
            )
        if count != 1:
            return self._result(
                TextReplacementStatus.TEXT_MATCH_MULTIPLE,
                proposal,
                context,
                exact_match_count=count,
                before_file_sha256=_sha256(before_bytes),
                detail="old_text does not identify exactly one region",
            )
        if proposal.old_text == proposal.new_text:
            return self._result(
                TextReplacementStatus.TEXT_REPLACEMENT_NO_EFFECT,
                proposal,
                context,
                exact_match_count=1,
                before_file_sha256=_sha256(before_bytes),
                detail="old_text and new_text are identical",
            )

        after_text = before_text.replace(proposal.old_text, proposal.new_text, 1)
        after_bytes = after_text.encode("utf-8")
        try:
            target.write_bytes(after_bytes)
            after_snapshot = self._observer.observe_repository(root).snapshot
            after_manifest = self._material_manifest(root)
            changed = tuple(sorted(
                path for path in set(before_manifest) | set(after_manifest)
                if before_manifest.get(path) != after_manifest.get(path)
            ))
            if changed != (proposal.path,) or not set(changed) <= set(allowed_paths):
                return self._result(
                    TextReplacementStatus.DENIED_AUTHORITY,
                    proposal,
                    context,
                    result_snapshot=after_snapshot,
                    actual_changed_paths=changed,
                    exact_match_count=1,
                    before_file_sha256=_sha256(before_bytes),
                    after_file_sha256=_sha256(after_bytes),
                    detail="observed candidate effects exceed explicit authority",
                )
            canonical_diff = self._canonical_diff(root, proposal.path)
            diff_sha = _sha256(canonical_diff)
            candidate_identity = _sha256(_canonical_json({
                "source_snapshot_identity": source.snapshot_identity,
                "structured_request_sha256": proposal.structured_request_sha256,
                "path": proposal.path,
                "before_file_sha256": _sha256(before_bytes),
                "after_file_sha256": _sha256(after_bytes),
                "canonical_diff_sha256": diff_sha,
                "changed_paths": changed,
            }))
            return self._result(
                TextReplacementStatus.STRUCTURED_EDIT_ACCEPTED,
                proposal,
                context,
                result_snapshot=after_snapshot,
                actual_changed_paths=changed,
                exact_match_count=1,
                before_file_sha256=_sha256(before_bytes),
                after_file_sha256=_sha256(after_bytes),
                canonical_diff=canonical_diff,
                canonical_diff_sha256=diff_sha,
                candidate_identity=candidate_identity,
                detail="exact replacement applied in isolated candidate",
                success=True,
            )
        except OSError as error:
            return self._result(
                TextReplacementStatus.EXECUTOR_ERROR,
                proposal,
                context,
                exact_match_count=1,
                before_file_sha256=_sha256(before_bytes),
                detail=f"isolated replacement failed: {type(error).__name__}",
            )

    @staticmethod
    def _authorized_path(path: str, allowed_paths: tuple[str, ...]) -> bool:
        if not path or "\0" in path or "\\" in path or path not in allowed_paths:
            return False
        pure = PurePosixPath(path)
        return (
            not pure.is_absolute()
            and pure.as_posix() not in {"", "."}
            and pure.as_posix() == path
            and ".." not in pure.parts
            and ".git" not in pure.parts
        )

    @staticmethod
    def _exact_occurrence_count(text: str, old_text: str) -> int:
        """Count every exact start position, including overlapping matches."""

        count = 0
        start = 0
        while True:
            position = text.find(old_text, start)
            if position < 0:
                return count
            count += 1
            start = position + 1

    @staticmethod
    def _safe_existing_regular_file(root: Path, target: Path) -> bool:
        current = root
        try:
            for part in target.relative_to(root).parts:
                current = current / part
                if current.is_symlink():
                    return False
            return target.is_file() and not target.is_symlink() and target.resolve().is_relative_to(root.resolve())
        except (OSError, ValueError):
            return False

    @staticmethod
    def _canonical_diff(root: Path, path: str) -> bytes:
        process = subprocess.run(
            [
                "git", "-C", str(root), "diff", "--no-ext-diff", "--no-textconv",
                "--no-color", "--no-renames", "--src-prefix=a/", "--dst-prefix=b/",
                "--", path,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode or not process.stdout:
            raise OSError("canonical candidate diff unavailable")
        return process.stdout

    @staticmethod
    def _same_material_state(left: RepositorySnapshot, right: RepositorySnapshot) -> bool:
        return (
            left.head_commit,
            left.branch,
            left.index_identity,
            left.tracked_worktree_identity,
            left.untracked_identity,
            left.submodule_identity,
            left.ignored_file_policy,
        ) == (
            right.head_commit,
            right.branch,
            right.index_identity,
            right.tracked_worktree_identity,
            right.untracked_identity,
            right.submodule_identity,
            right.ignored_file_policy,
        )

    @staticmethod
    def _material_manifest(root: Path) -> Mapping[str, str]:
        process = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode:
            raise OSError("candidate inventory unavailable")
        result: dict[str, str] = {}
        for raw in process.stdout.split(b"\0"):
            if not raw:
                continue
            relative = raw.decode("utf-8", errors="surrogateescape")
            candidate = root / relative
            if candidate.is_symlink():
                result[relative] = "symlink:" + os.readlink(candidate)
            elif candidate.is_file():
                result[relative] = "file:" + _sha256(candidate.read_bytes())
            else:
                result[relative] = "other"
        return result

    def _result(
        self,
        status: TextReplacementStatus,
        proposal: StructuredTextReplacement,
        context: IsolatedContext | None,
        *,
        result_snapshot: RepositorySnapshot | None = None,
        actual_changed_paths: tuple[str, ...] = (),
        exact_match_count: int | None = None,
        before_file_sha256: str | None = None,
        after_file_sha256: str | None = None,
        canonical_diff: bytes | None = None,
        canonical_diff_sha256: str | None = None,
        candidate_identity: str | None = None,
        detail: str,
        success: bool = False,
    ) -> StructuredTextReplacementResult:
        evidence = {
            "structured_request_sha256": proposal.structured_request_sha256,
            "raw_request_sha256": proposal.raw_request_sha256,
            "path_sha256": proposal.path_sha256,
            "old_text_sha256": proposal.old_text_sha256,
            "new_text_sha256": proposal.new_text_sha256,
            "before_file_sha256": before_file_sha256,
            "after_file_sha256": after_file_sha256,
            "canonical_diff_sha256": canonical_diff_sha256,
            "candidate_identity": candidate_identity,
            "result_snapshot_identity": result_snapshot.snapshot_identity if result_snapshot else None,
            "exact_match_count": exact_match_count,
            "actual_changed_paths": actual_changed_paths,
            "detail": detail,
            "canonical_diff_origin": "evaluator" if canonical_diff is not None else None,
        }
        return StructuredTextReplacementResult(
            status=status,
            proposal=proposal,
            context=context,
            result_snapshot=result_snapshot,
            actual_changed_paths=actual_changed_paths,
            exact_match_count=exact_match_count,
            before_file_sha256=before_file_sha256,
            after_file_sha256=after_file_sha256,
            canonical_diff=canonical_diff,
            canonical_diff_sha256=canonical_diff_sha256,
            candidate_identity=candidate_identity,
            fact=ExecutorFact(
                operation=OPERATION,
                success=success,
                observed_result=evidence,
                snapshot_identity=proposal.source_snapshot_identity,
                error_classification=None if success else status.value,
                component=COMPONENT_ID,
            ),
        )
