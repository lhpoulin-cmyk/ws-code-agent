"""Canonical generation-attempt states and compatibility helpers."""

from __future__ import annotations

from dataclasses import dataclass

CLASSIFIER_VERSION = "generation-failure-taxonomy-v1"

STATES = frozenset((
    "REQUEST_NOT_STARTED", "QUEUED", "RUNNING", "COMPLETED", "INTERRUPTED",
    "REQUEST_TIMEOUT", "OLLAMA_UNAVAILABLE", "OLLAMA_HTTP_ERROR", "EMPTY_RESPONSE",
    "MALFORMED_JSON", "RESPONSE_SCHEMA_INVALID", "PROPOSAL_FIELD_MISSING",
    "TASK_ADHERENCE_FAILED", "NORMALIZATION_FAILURE", "PERSISTENCE_FAILURE",
    "RENDER_FAILURE", "STALE_SOURCE",
))
TERMINAL_STATES = frozenset(STATES) - {"REQUEST_NOT_STARTED", "QUEUED", "RUNNING"}
ATTENTION_STATES = frozenset(STATES) - {"REQUEST_NOT_STARTED", "QUEUED", "RUNNING", "COMPLETED"}
ALLOWED_TRANSITIONS = frozenset(
    [("REQUEST_NOT_STARTED", "QUEUED"), ("QUEUED", "RUNNING"), ("QUEUED", "INTERRUPTED")]
    + [("RUNNING", target) for target in TERMINAL_STATES]
)

# Existing records remain physically unchanged. This map only interprets their
# legacy mutable status/error_class pair for current-state presentation.
LEGACY_STATE_MAP = {
    "FAILED:REQUEST_TIMEOUT": "REQUEST_TIMEOUT",
    "FAILED:OLLAMA_UNAVAILABLE": "OLLAMA_UNAVAILABLE",
    "FAILED:OLLAMA_HTTP_ERROR": "OLLAMA_HTTP_ERROR",
    "FAILED:EMPTY_RESPONSE": "EMPTY_RESPONSE",
    "FAILED:RESPONSE_SCHEMA_INVALID": "RESPONSE_SCHEMA_INVALID",
    "FAILED:PROPOSAL_FIELD_MISSING": "PROPOSAL_FIELD_MISSING",
    "FAILED:TASK_ADHERENCE_FAILED": "TASK_ADHERENCE_FAILED",
    "FAILED:NORMALIZATION_FAILURE": "NORMALIZATION_FAILURE",
    "FAILED:PERSISTENCE_FAILURE": "PERSISTENCE_FAILURE",
    "FAILED:RENDER_FAILURE": "RENDER_FAILURE",
    "FAILED:UNKNOWN_FAILURE": "INTERRUPTED",
    "FAILED:": "INTERRUPTED",
    "STALE_SOURCE:": "STALE_SOURCE",
    "INTERRUPTED:": "INTERRUPTED",
    "REQUEST_TIMEOUT:REQUEST_TIMEOUT": "REQUEST_TIMEOUT",
    "COMPLETED:": "COMPLETED",
    "RUNNING:": "RUNNING",
    "QUEUED:": "QUEUED",
}


def canonical_state(status: str | None, error_class: str | None = "", explicit: str | None = "") -> str:
    if explicit in STATES:
        return explicit
    status, error_class = status or "", error_class or ""
    if status in STATES:
        return status
    mapped = LEGACY_STATE_MAP.get(f"{status}:{error_class}") or LEGACY_STATE_MAP.get(f"{status}:")
    return mapped or "INTERRUPTED"


@dataclass(frozen=True)
class FailureClassification:
    state: str
    safe_detail: str
    retry_allowed: bool


def classify_error(error_class: str, detail: str = "") -> FailureClassification:
    state = error_class if error_class in STATES else "INTERRUPTED"
    return FailureClassification(state, detail or default_detail(state), state in ATTENTION_STATES)


def default_detail(state: str) -> str:
    return {
        "REQUEST_TIMEOUT": "The local model request exceeded its bounded time limit.",
        "OLLAMA_UNAVAILABLE": "The local model service could not be reached.",
        "OLLAMA_HTTP_ERROR": "The local model service returned an unsuccessful HTTP response.",
        "EMPTY_RESPONSE": "The model exchange completed without a usable response body.",
        "MALFORMED_JSON": "The response body was not valid JSON.",
        "RESPONSE_SCHEMA_INVALID": "The JSON response did not match the required response schema.",
        "PROPOSAL_FIELD_MISSING": "The structured response did not contain a usable proposal.",
        "TASK_ADHERENCE_FAILED": "The proposal did not follow the document-editing contract.",
        "NORMALIZATION_FAILURE": "The valid response could not be normalized deterministically.",
        "PERSISTENCE_FAILURE": "The result could not be completely saved to the review record.",
        "RENDER_FAILURE": "The saved result could not be displayed by the normal review page.",
        "STALE_SOURCE": "The source changed before the result could be applied.",
        "INTERRUPTED": "The attempt did not reach a terminal result before execution stopped.",
    }.get(state, "The attempt state is recorded in the preserved lifecycle evidence.")
