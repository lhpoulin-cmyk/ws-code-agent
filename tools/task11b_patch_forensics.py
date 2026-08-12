"""Evaluator-only Task 11B structural analysis for unified-diff evidence.

This module classifies bytes. It is not imported by the parser, executor, or
supervised work lane, and it never repairs or applies a model patch.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re


NO_SUPPORTED_DIFF_HEADER = "NO_SUPPORTED_DIFF_HEADER"
MISSING_FILE_HEADER = "MISSING_FILE_HEADER"
MALFORMED_FILE_HEADER = "MALFORMED_FILE_HEADER"
MISSING_HUNK_HEADER = "MISSING_HUNK_HEADER"
MALFORMED_HUNK_HEADER = "MALFORMED_HUNK_HEADER"
INCORRECT_HUNK_COUNTS = "INCORRECT_HUNK_COUNTS"
INVALID_CONTEXT = "INVALID_CONTEXT"
TRUNCATED_PATCH = "TRUNCATED_PATCH"
WRONG_TARGET_PATH = "WRONG_TARGET_PATH"

_DIFF_HEADER = re.compile(r"^diff --git a/(?P<left>[^\0]+) b/(?P<right>[^\0]+)$")
_OLD_HEADER = re.compile(r"^--- (?P<path>/dev/null|a/[^\t\0]+)(?:\t.*)?$")
_NEW_HEADER = re.compile(r"^\+\+\+ (?P<path>/dev/null|b/[^\t\0]+)(?:\t.*)?$")
_HUNK_HEADER = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?: .*)?$"
)


@dataclass(frozen=True)
class HunkForensics:
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    observed_old_lines: int
    observed_new_lines: int
    context_lines: int
    context_content: tuple[str, ...]
    removed_lines: tuple[str, ...]
    added_lines: tuple[str, ...]
    invalid_lines: tuple[str, ...]

    def evidence(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PatchForensics:
    patch_sha256: str
    byte_count: int
    terminal_newline: bool
    diff_paths: tuple[tuple[str, str], ...]
    old_headers: tuple[str, ...]
    new_headers: tuple[str, ...]
    target_paths: tuple[str, ...]
    hunks: tuple[HunkForensics, ...]
    findings: tuple[str, ...]

    def evidence(self) -> dict[str, object]:
        result = asdict(self)
        result["hunks"] = [hunk.evidence() for hunk in self.hunks]
        return result


def inspect_patch(patch: bytes, proposed_paths: tuple[str, ...]) -> PatchForensics:
    """Classify exact patch bytes without changing or applying them."""

    if not isinstance(patch, bytes):
        raise TypeError("patch must be bytes")
    text = patch.decode("utf-8", errors="strict")
    lines = text.splitlines()
    findings: set[str] = set()

    diff_paths: list[tuple[str, str]] = []
    old_headers: list[str] = []
    new_headers: list[str] = []
    target_paths: set[str] = set()
    hunk_starts: list[tuple[int, re.Match[str]]] = []

    for index, line in enumerate(lines):
        if line.startswith("diff --git "):
            match = _DIFF_HEADER.fullmatch(line)
            if match is None:
                findings.add(MALFORMED_FILE_HEADER)
            else:
                diff_paths.append((match.group("left"), match.group("right")))
        elif line.startswith("--- "):
            match = _OLD_HEADER.fullmatch(line)
            if match is None:
                findings.add(MALFORMED_FILE_HEADER)
            else:
                old_headers.append(match.group("path"))
        elif line.startswith("+++ "):
            match = _NEW_HEADER.fullmatch(line)
            if match is None:
                findings.add(MALFORMED_FILE_HEADER)
            else:
                value = match.group("path")
                new_headers.append(value)
                if value != "/dev/null":
                    target_paths.add(value[2:])
        elif line.startswith("@@"):
            match = _HUNK_HEADER.fullmatch(line)
            if match is None:
                findings.add(MALFORMED_HUNK_HEADER)
            else:
                hunk_starts.append((index, match))

    if not diff_paths:
        findings.add(NO_SUPPORTED_DIFF_HEADER)
    if not old_headers or not new_headers:
        findings.add(MISSING_FILE_HEADER)
    if not hunk_starts:
        findings.add(MISSING_HUNK_HEADER)
    if not patch.endswith(b"\n"):
        findings.add(TRUNCATED_PATCH)

    expected_paths = set(proposed_paths)
    diff_target_paths = {right for _left, right in diff_paths}
    if (target_paths and target_paths != expected_paths) or (
        diff_target_paths and diff_target_paths != expected_paths
    ):
        findings.add(WRONG_TARGET_PATH)

    hunks: list[HunkForensics] = []
    for position, (start, match) in enumerate(hunk_starts):
        limit = hunk_starts[position + 1][0] if position + 1 < len(hunk_starts) else len(lines)
        body: list[str] = []
        for line in lines[start + 1 : limit]:
            if line.startswith("diff --git "):
                break
            body.append(line)
        context = tuple(line[1:] for line in body if line.startswith(" "))
        removed = tuple(line[1:] for line in body if line.startswith("-") and not line.startswith("---"))
        added = tuple(line[1:] for line in body if line.startswith("+") and not line.startswith("+++"))
        invalid = tuple(
            line
            for line in body
            if not line.startswith((" ", "+", "-", "\\"))
        )
        if invalid:
            findings.add(INVALID_CONTEXT)
        observed_old = len(context) + len(removed)
        observed_new = len(context) + len(added)
        old_count = int(match.group("old_count") or 1)
        new_count = int(match.group("new_count") or 1)
        if old_count != observed_old or new_count != observed_new:
            findings.add(INCORRECT_HUNK_COUNTS)
        hunks.append(
            HunkForensics(
                header=lines[start],
                old_start=int(match.group("old_start")),
                old_count=old_count,
                new_start=int(match.group("new_start")),
                new_count=new_count,
                observed_old_lines=observed_old,
                observed_new_lines=observed_new,
                context_lines=len(context),
                context_content=context,
                removed_lines=removed,
                added_lines=added,
                invalid_lines=invalid,
            )
        )

    return PatchForensics(
        patch_sha256=hashlib.sha256(patch).hexdigest(),
        byte_count=len(patch),
        terminal_newline=patch.endswith(b"\n"),
        diff_paths=tuple(diff_paths),
        old_headers=tuple(old_headers),
        new_headers=tuple(new_headers),
        target_paths=tuple(sorted(target_paths)),
        hunks=tuple(hunks),
        findings=tuple(sorted(findings)),
    )


def canonical_unified_diff(path: str, before: bytes | None, after: bytes) -> bytes:
    """Build one deterministic evaluator control from explicit before/after bytes."""

    if not path or path.startswith("/") or ".." in path.split("/"):
        raise ValueError("canonical control path must be repository-relative")
    if before is not None and not before.endswith(b"\n"):
        raise ValueError("canonical control requires newline-terminated source")
    if not after.endswith(b"\n"):
        raise ValueError("canonical control requires newline-terminated result")
    old_lines = [] if before is None else before.decode("utf-8").splitlines()
    new_lines = after.decode("utf-8").splitlines()
    header = [f"diff --git a/{path} b/{path}"]
    if before is None:
        header.extend(("new file mode 100644", "--- /dev/null", f"+++ b/{path}"))
        body = [f"@@ -0,0 +1,{len(new_lines)} @@", *(f"+{line}" for line in new_lines)]
    else:
        if len(old_lines) != len(new_lines):
            raise ValueError("v1 forensic control supports equal-length replacement only")
        changed = [index for index, pair in enumerate(zip(old_lines, new_lines)) if pair[0] != pair[1]]
        if not changed:
            raise ValueError("canonical control requires a changed result")
        header.extend((f"--- a/{path}", f"+++ b/{path}"))
        body = [f"@@ -1,{len(old_lines)} +1,{len(new_lines)} @@"]
        for old, new in zip(old_lines, new_lines):
            if old == new:
                body.append(f" {old}")
            else:
                body.extend((f"-{old}", f"+{new}"))
    return ("\n".join((*header, *body)) + "\n").encode("utf-8")
