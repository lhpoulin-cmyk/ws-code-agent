import base64
import io
import json
import sqlite3
import pytest
from dataclasses import replace

from docwriter_web import AppConfig, DocWriterApp
from docwriter_web.generation import (
    GENERATION_SETTINGS,
    MODEL,
    MODEL_DIGEST,
    PROMPT_VERSION,
    GenerationResult,
    OllamaClient,
    OllamaError,
    ResponseSchemaError,
    exact_diff,
    prompt_for,
    serialized_json,
    sha256_text,
)
from docwriter_web.prompt_contracts import PROMPT_VERSION as V2_PROMPT_VERSION
from docwriter_web.prompt_contracts import load_phase_b_assets
from docwriter_web.generation import delimited_source_payload, parse_response_v2, request_payload_v2, validate_task_adherence


class FakeHTTPResponse:
    def __init__(self, payload): self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit=-1): return self.payload[:limit]


def request(app, path="/", method="GET", form=None, auth=True):
    body = "" if form is None else "&".join(f"{k}={v}" for k, v in form.items())
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(body.encode())), "wsgi.input": io.BytesIO(body.encode()), "HTTP_COOKIE": "docwriter_csrf=x", "HTTP_AUTHORIZATION": "Basic " + base64.b64encode(b"operator:testing-password").decode() if auth else ""}
    result = {}
    def start(status, headers): result.update(status=status, headers=headers)
    result["body"] = b"".join(app(environ, start)).decode()
    return result


def make_app(tmp_path):
    password = tmp_path / "password"
    password.write_text("testing-password\n")
    return DocWriterApp(AppConfig(tmp_path, "operator", password, b"x" * 32))


def make_trial(app):
    response = request(app, "/trial", "POST", {"source_text": "The observed service remains local and review is unresolved.", "model_identifier": MODEL, "csrf": "x"})
    return response["headers"][0][1].rsplit("/", 1)[-1]


def result_for(source, proposal="The service remains local, and review is unresolved."):
    raw = json.dumps({"integrity_findings": [{"category": "no material issue found", "detail": "No material issue found."}], "conversational_proposal": proposal}, separators=(",", ":"))
    return replace(GenerationResult(MODEL, MODEL_DIGEST, "{request}", prompt_for(source), sha256_text(prompt_for(source)), "2026-08-03T00:00:00+00:00", "2026-08-03T00:00:01+00:00", raw, {"eval_count": 12}, [{"category": "no material issue found", "detail": "No material issue found."}], proposal, exact_diff(source, proposal), sha256_text(raw), sha256_text(proposal), {"eval_count": 12, "wall_seconds": 1.0}), task_adherence_result="passed")


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def generate(self, source):
        self.calls.append(source)
        if self.error:
            raise self.error
        return self.result


def test_generation_requires_auth_and_csrf(tmp_path):
    application = make_app(tmp_path)
    assert request(application, "/trial/x/generate", "POST", {"csrf": "x"}, auth=False)["status"].startswith("401")
    trial_id = make_trial(application)
    assert request(application, f"/trial/{trial_id}/generate", "POST", {"csrf": "wrong"})["status"].startswith("403")


def test_success_persists_fixed_settings_provenance_and_review_required(tmp_path):
    application = make_app(tmp_path)
    trial_id = make_trial(application)
    source = "The observed service remains local and review is unresolved."
    fake = FakeClient(result_for(source))
    application.ollama_client = fake
    response = request(application, f"/trial/{trial_id}/generate", "POST", {"csrf": "x", "model_identifier": MODEL})
    assert response["status"].startswith("303")
    assert fake.calls == [source]
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        trial = db.execute("select model_identifier,model_digest,generation_parameters,integrity_findings,normalized_output,review_status,revision_lineage from trials where trial_id=?", (trial_id,)).fetchone()
        attempt = db.execute("select source_version_id,prompt_version,prompt_sha256,request_json,raw_ollama_response,source_to_proposal_diff,proposal_sha256,status from generation_attempts where trial_id=?", (trial_id,)).fetchone()
    assert trial[0:2] == (MODEL, MODEL_DIGEST)
    assert json.loads(trial[2]) == GENERATION_SETTINGS
    assert json.loads(trial[3])[0]["category"] == "no material issue found"
    assert trial[4] == "The service remains local, and review is unresolved."
    assert trial[5] == "REVIEW_REQUIRED"
    assert attempt[0] == 1 and attempt[1] == V2_PROMPT_VERSION and attempt[2] == application.contract_bundle.composed_hash
    assert attempt[4] and "source paragraph" in attempt[5] and attempt[6] == sha256_text(trial[4]) and attempt[7] == "COMPLETED"


def test_generation_rejects_arbitrary_browser_model(tmp_path):
    application = make_app(tmp_path)
    trial_id = make_trial(application)
    response = request(application, f"/trial/{trial_id}/generate", "POST", {"csrf": "x", "model_identifier": "http://attacker.invalid/model"})
    assert response["status"].startswith("400")


def test_v2_chat_request_roles_schema_and_provenance():
    bundle, profiles = load_phase_b_assets()
    profile = profiles["mistral-nemo-12b"]
    source = "I changed fields after a health transition, and one detail remains uncertain."
    payload = request_payload_v2(bundle, profile, source)
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert delimited_source_payload(source) in payload["messages"][1]["content"]
    assert source not in payload["messages"][0]["content"]
    assert payload["format"] == bundle.schema
    valid = json.dumps({"integrity_findings": [{"category": "ambiguity", "detail": "One detail remains uncertain.", "related_passage": "one detail", "blocks_approval": False, "resolution_authority": "operator"}], "conversational_proposal": "I changed fields after a health transition, and one detail remains uncertain."})
    findings, proposal = parse_response_v2(valid)
    assert findings[0]["category"] == "ambiguity"
    assert validate_task_adherence(source, proposal) == "passed"


def test_v2_chat_client_preserves_raw_http_and_metadata():
    bundle, profiles = load_phase_b_assets()
    profile = profiles["mistral-nemo-12b"]
    source = "I changed fields after a health transition, and one detail remains uncertain."
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, json.loads(request.data.decode()) if request.data else None))
        if request.full_url.endswith("/api/tags"):
            return FakeHTTPResponse({"models": [{"name": profile.model_identifier, "digest": profile.expected_digest.removeprefix("sha256:")}]})
        return FakeHTTPResponse({"message": {"role": "assistant", "content": json.dumps({"integrity_findings": [{"category": "ambiguity", "detail": "One detail remains uncertain.", "related_passage": "one detail", "blocks_approval": False, "resolution_authority": "operator"}], "conversational_proposal": source})}, "done": True, "eval_count": 8})

    result = OllamaClient(opener=opener).generate_v2(source, bundle, profile)
    assert calls[1][0].endswith("/api/chat")
    assert calls[1][1]["messages"][1]["content"].startswith("TASK: EDIT_SOURCE_PARAGRAPH")
    assert result.transport_type == "chat" and result.adapter_id == profile.adapter_id
    assert result.task_adherence_result == "passed"
    assert '"message"' in result.raw_ollama_response


def test_v2_task_adherence_rejects_author_directed_and_point_of_view_shifts():
    with pytest.raises(Exception, match="addresses"):
        validate_task_adherence("I wrote this after waking.", "Hi there, I rewrote this for you.")
    with pytest.raises(Exception, match="first-person"):
        validate_task_adherence("I wrote this after waking.", "The author wrote this after waking.")
    with pytest.raises(Exception, match="question"):
        validate_task_adherence("I wrote this after waking.", "I wrote this after waking. What do you think?")


def test_malformed_response_fails_closed_and_retry_is_new_attempt(tmp_path):
    application = make_app(tmp_path)
    trial_id = make_trial(application)
    failed = FakeClient(error=OllamaError("structured response fields are invalid", '{"bad":true}', {"response": '{"bad":true}'}))
    application.ollama_client = failed
    assert request(application, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("select status,raw_ollama_response from generation_attempts").fetchone() == ("INTERRUPTED", '{"bad":true}')
        assert db.execute("select normalized_output,review_status from trials where trial_id=?", (trial_id,)).fetchone() == ("", "REVIEW_REQUIRED")
    source = "The observed service remains local and review is unresolved."
    application.ollama_client = FakeClient(result_for(source))
    assert request(application, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        attempts = db.execute("select status,raw_ollama_response from generation_attempts order by rowid").fetchall()
    assert [row[0] for row in attempts] == ["INTERRUPTED", "COMPLETED"]
    assert attempts[0][1] == '{"bad":true}'


def test_ollama_failure_preserves_draft_and_duplicate_is_rejected(tmp_path):
    application = make_app(tmp_path)
    trial_id = make_trial(application)
    application._generation_lock.acquire()
    try:
        assert request(application, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})["status"].startswith("409")
    finally:
        application._generation_lock.release()
    application.ollama_client = FakeClient(error=OllamaError("local Ollama request failed"))
    assert request(application, f"/trial/{trial_id}/generate", "POST", {"csrf": "x"})["status"].startswith("303")
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        assert db.execute("select normalized_output,review_status from trials where trial_id=?", (trial_id,)).fetchone() == ("", "REVIEW_REQUIRED")


def test_mocked_ollama_request_reconciles_digest_and_settings():
    from docwriter_web.generation import OllamaClient
    calls = []
    raw = json.dumps({"integrity_findings": [], "conversational_proposal": "A concise proposal."})
    def opener(request, timeout):
        calls.append((request.full_url, json.loads(request.data.decode()) if request.data else None, timeout))
        if request.full_url.endswith("/api/tags"):
            return FakeHTTPResponse({"models": [{"name": MODEL, "digest": MODEL_DIGEST}]})
        return FakeHTTPResponse({"response": raw, "eval_count": 4, "eval_duration": 12})
    result = OllamaClient(opener=opener).generate("A source paragraph.")
    assert result.model_digest == MODEL_DIGEST and result.proposal == "A concise proposal."


    assert calls[0][0].endswith("/api/tags") and calls[1][0].endswith("/api/generate")
    payload = calls[1][1]
    assert payload["model"] == MODEL and payload["stream"] is False and payload["think"] is False
    assert payload["options"] == {"num_ctx": 8192, "temperature": 0.2, "top_p": 0.9, "seed": 42}


def test_mocked_ollama_request_normalizes_unprefixed_digest():
    calls = []
    raw = json.dumps({"integrity_findings": [], "conversational_proposal": "A concise proposal."})
    def opener(request, timeout):
        calls.append(request.full_url)
        if request.full_url.endswith("/api/tags"):
            return FakeHTTPResponse({"models": [{"name": MODEL, "digest": MODEL_DIGEST.removeprefix("sha256:")}]})
        return FakeHTTPResponse({"response": raw})
    result = OllamaClient(opener=opener).generate("Source paragraph.")
    assert result.model_digest == MODEL_DIGEST


def test_mocked_ollama_digest_mismatch_fails_closed():
    from docwriter_web.generation import OllamaClient
    def opener(request, timeout):
        return FakeHTTPResponse({"models": [{"name": MODEL, "digest": "sha256:wrong"}]})
    try:
        OllamaClient(opener=opener).generate("A source paragraph.")
    except OllamaError as exc:
        assert "digest" in str(exc)
    else:
        raise AssertionError("digest mismatch did not fail closed")


def test_response_parser_classifies_missing_proposal_and_malformed_json():
    try:
        from docwriter_web.generation import parse_response
        parse_response('{"integrity_findings": []}')
    except ResponseSchemaError as exc:
        assert exc.error_class == "PROPOSAL_FIELD_MISSING"
    else:
        raise AssertionError("missing proposal was accepted")
    try:
        parse_response("not json")
    except ResponseSchemaError as exc:
        assert exc.error_class == "RESPONSE_SCHEMA_INVALID"
    else:
        raise AssertionError("malformed JSON was accepted")


def test_ollama_request_classifies_timeout_http_and_empty_response():
    def timeout_opener(request, timeout):
        raise TimeoutError("timed out")
    try:
        OllamaClient(opener=timeout_opener)._request("/api/generate", {})
    except OllamaError as exc:
        assert exc.error_class == "REQUEST_TIMEOUT"
    else:
        raise AssertionError("timeout was not classified")

    def http_opener(request, timeout):
        raise __import__("urllib.error", fromlist=["HTTPError"]).HTTPError(request.full_url, 503, "unavailable", {}, __import__("io").BytesIO(b'{"error":"safe"}'))
    try:
        OllamaClient(opener=http_opener)._request("/api/generate", {})
    except OllamaError as exc:
        assert exc.error_class == "OLLAMA_HTTP_ERROR" and exc.raw_response == '{"error":"safe"}'
    else:
        raise AssertionError("HTTP failure was not classified")

    class EmptyResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit=-1): return b""
    def empty_opener(request, timeout): return EmptyResponse()
    try:
        OllamaClient(opener=empty_opener)._request("/api/generate", {})
    except OllamaError as exc:
        assert exc.error_class == "EMPTY_RESPONSE"
    else:
        raise AssertionError("empty response was not classified")
