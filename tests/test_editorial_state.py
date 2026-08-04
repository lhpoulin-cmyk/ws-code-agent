from docwriter_web.editorial_state import derive_editorial_state


def a():
    return {"attempt_id": "attempt-1", "status": "COMPLETED", "normalized_proposal": "proposal", "source_version_id": 1, "source_sha256": "source", "proposal_sha256": "proposal"}


def e(stage, decision, n):
    return {"event_id": str(n), "event_type": "REVIEW_TARGET_SELECTED" if stage == "TARGET" else stage + "_REVIEW", "stage": stage, "decision": decision, "created_at": str(n), "stream_id": "editorial:trial:attempt-1", "generation_attempt_id": "attempt-1", "source_version_id": 1, "source_sha256": "source", "proposal_sha256": "proposal"}


def test_editorial_state_progression_and_blocking():
    trial = {"trial_id": "trial"}
    assert derive_editorial_state(trial, [], []).state == "GENERATION_REQUIRED"
    target = e("TARGET", "SELECTED", 1)
    assert derive_editorial_state(trial, [a()], []).state == "REVIEW_TARGET_REQUIRED"
    assert derive_editorial_state(trial, [a()], [target]).state == "INTEGRITY_REVIEW_REQUIRED"
    integrity = e("INTEGRITY", "INTEGRITY_ACCEPTED", 2)
    assert derive_editorial_state(trial, [a()], [target, integrity]).state == "REVISION_REVIEW_REQUIRED"
    revision = e("REVISION", "READY_FOR_TONE_REVIEW", 3)
    assert derive_editorial_state(trial, [a()], [target, integrity, revision]).state == "TONE_REVIEW_REQUIRED"
    tone = e("TONE", "TONE_ACCEPTED", 4)
    assert derive_editorial_state(trial, [a()], [target, integrity, revision, tone]).state == "READY_FOR_BASELINE_ACCEPTANCE"
    assert derive_editorial_state(trial, [a()], [target, e("INTEGRITY", "INTEGRITY_ISSUE", 2)]).state == "INTEGRITY_ISSUE_UNRESOLVED"
