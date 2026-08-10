"""Bounded model projection of executor-observed patch rejection facts."""

from __future__ import annotations

import re
from typing import Any


MAX_EXECUTOR_FEEDBACK_CHARS = 2_048
_ABSOLUTE_PATH_TOKEN = re.compile(r"(?<![A-Za-z0-9_.-])/(?:[^\s\x00'\"`]+)")


def bounded_executor_feedback(classification: str, observed: dict[str, Any], roots: tuple[str, ...]) -> dict[str, Any]:
    feedback: dict[str, Any] = {"origin": "executor", "classification": classification}
    detail = _safe_executor_text(observed.get("detail"), roots)
    if detail:
        feedback["detail"] = detail
    exit_code = observed.get("exit_code")
    if isinstance(exit_code, int):
        feedback["exit_code"] = exit_code
    stderr = _safe_executor_text(observed.get("stderr"), roots)
    if stderr:
        feedback["stderr"] = stderr
    return feedback


def _safe_executor_text(value: Any, roots: tuple[str, ...]) -> str:
    if not isinstance(value, str):
        return ""
    text = value
    protected_roots = (
        *roots,
        "/home/louis/lab-root-trust",
        "/home/louis/.local/share/ws-code-agent/alpha-private",
        "/home/louis/src/ws-code-agent",
    )
    for root in sorted((root for root in protected_roots if root), key=len, reverse=True):
        text = text.replace(root, "<path-redacted>")
    return _ABSOLUTE_PATH_TOKEN.sub("<path-redacted>", text)[:MAX_EXECUTOR_FEEDBACK_CHARS]
