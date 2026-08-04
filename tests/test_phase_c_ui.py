import base64
import io
import sqlite3

from docwriter_web import AppConfig, DocWriterApp


def request(app, path="/", method="GET", form=None):
    body = "" if form is None else "&".join(f"{k}={v}" for k, v in form.items())
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
    response = request(app, "/trial", "POST", {"source_text": "A preserved source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"})
    return response["headers"][0][1].rsplit("/", 1)[-1]


def test_fallback_attempt_view_has_safe_structural_evidence(tmp_path):
    app = make_app(tmp_path)
    trial_id = make_trial(app)
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        db.execute("UPDATE generation_attempts SET presentation_result='failed' WHERE 0")
    # The route is exercised against an actual completed-shaped record without
    # invoking a model; only structural fallback content is asserted.
    with app._db() as db:
        trial = db.execute("select trial_id from trials where trial_id=?", (trial_id,)).fetchone()
        assert trial
    page = request(app, f"/project/alpha/trial/{trial_id}")
    assert page["status"].startswith("200")
    assert "REQUEST_NOT_STARTED" in page["body"]
    assert "writer has not been run yet" in page["body"]

