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
    assert "Model execution</strong><p class='status'>disabled" in response["body"]


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
    decision = request(application, f"/trial/{trial_id}/decision", "POST", {"decision": "REVISION_REQUIRED", "csrf": "x"})
    assert decision["status"].startswith("303")
    assert "REVISION_REQUIRED" in request(application, f"/trial/{trial_id}")["body"]
    assert request(application, f"/trial/{trial_id}/delete", "POST", {"csrf": "x"})["status"].startswith("303")


def test_no_model_execution_route(tmp_path):
    response = request(app(tmp_path), "/api/generate", "POST", {"source_text": "never execute", "csrf": "x"})
    assert response["status"].startswith("404")
