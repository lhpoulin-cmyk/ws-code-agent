import base64
import io
import sqlite3
from pathlib import Path

from docwriter_web import AppConfig, DocWriterApp


def request(app, path="/", method="GET", form=None, auth=True):
    body = "" if form is None else "&".join(f"{k}={v}" for k, v in form.items())
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(body.encode())), "wsgi.input": io.BytesIO(body.encode()), "HTTP_COOKIE": "docwriter_csrf=x", "HTTP_AUTHORIZATION": "Basic " + base64.b64encode(b"operator:testing-password").decode() if auth else ""}
    result = {}
    def start(status, headers): result.update(status=status, headers=headers)
    result["body"] = b"".join(app(environ, start)).decode()
    return result


def app(tmp_path: Path):
    password = tmp_path / "password"
    password.write_text("testing-password\n")
    return DocWriterApp(AppConfig(tmp_path, "operator", password, b"x" * 32))


def test_authentication_and_home(tmp_path):
    application = app(tmp_path)
    assert request(application, auth=False)["status"].startswith("401")
    response = request(application)
    assert response["status"].startswith("200")
    assert "Model execution</strong><p class='status'>enabled" in response["body"]


def test_draft_versions_decision_and_delete(tmp_path):
    application = app(tmp_path)
    created = request(application, "/trial", "POST", {"source_text": "A source paragraph.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"})
    assert created["status"].startswith("303")
    trial_id = created["headers"][0][1].rsplit("/", 1)[-1]
    assert "REVIEW_REQUIRED" in request(application, f"/trial/{trial_id}")["body"]
    edited = request(application, f"/trial/{trial_id}/save", "POST", {"source_text": "An edited source paragraph.", "model_identifier": "mistral-nemo:12b-instruct-2407Z", "csrf": "x"})
    assert edited["status"].startswith("400")
    edited = request(application, f"/trial/{trial_id}/save", "POST", {"source_text": "An edited source paragraph.", "model_identifier": "mistral-nemo:12b-instruct-2407_K_M", "csrf": "x"})
    assert edited["status"].startswith("400")
    edited = request(application, f"/trial/{trial_id}/save", "POST", {"source_text": "An edited source paragraph.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"})
    assert edited["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("select count(*) from trial_versions where trial_id=?", (trial_id,)).fetchone()[0] == 2
    decision = request(application, f"/trial/{trial_id}/decision", "POST", {"decision": "REVISION_REQUIRED", "decision_reason": "The proposal needs a more direct voice.", "csrf": "x"})
    assert decision["status"].startswith("303")
    assert "REVISION_REQUIRED" in request(application, f"/trial/{trial_id}")["body"]
    assert request(application, f"/trial/{trial_id}/delete", "POST", {"csrf": "x"})["status"].startswith("303")


def _trial_id(response):
    return response["headers"][0][1].rsplit("/", 1)[-1]


def test_decision_rationale_rules_and_csrf(tmp_path):
    application = app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "A source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    assert request(application, f"/trial/{trial_id}/decision", "POST", {"decision": "REJECTED", "csrf": "x"})["status"].startswith("400")
    assert request(application, f"/trial/{trial_id}/decision", "POST", {"decision": "REVISION_REQUIRED", "csrf": "x"})["status"].startswith("400")
    assert request(application, f"/trial/{trial_id}/decision", "POST", {"decision": "ACCEPTED", "csrf": "x"})["status"].startswith("303")
    assert request(application, f"/trial/{trial_id}/review", "POST", {"note_text": "no csrf"})["status"].startswith("403")


def test_legacy_rejection_gets_later_rationale_without_rewriting_decision(tmp_path):
    application = app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "A source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    original_time = "2026-08-03T13:00:00+00:00"
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.row_factory = sqlite3.Row
        trial = db.execute("select * from trials where trial_id=?", (trial_id,)).fetchone()
        snapshot = __import__("json").dumps({key: trial[key] for key in trial.keys()}, sort_keys=True)
        db.execute("update trials set review_status=? where trial_id=?", ("REJECTED", trial_id))
        db.execute("insert into trial_versions(trial_id,recorded_at,action,snapshot) values(?,?,?,?)", (trial_id, original_time, "DECISION_REJECTED", snapshot))
        db.commit()
    restarted = DocWriterApp(application.config)
    page = request(restarted, f"/trial/{trial_id}")["body"]
    assert "REVIEW_RATIONALE_MISSING" in page and "legacy / unavailable" in page
    saved = request(restarted, f"/trial/{trial_id}/review", "POST", {"note_text": "The opening sounded generic and did not sound like the operator.", "related_passage": "The opening sentence.", "private_steering": "1", "csrf": "x"})
    assert saved["status"].startswith("303") and "review_saved=1" in saved["headers"][0][1]
    refreshed = DocWriterApp(application.config)
    page = request(refreshed, f"/trial/{trial_id}")["body"]
    assert "The opening sounded generic" in page and "private steering" in page
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        events = db.execute("select event_type,decision,note_text,private_steering,created_at from review_events where trial_id=? order by created_at,event_id", (trial_id,)).fetchall()
        assert events[0][0:2] == ("DECISION", "REJECTED") and events[0][4] == original_time
        assert events[1][0:4] == ("REVIEW_NOTE", None, "The opening sounded generic and did not sound like the operator.", 1)
        assert db.execute("select review_status from trials where trial_id=?", (trial_id,)).fetchone()[0] == "REJECTED"


def test_note_revisions_are_immutable_and_lineage_unchanged(tmp_path):
    application = app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "A source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.execute("update trials set revision_lineage=? where trial_id=?", ('["generation-fixed"]', trial_id)); db.commit()
    request(application, f"/trial/{trial_id}/review", "POST", {"note_text": "First rationale", "csrf": "x"})
    request(application, f"/trial/{trial_id}/review", "POST", {"note_text": "Preferred replacement wording", "related_passage": "Exact phrase", "csrf": "x"})
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        notes = db.execute("select note_text,prior_event_id,content_hash from review_events where trial_id=? and event_type='REVIEW_NOTE' order by created_at,event_id", (trial_id,)).fetchall()
        assert {row[0] for row in notes} == {"First rationale", "Preferred replacement wording"}
        first_id = db.execute("select event_id from review_events where trial_id=? and note_text=?", (trial_id, "First rationale")).fetchone()[0]
        second = db.execute("select prior_event_id,content_hash from review_events where trial_id=? and note_text=?", (trial_id, "Preferred replacement wording")).fetchone()
        first_hash = db.execute("select content_hash from review_events where event_id=?", (first_id,)).fetchone()[0]
        assert second[0] == first_id and first_hash != second[1]
        assert db.execute("select revision_lineage from trials where trial_id=?", (trial_id,)).fetchone()[0] == '["generation-fixed"]'
    assert "First rationale" in request(DocWriterApp(application.config), f"/trial/{trial_id}")["body"]


def test_no_model_execution_route(tmp_path):
    response = request(app(tmp_path), "/api/generate", "POST", {"source_text": "never execute", "csrf": "x"})
    assert response["status"].startswith("404")
