import sqlite3

import pytest

from docwriter_web.baselines import current_baseline
from test_generation import FakeClient, make_app, make_trial, request, result_for


def staged_app(tmp_path):
    app = make_app(tmp_path)
    trial_id = make_trial(app)
    source = "The observed service remains local and review is unresolved."
    app.ollama_client = FakeClient(result_for(source))
    request(app, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        attempt_id = db.execute("select attempt_id from generation_attempts where trial_id=?", (trial_id,)).fetchone()[0]
    request(app, f"/trial/{trial_id}/review-target", "POST", {"attempt_id": attempt_id, "csrf": "x"})
    request(app, f"/trial/{trial_id}/integrity-review", "POST", {"outcome": "INTEGRITY_ACCEPTED", "note_text": "Evidence checked.", "csrf": "x"})
    request(app, f"/trial/{trial_id}/revision-review", "POST", {"outcome": "READY_FOR_TONE_REVIEW", "csrf": "x"})
    request(app, f"/trial/{trial_id}/tone-review", "POST", {"outcome": "TONE_ACCEPTED", "note_text": "Voice checked.", "csrf": "x"})
    return app, trial_id


def test_baseline_acceptance_is_atomic_and_immutable(tmp_path):
    app, trial_id = staged_app(tmp_path)
    accepted = request(app, f"/trial/{trial_id}/baseline/accept", "POST", {"confirm_baseline": "1", "acceptance_note": "Phase E synthetic acceptance.", "csrf": "x"})
    assert accepted["status"].startswith("303")
    location = dict(accepted["headers"])["Location"]
    detail = request(app, location)
    assert detail["status"].startswith("200") and "accepted conversational baseline" in detail["body"].lower()
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        baseline_id, proposal = db.execute("select baseline_id,accepted_proposal from accepted_baselines where trial_id=?", (trial_id,)).fetchone()
        assert db.execute("select count(*) from review_events where trial_id=? and event_type='BASELINE_ACCEPT'", (trial_id,)).fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError): db.execute("update accepted_baselines set acceptance_note='changed' where baseline_id=?", (baseline_id,))
        with pytest.raises(sqlite3.IntegrityError): db.execute("delete from accepted_baselines where baseline_id=?", (baseline_id,))
        assert db.execute("select accepted_proposal from accepted_baselines where baseline_id=?", (baseline_id,)).fetchone()[0] == proposal


def test_baseline_requires_explicit_confirmation_and_legacy_has_none(tmp_path):
    app, trial_id = staged_app(tmp_path)
    denied = request(app, f"/trial/{trial_id}/baseline/accept", "POST", {"csrf": "x"})
    assert denied["status"].startswith("400")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("select count(*) from accepted_baselines where trial_id=?", (trial_id,)).fetchone()[0] == 0


def test_baseline_chain_has_one_current_and_preserves_supersession():
    rows = [
        {"baseline_id": "b1", "trial_id": "t", "supersedes_baseline_id": None},
        {"baseline_id": "b2", "trial_id": "t", "supersedes_baseline_id": "b1"},
    ]
    assert current_baseline(rows)["baseline_id"] == "b2"
    with pytest.raises(ValueError): current_baseline(rows + [{"baseline_id": "b3", "trial_id": "t", "supersedes_baseline_id": "b1"}])
