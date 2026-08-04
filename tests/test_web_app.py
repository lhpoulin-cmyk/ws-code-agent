import base64
import io
import sqlite3
from pathlib import Path

from docwriter_web import AppConfig, DocWriterApp


def request(app, path="/", method="GET", form=None, auth=True):
    path, _, query = path.partition("?")
    body = "" if form is None else "&".join(f"{k}={v}" for k, v in form.items())
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query, "CONTENT_LENGTH": str(len(body.encode())), "wsgi.input": io.BytesIO(body.encode()), "HTTP_COOKIE": "docwriter_csrf=x", "HTTP_AUTHORIZATION": "Basic " + base64.b64encode(b"operator:testing-password").decode() if auth else ""}
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
    assert "Projects" in response["body"] and "Review queue" in response["body"] and "System status" in response["body"]


def test_draft_versions_decision_and_delete(tmp_path):
    application = app(tmp_path)
    created = request(application, "/trial", "POST", {"source_text": "A source paragraph.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"})
    assert created["status"].startswith("303")
    trial_id = created["headers"][0][1].rsplit("/", 1)[-1]
    assert "REVIEW_REQUIRED" in trial_page(application, trial_id)["body"]
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
    assert "REVISION_REQUIRED" in trial_page(application, trial_id)["body"]
    assert request(application, f"/trial/{trial_id}/delete", "POST", {"csrf": "x"})["status"].startswith("400")
    assert request(application, f"/trial/{trial_id}/archive", "POST", {"csrf": "x"})["status"].startswith("303")
    assert "Archived trial" in trial_page(application, trial_id)["body"]
    assert request(application, f"/trial/{trial_id}/restore", "POST", {"csrf": "x"})["status"].startswith("303")


def _trial_id(response):
    return response["headers"][0][1].rsplit("/", 1)[-1]


def trial_page(application, trial_id):
    return request(application, f"/project/alpha/trial/{trial_id}")


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
    page = trial_page(restarted, trial_id)["body"]
    assert "REVIEW_RATIONALE_MISSING" in page and "legacy / unavailable" in page
    saved = request(restarted, f"/trial/{trial_id}/review", "POST", {"note_text": "The opening sounded generic and did not sound like the operator.", "related_passage": "The opening sentence.", "private_steering": "1", "csrf": "x"})
    assert saved["status"].startswith("303") and "review_saved=1" in saved["headers"][0][1]
    refreshed = DocWriterApp(application.config)
    page = trial_page(refreshed, trial_id)["body"]
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
    assert "First rationale" in trial_page(DocWriterApp(application.config), trial_id)["body"]


def test_no_model_execution_route(tmp_path):
    response = request(app(tmp_path), "/api/generate", "POST", {"source_text": "never execute", "csrf": "x"})
    assert response["status"].startswith("404")


def test_all_trials_listing_filters_search_and_deleted_exclusion(tmp_path):
    application = app(tmp_path)
    accepted = _trial_id(request(application, "/trial", "POST", {"source_text": "Accepted writing sample.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    rejected = _trial_id(request(application, "/trial", "POST", {"source_text": "Rejected writing sample.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    request(application, f"/trial/{accepted}/decision", "POST", {"decision": "ACCEPTED", "csrf": "x"})
    request(application, f"/trial/{rejected}/decision", "POST", {"decision": "REJECTED", "decision_reason": "Not direct enough.", "csrf": "x"})
    deleted = _trial_id(request(application, "/trial", "POST", {"source_text": "Deleted writing sample.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    request(application, f"/trial/{deleted}/archive", "POST", {"csrf": "x"})
    all_page = request(application, "/trials")["body"]
    assert accepted in all_page and rejected in all_page and deleted in all_page
    assert "ACCEPTED" in request(application, "/trials?status=ACCEPTED")["body"]
    rejected_page = request(application, "/trials?status=REJECTED")["body"]
    assert rejected in rejected_page and accepted not in rejected_page
    search_page = request(application, "/trials", "POST", {"search": rejected, "csrf": "x"})["body"]
    assert rejected in search_page and accepted not in search_page


def test_system_status_is_dedicated_and_human_readable(tmp_path):
    response = request(app(tmp_path), "/system")
    assert "System status" in response["body"]
    assert "Doc Writer review application" in response["body"]
    assert "docwriter.home.arpa" in response["body"]
    assert "127.0.0.1:11434" not in response["body"]


def test_environment_configuration_keeps_host_version_and_ollama_distinct(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "session-secret").write_bytes(b"x" * 32)
    (tmp_path / "config" / "operator-password").write_text("testing-password\n")
    monkeypatch.setenv("DOCWRITER_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setenv("DOCWRITER_APP_VERSION", "ba30eb0")
    monkeypatch.setenv("DOCWRITER_OLLAMA_URL", "http://127.0.0.1:11434")
    config = AppConfig.from_environment()
    assert config.canonical_host == "docwriter.home.arpa"
    assert config.version == "ba30eb0"
    assert config.ollama_url == "http://127.0.0.1:11434"


def test_existing_trial_detail_order_and_collapsed_provenance(tmp_path):
    application = app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "Source paragraph.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.execute("insert into generation_attempts(attempt_id,trial_id,source_version_id,source_text,source_sha256,prompt_version,prompt_text,prompt_sha256,request_json,model_identifier,model_digest,generation_settings,started_at,completed_at,raw_ollama_response,response_sha256,integrity_findings,normalized_proposal,proposal_sha256,source_to_proposal_diff,telemetry,application_version,status,error,error_class) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("generation-test", trial_id, 1, "Source paragraph.", "source-hash", "prompt-v1", "prompt", "prompt-hash", "{}", "mistral-nemo:12b-instruct-2407-q4_K_M", "sha256:test", "{}", "2026-08-03T00:00:00+00:00", "2026-08-03T00:00:01+00:00", "raw", "raw-hash", "[]", "Proposal.", "proposal-hash", "diff", "{}", "test-version", "COMPLETED", "", ""))
        db.execute("update trials set normalized_output=? where trial_id=?", ("Proposal.", trial_id)); db.commit()
    body = trial_page(application, trial_id)["body"]
    assert "Source paragraph" in body and "Conversational proposal" in body and "Exact diff" in body
    assert "<details class='panel'><summary><strong>Full provenance" in body
    assert body.index("Source paragraph") < body.index("Conversational proposal") < body.index("Exact diff")


def test_review_workspace_visual_identity_and_focus_styles(tmp_path):
    body = request(app(tmp_path), "/")["body"]
    assert "background: var(--ink)" in body
    assert "--copper: #b76638" in body
    assert "outline: 3px solid #6db5d2" in body
    assert "Review queue" in body and "System status" in body


def test_alpha_project_backfill_and_project_hierarchy(tmp_path):
    application = app(tmp_path)
    first = _trial_id(request(application, "/trial", "POST", {"source_text": "Retained historical trial.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    second = _trial_id(request(application, "/trial", "POST", {"source_text": "Another retained trial.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.execute("update trials set project_id=NULL")
        db.execute("delete from project_migration_events")
        db.commit()
    application = DocWriterApp(application.config)
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        project = db.execute("select project_id,slug,name,status from projects where slug='alpha'").fetchone()
        assert project == ("project-alpha", "alpha", "Alpha Trial", "ACTIVE")
        assert db.execute("select count(*) from trials where project_id=?", (project[0],)).fetchone()[0] == 2
        assert db.execute("select trial_count_assigned from project_migration_events where migration_name='projects-alpha-v1'").fetchone()[0] == 2
    page = request(application, "/projects")["body"]
    assert "Alpha Trial" in page and "2 trials" in page
    detail = request(application, "/project/alpha")["body"]
    assert first in detail and second in detail and "New trial" in detail
    assert request(application, f"/trial/{first}")["status"].startswith("301")
    assert "Projects</a>" in trial_page(application, first)["body"]


def test_project_create_edit_archive_restore_and_no_orphan(tmp_path):
    application = app(tmp_path)
    created = request(application, "/project", "POST", {"name": "Second Project", "purpose": "A separate review workspace.", "csrf": "x"})
    assert created["status"].startswith("303")
    project_id = created["headers"][0][1].rsplit("/", 1)[-1]
    assert "Second Project" in request(application, f"/project/{project_id}")["body"]
    trial = request(application, "/trial", "POST", {"project_id": project_id, "source_text": "Assigned trial.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"})
    trial_id = _trial_id(trial)
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("select project_id from trials where trial_id=?", (trial_id,)).fetchone()[0] == project_id
    assert request(application, f"/project/{project_id}/archive", "POST", {"csrf": "x"})["status"].startswith("303")
    assert request(application, f"/trial/new?project={project_id}")["status"].startswith("400")
    assert request(application, f"/project/{project_id}/restore", "POST", {"csrf": "x"})["status"].startswith("303")
    assert request(application, f"/project/{project_id}/edit", "POST", {"name": "Renamed Project", "purpose": "Edited purpose.", "csrf": "x"})["status"].startswith("303")
    assert "Renamed Project" in request(application, f"/project/{project_id}")["body"]


def test_project_scoped_and_global_review_queues_and_incomplete_state(tmp_path):
    application = app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "Unsumbitted source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    page = trial_page(application, trial_id)["body"]
    assert "REQUEST_NOT_STARTED" in page and "writer has not been run yet" in page
    assert trial_id in request(application, "/review-queue")["body"]
    assert trial_id in request(application, "/project/alpha?status=needs_review")["body"]
    assert request(application, f"/trial/{trial_id}/generate", "POST", {"csrf": "wrong"})["status"].startswith("403")


def test_failed_attempt_classification_and_raw_response_render(tmp_path):
    application = app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "A source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    from docwriter_web.generation import OllamaError
    application.ollama_client = type("FailingClient", (), {"generate": lambda self, source: (_ for _ in ()).throw(OllamaError("Ollama HTTP status 500", '{"error":"safe"}', {"error": "safe"}, "OLLAMA_HTTP_ERROR"))})()
    assert request(application, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})["status"].startswith("303")
    body = trial_page(application, trial_id)["body"]
    assert "OLLAMA_HTTP_ERROR" in body and "Preserved raw Ollama response" in body and '{&quot;error&quot;:&quot;safe&quot;}' in body
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("select error_class,status from generation_attempts").fetchone() == ("OLLAMA_HTTP_ERROR", "OLLAMA_HTTP_ERROR")


def test_stale_running_attempt_is_recovered_without_rewriting_history(tmp_path):
    application = app(tmp_path)
    trial_id = _trial_id(request(application, "/trial", "POST", {"source_text": "A retained source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"}))
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.execute("insert into generation_attempts(attempt_id,trial_id,source_version_id,source_text,source_sha256,prompt_version,prompt_text,prompt_sha256,request_json,model_identifier,model_digest,generation_settings,started_at,completed_at,raw_ollama_response,response_sha256,integrity_findings,normalized_proposal,proposal_sha256,source_to_proposal_diff,telemetry,application_version,status,error,error_class) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("generation-stale", trial_id, 1, "A retained source.", "hash", "prompt-v1", "prompt", "prompt-hash", "{}", "mistral-nemo:12b-instruct-2407-q4_K_M", "sha256:test", "{}", "2020-01-01T00:00:00+00:00", "", "preserved-raw", "raw-hash", "[]", "", "", "", "{}", "test", "RUNNING", "", ""))
        db.commit()
    restarted = DocWriterApp(application.config)
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("select status,error_class,raw_ollama_response from generation_attempts where attempt_id='generation-stale'").fetchone() == ("INTERRUPTED", "INTERRUPTED", "preserved-raw")
    assert "INTERRUPTED" in trial_page(restarted, trial_id)["body"]
