import sqlite3
import pytest

from docwriter_web.audience import AUDIENCE_VERSION, audience_schema, derived_state, parse_audience_response, profile_contract
from test_generation import make_app
from test_phase_e import staged_app
from test_generation import request, result_for


def test_three_seeded_profiles_are_repository_owned(tmp_path):
    make_app(tmp_path)
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        rows = db.execute("select slug,contract_version,active,contract_sha256 from audience_profiles order by slug").fetchall()
    assert [row[0] for row in rows] == ["executive", "public", "technical-peer"]
    assert all(row[1] == "audience-adaptation-v1" and row[2] == 1 and len(row[3]) == 64 for row in rows)


def test_audience_states_are_independent():
    assert derived_state({}, [], []) == "AUDIENCE_GENERATION_REQUIRED"
    assert derived_state({}, [{"status": "RUNNING", "started_at": "1", "attempt_id": "a"}], []) == "AUDIENCE_GENERATION_RUNNING"
    assert derived_state({}, [{"status": "COMPLETED", "started_at": "1", "attempt_id": "a", "normalized_proposal": "x"}], []) == "AUDIENCE_REVIEW_TARGET_REQUIRED"


def test_unknown_profile_contract_fails_closed():
    with pytest.raises(ValueError): profile_contract("unknown")


def test_audience_v2_contract_is_explicit_and_preserves_integrity_semantics():
    assert AUDIENCE_VERSION == "audience-adaptation-v2"
    schema = audience_schema()
    finding = {"category": "no_material_issue_found", "detail": "No new material integrity issue was identified."}
    raw = __import__("json").dumps({"integrity_findings": [finding], "audience_adaptation": "The service remains local."})
    assert parse_audience_response(raw)[0] == [finding]
    with pytest.raises(ValueError, match="sole concise"):
        parse_audience_response(__import__("json").dumps({"integrity_findings": [finding, {"category": "ambiguity", "detail": "One issue remains."}], "audience_adaptation": "The service remains local."}))
    with pytest.raises(ValueError, match="integrity finding"):
        parse_audience_response(__import__("json").dumps({"integrity_findings": [{"category": "no material issue found", "detail": "No issue."}], "audience_adaptation": "The service remains local."}))
    assert schema["properties"]["integrity_findings"]["items"]["required"] == ["category", "detail"]


def test_adaptation_requires_and_binds_accepted_baseline(tmp_path):
    app, trial_id = staged_app(tmp_path)
    accepted = request(app, f"/trial/{trial_id}/baseline/accept", "POST", {"confirm_baseline": "1", "csrf": "x"})
    assert accepted["status"].startswith("303")
    with app._db() as db:
        trial = db.execute("select * from trials where trial_id=?", (trial_id,)).fetchone()
        adaptation_id = app._create_audience_adaptation(db, trial, "technical-peer")
        row = db.execute("select baseline_id,profile_id from audience_adaptations where adaptation_id=?", (adaptation_id,)).fetchone()
    assert row[1] == "audience-technical-peer"


def test_audience_generation_attempt_is_typed_and_provenanced(tmp_path):
    app, trial_id = staged_app(tmp_path)
    assert request(app, f"/trial/{trial_id}/baseline/accept", "POST", {"confirm_baseline": "1", "csrf": "x"})["status"].startswith("303")
    class Client:
        def generate_audience(self, *args, **kwargs): return result_for("The observed service remains local and review is unresolved.", "The service remains local for technical peers.")
    app.ollama_client = Client()
    attempt_id, state = app._generate_audience(trial_id, "technical-peer")
    assert state == "COMPLETED"
    with app._db() as db:
        row = db.execute("select kind,adaptation_id,baseline_id,profile_id,status from generation_attempts where attempt_id=?", (attempt_id,)).fetchone()
    assert tuple(row)[0] == "AUDIENCE" and row[1] and row[2] and row[3] == "audience-technical-peer" and row[4] == "COMPLETED"


def test_audience_review_acceptance_is_profile_scoped(tmp_path):
    app, trial_id = staged_app(tmp_path)
    assert request(app, f"/trial/{trial_id}/baseline/accept", "POST", {"confirm_baseline": "1", "csrf": "x"})["status"].startswith("303")
    class Client:
        def generate_audience(self, *args, **kwargs): return result_for("The observed service remains local and review is unresolved.", "The service remains local for technical peers.")
    app.ollama_client = Client()
    assert request(app, f"/trial/{trial_id}/audience/technical-peer/create", "POST", {"csrf": "x"})["status"].startswith("303")
    assert request(app, f"/trial/{trial_id}/audience/technical-peer/generate", "POST", {"csrf": "x"})["status"].startswith("303")
    assert request(app, f"/trial/{trial_id}/audience/technical-peer/review-target", "POST", {"csrf": "x"})["status"].startswith("303")
    assert request(app, f"/trial/{trial_id}/audience/technical-peer/review", "POST", {"outcome": "AUDIENCE_ACCEPTED", "csrf": "x"})["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("select count(*) from accepted_audience_versions").fetchone()[0] == 1
        assert db.execute("select count(*) from accepted_audience_versions where profile_id='audience-executive'").fetchone()[0] == 0


def test_audience_attempt_is_durable_before_model_call(tmp_path):
    app, trial_id = staged_app(tmp_path)
    assert request(app, f"/trial/{trial_id}/baseline/accept", "POST", {"confirm_baseline": "1", "csrf": "x"})["status"].startswith("303")
    class Client:
        def __init__(self): self.calls = []
        def generate_audience(self, *args, **kwargs):
            with app._db() as db:
                self.calls.append([tuple(row) for row in db.execute("select status from generation_attempts where kind='AUDIENCE'").fetchall()])
            return result_for("The observed service remains local and review is unresolved.", "The service remains local for technical peers.")
    client = Client(); app.ollama_client = client
    attempt_id, state = app._generate_audience(trial_id, "technical-peer")
    assert state == "COMPLETED" and client.calls == [[("RUNNING",)]]
    with app._db() as db:
        events = [row[0:2] for row in db.execute("select from_status,to_status from generation_attempt_events where attempt_id=? order by sequence_number", (attempt_id,))]
    assert events == [(None, "QUEUED"), ("QUEUED", "RUNNING"), ("RUNNING", "COMPLETED")]


def test_archived_audience_generation_is_local_and_humane(tmp_path):
    app, trial_id = staged_app(tmp_path)
    assert request(app, f"/trial/{trial_id}/baseline/accept", "POST", {"confirm_baseline": "1", "csrf": "x"})["status"].startswith("303")
    assert request(app, f"/trial/{trial_id}/audience/technical-peer/create", "POST", {"csrf": "x"})["status"].startswith("303")
    assert request(app, f"/trial/{trial_id}/archive", "POST", {"csrf": "x"})["status"].startswith("303")
    response = request(app, f"/trial/{trial_id}/audience/technical-peer/generate", "POST", {"csrf": "x"})
    assert response["status"].startswith("400") and "did not start a new audience attempt" in response["body"]
    with app._db() as db:
        assert db.execute("select count(*) from generation_attempts where kind='AUDIENCE'").fetchone()[0] == 0
