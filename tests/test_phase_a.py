import sqlite3

from docwriter_web import DocWriterApp
from test_web_app import request, trial_page


def _trial_id(response):
    return response["headers"][0][1].rsplit("/", 1)[-1]


def test_phase_a_ledger_fk_and_idempotence(tmp_path):
    application = __import__("test_web_app").app(tmp_path)
    db_path = tmp_path / "state" / "docwriter.sqlite3"
    with sqlite3.connect(db_path) as db:
        names = [row[0] for row in db.execute("SELECT migration_name FROM schema_migrations ORDER BY rowid")]
        counts = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("trials", "trial_versions", "generation_attempts", "review_events", "schema_migrations")}
        assert len(names) == 9
    restarted = DocWriterApp(application.config)
    with sqlite3.connect(db_path) as db:
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 0  # raw connections are not the application factory
        assert {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in counts} == counts
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    with restarted._db() as db:
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_archive_preserves_children_and_restore_returns_to_active(tmp_path):
    application = __import__("test_web_app").app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "Disposable source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.execute("INSERT INTO generation_attempts(attempt_id,trial_id,source_version_id,source_text,source_sha256,prompt_version,prompt_text,prompt_sha256,request_json,model_identifier,model_digest,generation_settings,started_at,completed_at,raw_ollama_response,response_sha256,integrity_findings,normalized_proposal,proposal_sha256,source_to_proposal_diff,telemetry,application_version,status,error,error_class) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("generation-preserved", trial_id, 1, "Disposable source.", "source-hash", "prompt-v1", "prompt", "prompt-hash", "{}", "mistral-nemo:12b-instruct-2407-q4_K_M", "sha256:test", "{}", "2026-08-03T00:00:00+00:00", "2026-08-03T00:00:01+00:00", "", "", "[]", "", "", "", "{}", "test", "FAILED", "", "TEST"))
        db.commit()
    assert request(application, f"/trial/{trial_id}/archive", "POST", {"csrf": "x"})["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("SELECT lifecycle_state FROM trials WHERE trial_id=?", (trial_id,)).fetchone()[0] == "ARCHIVED"
        assert db.execute("SELECT count(*) FROM trial_versions WHERE trial_id=?", (trial_id,)).fetchone()[0] == 2
        assert db.execute("SELECT count(*) FROM generation_attempts WHERE trial_id=?", (trial_id,)).fetchone()[0] == 1
    assert "Archived trial" in trial_page(application, trial_id)["body"]
    assert request(application, f"/trial/{trial_id}/restore", "POST", {"csrf": "x"})["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("SELECT lifecycle_state FROM trials WHERE trial_id=?", (trial_id,)).fetchone()[0] == "ACTIVE"


def test_flat_route_redirects_and_unknown_is_404(tmp_path):
    application = __import__("test_web_app").app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "Route source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    response = request(application, f"/trial/{trial_id}")
    assert response["status"].startswith("301")
    assert response["headers"][0][1] == f"/project/alpha/trial/{trial_id}"
    assert request(application, "/trial/unknown-trial")["status"].startswith("404")


def test_attempts_and_review_events_are_append_only(tmp_path):
    application = __import__("test_web_app").app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "Lineage source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.execute("INSERT INTO generation_attempts(attempt_id,trial_id,source_version_id,source_text,source_sha256,prompt_version,prompt_text,prompt_sha256,request_json,model_identifier,model_digest,generation_settings,started_at,completed_at,raw_ollama_response,response_sha256,integrity_findings,normalized_proposal,proposal_sha256,source_to_proposal_diff,telemetry,application_version,status,error,error_class) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("generation-lineage", trial_id, 1, "Lineage source.", "source-hash", "prompt-v1", "prompt", "prompt-hash", "{}", "mistral-nemo:12b-instruct-2407-q4_K_M", "sha256:test", "{}", "2026-08-03T00:00:00+00:00", "2026-08-03T00:00:01+00:00", "", "", "[]", "", "", "", "{}", "test", "FAILED", "", "TEST"))
        db.execute("INSERT INTO review_events(event_id,trial_id,event_type,decision,note_text,private_steering,related_passage,reviewer_identity,created_at,content_hash) VALUES(?,?,?,?,?,?,?,?,?,?)", ("review-lineage", trial_id, "REVIEW_NOTE", None, "A note.", 0, "", "operator", "2026-08-03T00:00:00+00:00", "hash"))
        db.commit()
        try:
            db.execute("DELETE FROM generation_attempts WHERE attempt_id='generation-lineage'")
            assert False, "attempt deletion unexpectedly succeeded"
        except sqlite3.IntegrityError:
            pass
        try:
            db.execute("UPDATE generation_attempts SET source_sha256='changed' WHERE attempt_id='generation-lineage'")
            assert False, "attempt provenance update unexpectedly succeeded"
        except sqlite3.IntegrityError:
            pass
        try:
            db.execute("DELETE FROM review_events WHERE event_id='review-lineage'")
            assert False, "review deletion unexpectedly succeeded"
        except sqlite3.IntegrityError:
            pass
