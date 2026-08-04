"""Deterministic operator-recovery guidance derived from preserved state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from .failure_taxonomy import canonical_state
from .editorial_state import derive_editorial_state


@dataclass(frozen=True)
class Guidance:
    guidance_id: str
    severity: str
    title: str
    explanation: str
    preserved_work: str
    why_it_matters: str
    primary_action_label: str | None
    primary_action_url: str | None
    secondary_action_label: str | None = None
    secondary_action_url: str | None = None
    target_section_id: str | None = None
    technical_details: str | None = None


def _value(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return default


def _base(project_slug: str | None, trial_id: str) -> str:
    return f"/project/{project_slug}/trial/{trial_id}" if project_slug else f"/trial/{trial_id}"


def guidance_for(
    trial: Any,
    attempts: Iterable[Any] = (),
    review_events: Iterable[Any] = (),
    project_slug: str | None = None,
    tone_available: bool = False,
    audience_available: bool = False,
    baselines: Iterable[Any] = (),
) -> Guidance:
    """Return the next safe action without adding workflow authority."""
    trial_id = str(_value(trial, "trial_id", "unknown"))
    base = _base(project_slug or _value(trial, "project_slug"), trial_id)
    state = _value(trial, "lifecycle_state", "ACTIVE")
    source_state = _value(trial, "source_state", "PRESENT")
    recovery_state = _value(trial, "recovery_state")
    if not (project_slug or _value(trial, "project_slug")) and _value(trial, "project_id", "__missing__") is None:
        return Guidance(
            "MISSING_PROJECT_CONTEXT", "neutral", "This historical trial was recovered from surviving evidence.",
            "Some original project information is unavailable, but the preserved attempts and provenance remain accessible.",
            "The surviving trial history remains available without manufactured project or source context.",
            "This keeps the record precise about what can and cannot be verified.",
            "View preserved history", f"{base}#generation-attempts", target_section_id="generation-attempts",
        )
    if state == "ARCHIVED" and (source_state != "PRESENT" or recovery_state == "PROVENANCE_ONLY"):
        return Guidance(
            "PROVENANCE_ONLY", "neutral", "This historical trial was recovered from surviving evidence.",
            "Some original project information is unavailable, but the preserved attempts and provenance remain accessible.",
            "The surviving attempt identifiers, timestamps, hashes, and model metadata remain available.",
            "This keeps the historical record useful without manufacturing missing prose.",
            "View preserved history", f"{base}#provenance", target_section_id="provenance",
        )
    if state == "ARCHIVED":
        return Guidance(
            "ARCHIVED_TRIAL", "neutral", "This trial is archived.",
            "Its source, attempts, and review history remain preserved, but it is not part of the active review queue.",
            "The trial and its child history remain intact.",
            "Restore it when this work should return to active review.",
            "Restore trial", f"{base}#archive-actions", "View history", f"{base}#generation-attempts", "archive-actions",
        )

    attempts = list(attempts)
    events = list(review_events)
    attempt = attempts[0] if attempts else None
    editorial = derive_editorial_state(trial, attempts, events, baselines)
    editorial_messages = {
        "REVIEW_TARGET_REQUIRED": ("This trial has more than one completed proposal, or no durable review target has been chosen.", "Earlier attempts and decisions remain preserved.", "Choose the exact proposal that should receive staged review.", "Choose proposal", f"{base}#editorial-target"),
        "INTEGRITY_REVIEW_REQUIRED": ("A proposal is ready. First check whether it preserves the facts, authority, uncertainty, and meaning of the source.", "The source, proposal, findings, and exact hashes remain preserved.", "Integrity review must come before meaning review.", "Review integrity", f"{base}#integrity-review"),
        "INTEGRITY_ISSUE_UNRESOLVED": ("An integrity issue is still open.", "The source and proposal are preserved.", "Confirm or explain the issue before moving to revision review.", "Return to integrity review", f"{base}#integrity-review"),
        "REVISION_REVIEW_REQUIRED": ("Integrity has been accepted. Now check whether the proposal still says what you meant and whether anything important was lost.", "The exact reviewed source and proposal remain preserved.", "Meaning review is separate from tone review.", "Review revision", f"{base}#revision-review"),
        "REVISION_REQUIRED": ("The proposal needs another meaning or content revision.", "The reviewed source, proposal, and rationale remain preserved.", "Record the next revision rationale before starting another attempt.", "Review revision feedback", f"{base}#revision-review"),
        "REVISION_REJECTED": ("This proposal was rejected for staged review.", "The proposal and rejection rationale remain preserved.", "Choose another completed attempt if one is available.", "View review history", f"{base}#review-history"),
        "TONE_REVIEW_REQUIRED": ("The proposal passed the meaning check. The next step is deciding whether it sounds like you.", "Meaning, integrity, and the exact proposal remain preserved.", "Tone is an independent human judgment.", "Review tone", f"{base}#tone-review"),
        "TONE_REVISION_REQUIRED": ("The meaning is acceptable, but the voice still needs work.", "Your tone notes and preferred wording are preserved.", "Use the tone feedback to guide a later explicit revision.", "Review tone feedback", f"{base}#tone-review"),
        "TONE_REJECTED": ("This proposal was rejected as a basis for the operator's voice.", "The proposal and tone rationale remain preserved.", "Choose another completed attempt if one is available.", "View review history", f"{base}#review-history"),
        "READY_FOR_BASELINE_ACCEPTANCE": ("Meaning and tone have both been accepted.", "Your reviewed proposal and complete history are preserved.", "Accepting this exact proposal will preserve it as the conversational baseline.", "Review and accept baseline", f"{base}#baseline-acceptance"),
        "BASELINE_ACCEPTED": ("This conversational version is now the accepted baseline.", "Its source, proposal, and review history are preserved together.", "Audience adaptations are the next editorial step, but they are not available in this version yet.", "View accepted baseline", f"{base}#baseline-history"),
    }
    if editorial.state in editorial_messages:
        title, preserved, why, label, url = editorial_messages[editorial.state]
        return Guidance(editorial.state, "attention" if editorial.state not in {"READY_FOR_BASELINE_ACCEPTANCE", "BASELINE_ACCEPTED"} else "neutral", title, preserved, preserved, why, label, url, target_section_id=url.rsplit("#", 1)[-1], technical_details=f"{editorial.state} · {editorial.target_attempt_id or 'target required'}")
    status = _value(trial, "review_status", "REVIEW_REQUIRED")
    notes = any(_value(event, "event_type") == "REVIEW_NOTE" and str(_value(event, "note_text", "") or "").strip() for event in events)
    if status in {"REJECTED", "REVISION_REQUIRED"} and not notes:
        label = "Add rejection note" if status == "REJECTED" else "Add revision note"
        title = "This revision was marked rejected, but no reason was saved." if status == "REJECTED" else "This revision requires changes, but no reason was saved."
        return Guidance(
            "REVIEW_RATIONALE_MISSING", "attention", title,
            "The source, proposal, and original decision are still preserved.",
            "A short reason keeps this result useful when the writer is tuned later.",
            "The next reviewer needs the reason at the existing review surface.",
            label, f"{base}#review-rationale", target_section_id="review-rationale",
        )
    if attempt is None:
        return Guidance(
            "GENERATION_NOT_STARTED", "next", "This trial has a saved source paragraph, but the writer has not been run yet.",
            "Your draft is safe.", "The saved source remains available for this trial.",
            "A generation attempt is needed before there is a proposal to review.",
            "Generate conversational proposal", f"{base}#generation-attempts", target_section_id="generation-attempts",
        )

    attempt_status = _value(attempt, "status", "UNKNOWN")
    error_class = _value(attempt, "error_class", "") or ""
    failure_state = canonical_state(attempt_status, error_class, _value(attempt, "canonical_failure_class", "") or "")
    technical = f"{error_class or attempt_status} · {_value(attempt, 'attempt_id', 'unknown')}"
    reconciliation_id = _value(attempt, "reconciliation_id")
    replacement_attempt_id = _value(attempt, "replacement_attempt_id")
    if _value(attempt, "kind", "CONVERSATIONAL") == "AUDIENCE" and reconciliation_id and replacement_attempt_id:
        return Guidance(
            "AUDIENCE_FAILURE_RECONCILED", "neutral",
            "This attempt used audience contract v1, which had a known response-format mismatch.",
            "The original response and failure remain preserved. A corrected v2 attempt is available.",
            "The original request, response, and provenance remain inspectable.",
            "The corrected attempt is operationally linked without rewriting or replaying this failure.",
            "View corrected v2 attempt", f"/trial/{trial_id}/attempt/{replacement_attempt_id}",
            "Compare v1 and v2 provenance", f"/trial/{trial_id}/audience-reconciliation/{reconciliation_id}",
            "generation-attempts", technical,
        )
    if _value(attempt, "kind", "CONVERSATIONAL") == "AUDIENCE" and _value(attempt, "original_attempt_id"):
        return Guidance(
            "AUDIENCE_CORRECTED_SUCCESSOR", "neutral",
            "This attempt is the corrected operational successor to a preserved audience-contract v1 failure.",
            "The earlier failure remains available as historical evidence.",
            "This v2 result has its own immutable request and review provenance.",
            "The replacement is not a replay or a rewrite of the original attempt.",
            "View original v1 evidence", f"/trial/{trial_id}/attempt/{_value(attempt, 'original_attempt_id')}",
            target_section_id="generation-attempts", technical_details=technical,
        )
    if _value(attempt, "kind", "CONVERSATIONAL") == "AUDIENCE" and failure_state == "RESPONSE_SCHEMA_INVALID":
        return Guidance(
            "AUDIENCE_RESPONSE_SCHEMA_INVALID", "attention",
            "The model returned an audience version, but one integrity finding did not match the required review format.",
            "The original response and full attempt history are preserved.",
            "The baseline, request, response, and provenance remain available for inspection.",
            "The audience response must use the shared integrity categories and finding structure before it can enter review.",
            "View preserved response", f"{base}#generation-attempts", "Create new attempt", f"{base}#generation-attempts", "generation-attempts", technical,
        )
    if failure_state == "QUEUED":
        return Guidance("QUEUED", "next", "This generation request is queued for execution.", "Your source version and request details are preserved.", "The queued request remains attached to this trial.", "The writer must begin this request before a result can be reviewed.", "View attempt status", f"{base}#generation-attempts", target_section_id="generation-attempts", technical_details=technical)
    if attempt_status == "RUNNING":
        return Guidance(
            "GENERATION_RUNNING", "next", "The writer is working on this attempt.",
            "Your source version is locked for this run, so later edits will not change what the model received.",
            "The request and source-version provenance are preserved.", "The attempt must finish before another one is started.",
            "View attempt status", f"{base}#generation-attempts", target_section_id="generation-attempts", technical_details=technical,
        )
    failure_messages = {
        "REQUEST_TIMEOUT": ("This attempt ran longer than the allowed time and was stopped.", "The request and any response received are preserved.", "A new attempt can be started without changing this evidence.", "Create new attempt"),
        "OLLAMA_HTTP_ERROR": ("The local model service returned an unsuccessful response.", "The request and returned response evidence are preserved.", "A new attempt should wait for the service response to be understood.", "Create new attempt"),
        "EMPTY_RESPONSE": ("The model exchange completed without a usable response body.", "The request and exchange telemetry are preserved.", "A new attempt is separate from this incomplete exchange.", "Create new attempt"),
        "MALFORMED_JSON": ("The model returned a response, but Doc Writer could not read it as valid JSON.", "The original response is preserved.", "The preserved response can show what the next attempt must avoid.", "View preserved response"),
        "RESPONSE_SCHEMA_INVALID": ("The model returned JSON, but it did not match Doc Writer's response schema.", "The request and raw response are preserved.", "The response must be schema-valid before it can become a proposal.", "View preserved response"),
        "PROPOSAL_FIELD_MISSING": ("The structured response did not contain a usable proposal.", "The response and request provenance are preserved.", "A proposal is needed before meaning review can begin.", "View preserved response"),
        "TASK_ADHERENCE_FAILED": ("The model returned a proposal, but it did not follow the editing contract.", "The response and contract findings are preserved and were not accepted as a revision.", "The next attempt must keep the source as delimited editing input.", "View contract findings"),
        "NORMALIZATION_FAILURE": ("The model response was received, but Doc Writer could not normalize it deterministically.", "The raw response and request provenance are preserved.", "Normalization must be repeatable before the result can enter review.", "View preserved response"),
        "PERSISTENCE_FAILURE": ("Doc Writer received a result but could not finish saving it to the normal review record.", "Recovery evidence is preserved locally for reconciliation.", "Review recovery status before starting any new attempt.", "Review recovery status"),
        "RENDER_FAILURE": ("The result was saved, but Doc Writer could not display the normal review page.", "The writing and provenance remain preserved.", "Use the fallback result view before deciding whether to retry.", "Open fallback result view"),
        "STALE_SOURCE": ("The source changed before this result could be applied.", "The request and received response remain preserved for this source version.", "A new attempt must use the current source explicitly.", "Create new attempt"),
        "INTERRUPTED": ("This attempt did not reach a completed result before execution stopped.", "The request and any response received so far are preserved.", "Starting again creates a new attempt and leaves this one intact.", "Create new attempt"),
    }
    if failure_state in failure_messages:
        title, explanation, why, label = failure_messages[failure_state]
        if failure_state == "OLLAMA_UNAVAILABLE":
            return Guidance("OLLAMA_UNAVAILABLE", "attention", "Doc Writer could not reach the local model service.", "Your draft and this attempt are preserved. Generation can be tried again after the local model service is available.", "The failed request remains preserved.", "The local service must be available before a new attempt can run.", "Check system status", "/system", "Retry as new attempt", f"{base}#generation-attempts", "generation-attempts", technical)
        secondary_label = "Create new attempt" if failure_state not in {"PERSISTENCE_FAILURE", "RENDER_FAILURE"} else None
        secondary_url = f"{base}#generation-attempts" if secondary_label else None
        return Guidance(failure_state, "attention", title, explanation, explanation, why, label, f"{base}#generation-attempts", secondary_label, secondary_url, "generation-attempts", technical)
    if failure_state == "COMPLETED" and _value(attempt, "presentation_result", "not_applicable") == "failed":
        return Guidance("RENDER_FAILURE", "attention", "The result was saved, but Doc Writer could not display the normal review page.", "The writing and provenance remain preserved.", "The completed generation result remains intact.", "The fallback view separates presentation trouble from model failure.", "Open fallback result view", f"{base}/attempt/{_value(attempt, 'attempt_id')}" if _value(attempt, "attempt_id") else f"{base}#generation-attempts", target_section_id="generation-attempts", technical_details=technical)
    if failure_state == "OLLAMA_UNAVAILABLE":
        return Guidance(
            "OLLAMA_UNAVAILABLE", "attention", "Doc Writer could not reach the local model service.",
            "Your draft and this attempt are preserved. Generation can be tried again after the local model service is available.",
            "The failed request remains preserved.", "The local service must be available before a new attempt can run.",
            "Check system status", "/system", "Retry as new attempt", f"{base}#generation-attempts", "generation-attempts", technical,
        )
    if attempt_status in {"INTERRUPTED", "STALE_SOURCE"} or error_class in {"REQUEST_TIMEOUT", "STUCK_RUNNING"}:
        return Guidance(
            "GENERATION_INTERRUPTED", "attention", "This attempt did not reach a completed result.",
            "The request and any response received so far are preserved.",
            "This attempt remains intact; starting again creates a new attempt.",
            "Starting a new attempt leaves this evidence available for comparison.",
            "Create new attempt", f"{base}#generation-attempts", "View preserved attempt", f"{base}#generation-attempts", "generation-attempts", technical,
        )
    if attempt_status == "COMPLETED" and not str(_value(attempt, "normalized_proposal", "") or "").strip():
        legacy = not error_class and str(_value(attempt, "prompt_version", "") or "").strip() != ""
        if legacy:
            return Guidance(
                "LEGACY_NO_NORMALIZATION", "neutral", "This attempt was created before normalized proposals were recorded.",
                "Its original response and provenance remain available.", "The completed attempt remains preserved.",
                "The history can be reviewed without automatically regenerating it.",
                "View attempt history", f"{base}#generation-attempts", target_section_id="generation-attempts", technical_details=technical,
            )
    if attempt_status == "FAILED" or (attempt_status == "COMPLETED" and not str(_value(attempt, "normalized_proposal", "") or "").strip()):
        return Guidance(
            "NO_NORMALIZED_PROPOSAL", "attention", "The model returned a response, but Doc Writer could not read it as a valid proposal.",
            "The raw response is preserved below.", "The source, request, and response evidence remain preserved.",
            "Reviewing the preserved response identifies what a later attempt needs to handle.",
            "View preserved response", f"{base}#generation-attempts", "Create new attempt", f"{base}#generation-attempts", "generation-attempts", technical,
        )
    try:
        findings = json.loads(_value(trial, "integrity_findings", "[]") or "[]")
    except (TypeError, ValueError):
        findings = []
    if findings and any(_value(finding, "category") != "no material issue found" for finding in findings):
        return Guidance(
            "INTEGRITY_REVIEW_REQUIRED", "attention", "The writer found a possible factual, authority, or ambiguity issue.",
            "Confirm or explain it before approving the revision. No source wording will be changed automatically.",
            "The source, findings, and proposal remain preserved.", "The finding needs an explicit operator review.",
            "Review integrity finding", f"{base}#integrity-review", target_section_id="integrity-review",
        )
    if status in {"REVIEW_REQUIRED", "REVISION_REQUIRED"}:
        return Guidance(
            "REVISION_REVIEW_REQUIRED", "next", "A proposal is ready for meaning review.",
            "First check that it still means what you meant and that no material detail was lost.",
            "The source, proposal, and review history remain preserved.", "Meaning review comes before any later editorial stage.",
            "Review revision", f"{base}#revision-review", target_section_id="revision-review",
        )
    if status == "ACCEPTED" and not tone_available:
        return Guidance(
            "TONE_REVIEW_UNAVAILABLE", "neutral", "Tone review is planned but not available in this version.",
            "The revision and your current review history remain preserved.",
            "The accepted conversational record remains available.", "Tone mechanics must exist before tone can be reviewed.",
            None, None, "View history", f"{base}#generation-attempts", "generation-attempts",
        )
    if status == "ACCEPTED" and tone_available and not audience_available:
        return Guidance(
            "AUDIENCE_WORK_UNAVAILABLE", "neutral", "Audience versions begin after one conversational version is accepted for both meaning and tone.",
            "The current conversational version remains preserved.", "The next stage depends on tone acceptance.",
            "Complete tone review before audience work becomes available.", "Return to tone review", f"{base}#tone-review", target_section_id="tone-review",
        )
    return Guidance(
        "UNKNOWN_NEXT_STEP", "neutral", "Doc Writer cannot determine the next step from the available record.",
        "The preserved history remains available.", "The available record does not support a more specific action.",
        "Reviewing the preserved history is the safest next step.", "View history", f"{base}#generation-attempts", target_section_id="generation-attempts",
    )
