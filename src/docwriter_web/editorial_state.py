"""Pure derived editorial state for the staged human review sequence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class EditorialState:
    state: str
    target_attempt_id: str | None = None
    target_source_version_id: int | None = None
    target_source_sha256: str | None = None
    target_proposal_sha256: str | None = None
    explanation: str = ""


def _value(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


def _latest(rows: list[Any], stage: str | None = None, event_type: str | None = None) -> Any | None:
    selected = [r for r in rows if (stage is None or _value(r, "stage") == stage) and (event_type is None or _value(r, "event_type") == event_type)]
    return sorted(selected, key=lambda r: (_value(r, "created_at", ""), _value(r, "event_id", "")))[-1] if selected else None


def derive_editorial_state(trial: Any, attempts: Iterable[Any], events: Iterable[Any]) -> EditorialState:
    completed = [a for a in attempts if _value(a, "status") == "COMPLETED" and str(_value(a, "normalized_proposal", "") or "").strip()]
    if not completed:
        return EditorialState("GENERATION_REQUIRED", explanation="A completed proposal is required before staged editorial review can begin.")
    targets = [e for e in events if _value(e, "event_type") == "REVIEW_TARGET_SELECTED"]
    target = _latest(targets)
    if target is None:
        return EditorialState("REVIEW_TARGET_REQUIRED", explanation="Choose the completed proposal that should receive the staged review.")
    attempt_id = _value(target, "generation_attempt_id")
    attempt = next((a for a in completed if _value(a, "attempt_id") == attempt_id), None)
    if attempt is None or any(_value(target, key) != _value(attempt, key) for key in ("source_version_id", "source_sha256", "proposal_sha256")):
        return EditorialState("REVIEW_TARGET_REQUIRED", explanation="The selected review target no longer matches a completed preserved attempt.")
    scoped = [e for e in events if _value(e, "stream_id") == _value(target, "stream_id")]
    integrity = _latest(scoped, "INTEGRITY")
    base = EditorialState("INTEGRITY_REVIEW_REQUIRED", attempt_id, _value(attempt, "source_version_id"), _value(attempt, "source_sha256"), _value(attempt, "proposal_sha256"), "Review the source, findings, and proposal before reviewing meaning.")
    if integrity is None:
        return base
    if _value(integrity, "decision") == "INTEGRITY_ISSUE":
        return EditorialState("INTEGRITY_ISSUE_UNRESOLVED", base.target_attempt_id, base.target_source_version_id, base.target_source_sha256, base.target_proposal_sha256, "An integrity issue remains unresolved.")
    revision = _latest(scoped, "REVISION")
    if revision is None:
        return EditorialState("REVISION_REVIEW_REQUIRED", base.target_attempt_id, base.target_source_version_id, base.target_source_sha256, base.target_proposal_sha256, "Integrity is accepted; review whether the proposal still means what the operator meant.")
    if _value(revision, "decision") == "REVISION_REQUIRED":
        return EditorialState("REVISION_REQUIRED", base.target_attempt_id, base.target_source_version_id, base.target_source_sha256, base.target_proposal_sha256, "The proposal needs another meaning or content revision.")
    if _value(revision, "decision") == "REJECTED":
        return EditorialState("REVISION_REJECTED", base.target_attempt_id, base.target_source_version_id, base.target_source_sha256, base.target_proposal_sha256, "This proposal was rejected for staged review.")
    tone = _latest(scoped, "TONE")
    if tone is None:
        return EditorialState("TONE_REVIEW_REQUIRED", base.target_attempt_id, base.target_source_version_id, base.target_source_sha256, base.target_proposal_sha256, "Meaning is accepted; review whether the proposal sounds like the operator.")
    if _value(tone, "decision") == "TONE_REVISION_REQUIRED":
        return EditorialState("TONE_REVISION_REQUIRED", base.target_attempt_id, base.target_source_version_id, base.target_source_sha256, base.target_proposal_sha256, "The meaning is acceptable, but the voice still needs work.")
    if _value(tone, "decision") == "TONE_REJECTED":
        return EditorialState("TONE_REJECTED", base.target_attempt_id, base.target_source_version_id, base.target_source_sha256, base.target_proposal_sha256, "This proposal was rejected as a basis for the operator's voice.")
    if _value(tone, "decision") == "TONE_ACCEPTED":
        return EditorialState("READY_FOR_BASELINE_ACCEPTANCE", base.target_attempt_id, base.target_source_version_id, base.target_source_sha256, base.target_proposal_sha256, "Meaning and tone have both been accepted; baseline acceptance is not available in this version.")
    return EditorialState("TONE_REVIEW_REQUIRED", base.target_attempt_id, base.target_source_version_id, base.target_source_sha256, base.target_proposal_sha256, "The tone review record does not contain a recognized outcome.")
