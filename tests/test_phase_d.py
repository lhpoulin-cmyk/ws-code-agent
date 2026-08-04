import json
import sqlite3

from docwriter_web.editorial_state import derive_editorial_state
from test_generation import FakeClient, make_app, make_trial, request, result_for


def attempt(state="COMPLETED"):
    return {"attempt_id": "attempt-1", "status": state, "normalized_proposal": "A proposal.", "source_version_id": 1, "source_sha256": "source-hash", "proposal_sha256": "proposal-hash"}


def event(stage, decision, event_id, stream="editorial:trial:attempt-1"):
    return {"event_type": "REVIEW_TARGET_SELECTED" if stage == "TARGET" else stage + "_REVIEW", "stage": stage, "decision": decision, "event_id": event_id, "created_at": event_id, "stream_id": stream, "generation_attempt_id": "attempt-1", "source_version_id": 1, "source_sha256": "source-hash", "proposal_sha256": "proposal-hash"}


def test_derived_editorial_states_are_independent():
    trial = {"trial_id": "trial", "review_status": "REVIEW_REQUIRED"}
    a = attempt()
    assert derive_editorial_state(trial, [], []).state == "GENERATION_REQUIRED"
    assert derive_editorial_state(trial, [a], []).state == "REVIEW_TARGET_REQUIRED"
    target = event("TARGET", "SELECTED", "1")
    assert derive_editorial_state(trial, [a], [target]).state == "INTEGRITY_REVIEW_REQUIRED"
    integrity = event("INTEGRITY", "INTEGRITY_ACCEPTED", "2")
    assert derive_editorial_state(trial, [a], [target, integrity]).state == "REVISION_REVIEW_REQUIRED"
    revision = event("REVISION", "READY_FOR_TONE_REVIEW", "3")
    assert derive_editorial_state(trial, [a], [target, integrity, revision]).state == "TONE_REVIEW_REQUIRED"
    tone = event("TONE", "TONE_ACCEPTED", "4")
    assert derive_editorial_state(trial, [a], [target, integrity, revision, tone]).state == "READY_FOR_BASELINE_ACCEPTANCE"
    assert derive_editorial_state(trial, [a], [target, event("INTEGRITY", "INTEGRITY_ISSUE", "2")]).state == "INTEGRITY_ISSUE_UNRESOLVED"
    assert derive_editorial_state(trial, [a], [target, integrity, event("REVISION", "REVISION_REQUIRED", "3")]).state == "REVISION_REQUIRED"
    assert derive_editorial_state(trial, [a], [target, integrity, revision, event("TONE", "TONE_REVISION_REQUIRED", "4")]).state == "TONE_REVISION_REQUIRED"


def test_staged_review_sequence_binds_exact_attempt_and_creates_no_baseline(tmp_path):
    app = make_app(tmp_path); trial_id = make_trial(app); source = "The observed service remains local and review is unresolved."
    app.ollama_client = FakeClient(result_for(source))
    assert request(app, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        attempt_id, version_id, source_hash, proposal_hash = db.execute("select attempt_id,source_version_id,source_sha256,proposal_sha256 from generation_attempts").fetchone()
    assert request(app, f"/trial/{trial_id}/review-target", "POST", {"attempt_id": attempt_id, "csrf": "x"})["status"].startswith("303")
    assert request(app, f"/trial/{trial_id}/integrity-review", "POST", {"outcome": "INTEGRITY_ACCEPTED", "note_text": "Checked facts and uncertainty.", "csrf": "x"})["status"].startswith("303")
    assert request(app, f"/trial/{trial_id}/revision-review", "POST", {"outcome": "READY_FOR_TONE_REVIEW", "csrf": "x"})["status"].startswith("303")
    assert request(app, f"/trial/{trial_id}/tone-review", "POST", {"outcome": "TONE_ACCEPTED", "note_text": "Sounds like the intended voice.", "csrf": "x"})["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        rows = db.execute("select event_type,stage,decision,source_version_id,source_sha256,proposal_sha256 from review_events where trial_id=? and stream_id is not null order by sequence_number", (trial_id,)).fetchall()
        assert [r[0] for r in rows] == ["REVIEW_TARGET_SELECTED", "INTEGRITY_REVIEW", "REVISION_REVIEW", "TONE_REVIEW"]
        assert all(r[3:] == (version_id, source_hash, proposal_hash) for r in rows)
        assert db.execute("select name from sqlite_master where type='table' and name='accepted_baselines'").fetchone() is None


def test_private_steering_is_hidden_until_csrf_protected_reveal(tmp_path):
    app = make_app(tmp_path); trial_id = make_trial(app)
    saved = request(app, f"/trial/{trial_id}/review", "POST", {"note_text": "Private synthetic aside.", "private_steering": "1", "csrf": "x"})
    assert saved["status"].startswith("303")
    page = request(app, f"/project/alpha/trial/{trial_id}")["body"]
    assert "Private synthetic aside." not in page and "Private steering recorded" in page
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        event_id = db.execute("select event_id from review_events where private_steering=1").fetchone()[0]
    denied = request(app, f"/trial/{trial_id}/private-steering/{event_id}/reveal", "POST", {"csrf": "wrong"})
    assert denied["status"].startswith("403")
    revealed = request(app, f"/trial/{trial_id}/private-steering/{event_id}/reveal", "POST", {"csrf": "x"})
    assert revealed["status"].startswith("200") and "Private synthetic aside." in revealed["body"]
