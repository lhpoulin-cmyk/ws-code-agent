import base64
import io
import json
import sqlite3
from dataclasses import replace

from docwriter_web import AppConfig, DocWriterApp
from docwriter_web.generation import GenerationResult, MODEL, MODEL_DIGEST, exact_diff, parse_response_with_setup, sha256_text
from docwriter_web.writing_setup import SETUP_VERSION, serialize


def request(app, path, method="GET", form=None):
    body = "" if form is None else "&".join(f"{key}={value}" for key, value in form.items())
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(body.encode())), "wsgi.input": io.BytesIO(body.encode()), "HTTP_COOKIE": "docwriter_csrf=x", "HTTP_AUTHORIZATION": "Basic " + base64.b64encode(b"operator:testing-password").decode()}
    result = {}
    def start(status, headers): result.update(status=status, headers=headers)
    result["body"] = b"".join(app(environ, start)).decode()
    return result


def make_app(tmp_path):
    password = tmp_path / "password"
    password.write_text("testing-password\n")
    return DocWriterApp(AppConfig(tmp_path, "operator", password, b"x" * 32))


def make_trial(app):
    response = request(app, "/trial", "POST", {"source_text": "I changed careers after a health transition.", "primary_audience": "General reader / personal introduction", "tone": "Direct, hopeful, lightly wry, proud, resilient", "purpose": "Introduce a major life transition without diminishing the career that came before it.", "preservation_instructions": "Preserve pride, curiosity, perseverance, health context, excitement, and the system-test fact.", "clarification_policy": "Ask one focused question rather than guessing when ambiguity would materially change meaning.", "csrf": "x"})
    return response["headers"][0][1].rsplit("/", 1)[-1]


def result(source, kind, proposal="", question=""):
    finding = {"category": "no_material_issue_found", "detail": "No material issue found.", "related_passage": "", "blocks_approval": False, "resolution_authority": ""}
    payload = {"integrity_findings": [finding], "result": {"kind": kind}}
    if kind == "PROPOSAL":
        payload["result"]["conversational_proposal"] = proposal
    else:
        payload["result"]["clarification_question"] = question
    raw = json.dumps(payload, separators=(",", ":"))
    return GenerationResult(MODEL, MODEL_DIGEST, "{}", "setup prompt", "prompt-hash", "2026-08-04T00:00:00+00:00", "2026-08-04T00:00:01+00:00", raw, {"message": {"content": raw}}, [finding], proposal, exact_diff(source, proposal) if proposal else "", sha256_text(raw), sha256_text(proposal) if proposal else "", {}, "chat", "/api/chat", "mistral-nemo-12b", "phase-b-v1", "chat-json-v1", ("system", "user"), {}, "composed", "conversational-proposal-v3", "schema", "{}", "passed" if kind == "PROPOSAL" else "not_run", kind, question)


class SetupClient:
    def __init__(self):
        self.calls = []

    def generate_with_setup(self, source, setup, bundle, profile, clarification_answer=""):
        self.calls.append((source, setup, clarification_answer))
        if not clarification_answer:
            return result(source, "CLARIFICATION_REQUIRED", question="Which health transition should the introduction name?")
        return result(source, "PROPOSAL", proposal="I changed careers after a health transition, and I am excited about what comes next.")


def test_setup_is_versioned_serialized_and_sent_to_first_request(tmp_path):
    app = make_app(tmp_path)
    trial_id = make_trial(app)
    client = SetupClient()
    app.ollama_client = client
    assert request(app, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.row_factory = sqlite3.Row
        setup = db.execute("SELECT * FROM writing_setup_versions WHERE trial_id=?", (trial_id,)).fetchone()
        attempt = db.execute("SELECT * FROM generation_attempts WHERE trial_id=?", (trial_id,)).fetchone()
    assert setup["setup_version_id"].startswith("setup-") and setup["setup_sha256"] == sha256_text(setup["serialized_setup"])
    assert attempt["writing_setup_version_id"] == setup["setup_version_id"]
    assert attempt["writing_setup_sha256"] == setup["setup_sha256"]
    assert json.loads(attempt["serialized_writing_setup"])["primary_audience"] == "General reader / personal introduction"
    assert setup["serialized_setup"] in json.loads(attempt["request_json"])["messages"][1]["content"]
    assert client.calls[0][1].primary_audience == "General reader / personal introduction"


def test_clarification_is_bounded_answered_and_resumed_as_new_attempt(tmp_path):
    app = make_app(tmp_path)
    trial_id = make_trial(app)
    client = SetupClient()
    app.ollama_client = client
    request(app, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        question = db.execute("SELECT * FROM clarification_questions WHERE trial_id=?", (trial_id,)).fetchone()
        assert db.execute("SELECT result_kind,normalized_proposal FROM generation_attempts WHERE trial_id=?", (trial_id,)).fetchone() == ("CLARIFICATION_REQUIRED", "")
    blocked = request(app, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})
    assert blocked["status"].startswith("400") and "clarification question" in blocked["body"]
    answered = request(app, f"/trial/{trial_id}/clarification/{question[0]}/answer", "POST", {"answer_text": "Name the health transition without adding a diagnosis.", "csrf": "x"})
    assert answered["status"].startswith("303")
    resumed = request(app, f"/trial/{trial_id}/clarification/{question[0]}/resume", "POST", {"csrf": "x"})
    assert resumed["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.row_factory = sqlite3.Row
        attempts = db.execute("SELECT * FROM generation_attempts WHERE trial_id=? ORDER BY rowid", (trial_id,)).fetchall()
        answer = db.execute("SELECT * FROM clarification_answers WHERE question_id=?", (question[0],)).fetchone()
    assert len(attempts) == 2
    assert attempts[0]["result_kind"] == "CLARIFICATION_REQUIRED"
    assert attempts[1]["status"] == "COMPLETED" and attempts[1]["result_kind"] == "PROPOSAL"
    assert attempts[1]["clarification_question_id"] == question[0]
    assert attempts[1]["clarification_answer_id"] == answer["answer_id"]
    assert "Name the health transition" in json.loads(attempts[1]["request_json"])["messages"][1]["content"]
    assert len(client.calls) == 2


def test_setup_change_preserves_old_attempt_and_keeps_audience_separate(tmp_path):
    app = make_app(tmp_path)
    trial_id = make_trial(app)
    client = SetupClient()
    app.ollama_client = client
    request(app, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        old = db.execute("SELECT attempt_id,writing_setup_sha256 FROM generation_attempts WHERE trial_id=?", (trial_id,)).fetchone()
    request(app, f"/trial/{trial_id}/save", "POST", {"source_text": "I changed careers after a health transition.", "primary_audience": "Technical peer", "tone": "Precise", "purpose": "Explain the transition.", "preservation_instructions": "Preserve the facts.", "clarification_policy": "Ask one focused question when needed.", "csrf": "x"})
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        setups = db.execute("SELECT setup_version_id,setup_sha256 FROM writing_setup_versions WHERE trial_id=? ORDER BY source_version_id", (trial_id,)).fetchall()
        current = db.execute("SELECT attempt_id,writing_setup_sha256 FROM generation_attempts WHERE attempt_id=?", (old[0],)).fetchone()
        adaptations = db.execute("SELECT count(*) FROM audience_adaptations WHERE trial_id=?", (trial_id,)).fetchone()[0]
    assert len(setups) == 2 and setups[0][1] != setups[1][1]
    assert tuple(current) == tuple(old)
    assert adaptations == 0


def test_v3_parser_never_returns_proposal_with_clarification():
    findings, proposal, kind, question = parse_response_with_setup(json.dumps({"integrity_findings": [], "result": {"kind": "CLARIFICATION_REQUIRED", "clarification_question": "Which date matters?"}}))
    assert findings == [] and proposal == "" and kind == "CLARIFICATION_REQUIRED" and question == "Which date matters?"
