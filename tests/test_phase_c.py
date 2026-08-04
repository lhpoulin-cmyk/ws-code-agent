import json
import os
import stat

from docwriter_web.failure_taxonomy import (
    ALLOWED_TRANSITIONS,
    CLASSIFIER_VERSION,
    STATES,
    TERMINAL_STATES,
    canonical_state,
)
from docwriter_web.recovery_guidance import guidance_for
from docwriter_web.recovery_spool import read_spool, write_spool


def _trial():
    return {"trial_id": "trial-c", "review_status": "REVIEW_REQUIRED", "lifecycle_state": "ACTIVE", "source_state": "PRESENT", "project_slug": "alpha", "project_id": "project-alpha", "integrity_findings": "[]"}


def _attempt(state):
    return {"attempt_id": f"attempt-{state.lower()}", "status": state, "canonical_failure_class": state, "error_class": state, "normalized_proposal": "" if state not in {"COMPLETED"} else "proposal", "prompt_version": "conversational-proposal-v2", "presentation_result": "not_applicable"}


def test_taxonomy_contains_every_authoritative_state_and_legacy_mapping():
    assert len(STATES) == 17
    assert TERMINAL_STATES == STATES - {"REQUEST_NOT_STARTED", "QUEUED", "RUNNING"}
    assert canonical_state("FAILED", "REQUEST_TIMEOUT") == "REQUEST_TIMEOUT"
    assert canonical_state("FAILED", "UNKNOWN_FAILURE") == "INTERRUPTED"
    assert ("RUNNING", "MALFORMED_JSON") in ALLOWED_TRANSITIONS
    assert ("COMPLETED", "INTERRUPTED") not in ALLOWED_TRANSITIONS
    assert CLASSIFIER_VERSION == "generation-failure-taxonomy-v1"


def test_every_failure_state_has_precise_guidance():
    for state in sorted(TERMINAL_STATES - {"COMPLETED"}):
        result = guidance_for(_trial(), [_attempt(state)])
        assert result.guidance_id == state
        assert result.title and result.explanation and result.preserved_work and result.primary_action_url
        assert "something went wrong" not in " ".join((result.title, result.explanation)).lower()
        assert "unknown error" not in " ".join((result.title, result.explanation)).lower()


def test_recovery_spool_is_restricted_and_never_replayable(tmp_path):
    path = write_spool(tmp_path, "generation-persistence", {"request_json": "{}", "raw_response": "{}", "source_sha256": "hash"})
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    value = read_spool(path)
    assert value["attempt_id"] == "generation-persistence"
    assert value["replay"] is False

