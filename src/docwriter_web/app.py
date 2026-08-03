"""Authenticated local review surface; model execution is intentionally absent."""

from __future__ import annotations

import base64
import difflib
import hashlib
import hmac
import html
import json
import os
import secrets
import sqlite3
import threading
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .generation import (
    GENERATION_SETTINGS,
    MODEL,
    MODEL_DIGEST,
    PROMPT_VERSION,
    OllamaClient,
    OllamaError,
    prompt_for,
    request_payload_for,
    serialized_json,
    sha256_text,
    utc_now,
)

MAX_SOURCE = 12000
MAX_FIELD = 12000
MAX_NOTES = 4000
DECISIONS = {"ACCEPTED", "REVISION_REQUIRED", "REJECTED"}
MODEL_DIGESTS = {
    "qwen3:14b-q4_K_M": "sha256:bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8",
    "gemma3:12b-it-q4_K_M": "sha256:f4031aab637d1ffa37b425704ae0e4fad0314754d17ded67322e4b95836f8a",
    "mistral-nemo:12b-instruct-2407-q4_K_M": "sha256:daf6737417121831e572a9c482e92a221ee0c33537f35f1f857c7b4f7191df55",
}


@dataclass(frozen=True)
class AppConfig:
    runtime_root: Path
    operator_user: str
    operator_password_file: Path
    session_secret: bytes
    canonical_host: str = "docwriter.home.arpa"
    version: str = "generation-v1"
    ollama_url: str = "http://127.0.0.1:11434"

    @property
    def state_dir(self) -> Path:
        return self.runtime_root / "state"

    @property
    def database(self) -> Path:
        return self.state_dir / "docwriter.sqlite3"

    @classmethod
    def from_environment(cls) -> "AppConfig":
        runtime = Path(os.environ.get("DOCWRITER_RUNTIME_ROOT", "/srv/ws-doc-writer"))
        password_file = Path(os.environ.get("DOCWRITER_OPERATOR_PASSWORD_FILE", runtime / "config" / "operator-password"))
        secret_file = Path(os.environ.get("DOCWRITER_SESSION_SECRET_FILE", runtime / "config" / "session-secret"))
        if not secret_file.is_file():
            raise RuntimeError("required session secret is unavailable")
        secret = secret_file.read_bytes().strip()
        if len(secret) < 32:
            raise RuntimeError("session secret is too short")
        return cls(runtime, os.environ.get("DOCWRITER_OPERATOR_USER", "operator"), password_file, secret, os.environ.get("DOCWRITER_APP_VERSION", "generation-v1"), os.environ.get("DOCWRITER_OLLAMA_URL", "http://127.0.0.1:11434"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class DocWriterApp:
    def __init__(self, config: AppConfig):
        self.config = config
        self.ollama_client = OllamaClient(config.ollama_url)
        self._generation_lock = threading.Lock()
        self._generating: set[str] = set()
        self._initialize()

    def _initialize(self) -> None:
        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript("""
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS trials (
                    trial_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    source_text TEXT NOT NULL, source_sha256 TEXT NOT NULL,
                    model_identifier TEXT NOT NULL, model_digest TEXT NOT NULL,
                    generation_parameters TEXT NOT NULL, integrity_findings TEXT NOT NULL,
                    raw_output TEXT NOT NULL, normalized_output TEXT NOT NULL,
                    review_status TEXT NOT NULL, reviewer_notes TEXT NOT NULL,
                    revision_lineage TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trial_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT, trial_id TEXT NOT NULL REFERENCES trials(trial_id),
                    recorded_at TEXT NOT NULL, action TEXT NOT NULL, snapshot TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS generation_attempts (
                    attempt_id TEXT PRIMARY KEY, trial_id TEXT NOT NULL REFERENCES trials(trial_id),
                    source_version_id INTEGER NOT NULL, source_text TEXT NOT NULL, source_sha256 TEXT NOT NULL,
                    prompt_version TEXT NOT NULL, prompt_text TEXT NOT NULL, prompt_sha256 TEXT NOT NULL,
                    request_json TEXT NOT NULL, model_identifier TEXT NOT NULL, model_digest TEXT NOT NULL,
                    generation_settings TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT NOT NULL,
                    raw_ollama_response TEXT NOT NULL, response_sha256 TEXT NOT NULL,
                    integrity_findings TEXT NOT NULL, normalized_proposal TEXT NOT NULL,
                    proposal_sha256 TEXT NOT NULL, source_to_proposal_diff TEXT NOT NULL,
                    telemetry TEXT NOT NULL, application_version TEXT NOT NULL,
                    status TEXT NOT NULL, error TEXT NOT NULL
                );
            """)

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.config.database)
        db.row_factory = sqlite3.Row
        return db

    def _password_ok(self, user: str, password: str) -> bool:
        try:
            expected = self.config.operator_password_file.read_text(encoding="utf-8").rstrip("\n")
        except OSError:
            return False
        return hmac.compare_digest(user, self.config.operator_user) and hmac.compare_digest(password, expected)

    def _authenticated(self, environ: dict) -> bool:
        header = environ.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Basic "):
            return False
        try:
            user, password = base64.b64decode(header[6:], validate=True).decode("utf-8").split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False
        return self._password_ok(user, password)

    def _parse_form(self, environ: dict) -> dict[str, str]:
        try:
            size = int(environ.get("CONTENT_LENGTH", "0"))
        except ValueError:
            size = 0
        if size > MAX_FIELD * 5:
            raise ValueError("request too large")
        body = environ["wsgi.input"].read(size).decode("utf-8")
        return {key: values[-1] for key, values in urllib.parse.parse_qs(body, keep_blank_values=True).items()}

    def _headers(self, csrf: str | None = None) -> list[tuple[str, str]]:
        headers = [("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store")]
        if csrf:
            headers.append(("Set-Cookie", f"docwriter_csrf={csrf}; Path=/; Secure; HttpOnly; SameSite=Strict"))
        return headers

    def _csrf_token(self, environ: dict) -> str:
        cookies = {}
        for item in environ.get("HTTP_COOKIE", "").split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookies[key] = value
        return cookies.get("docwriter_csrf", "")

    def _csrf_valid(self, environ: dict, form: dict[str, str]) -> bool:
        expected = self._csrf_token(environ)
        supplied = form.get("csrf", "")
        return bool(expected and supplied) and hmac.compare_digest(expected, supplied)

    def _html(self, title: str, body: str, csrf: str) -> str:
        return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{html.escape(title)} · Doc Writer</title>
<style>body{{font:16px system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#18212b;background:#f7f8fa}}a{{color:#075985}}nav{{display:flex;gap:1rem;margin-bottom:2rem}}section,form{{background:#fff;border:1px solid #d5dbe1;border-radius:8px;padding:1rem;margin:1rem 0}}label{{display:block;font-weight:650;margin:.8rem 0 .25rem}}textarea,input,select{{width:100%;box-sizing:border-box;padding:.65rem;border:1px solid #aeb8c2;border-radius:5px;font:inherit}}textarea{{min-height:9rem}}button{{padding:.6rem 1rem;border:0;border-radius:5px;background:#075985;color:white;font-weight:650;cursor:pointer}}button.danger{{background:#991b1b}}.muted{{color:#52606d}}.status{{font-weight:700}}code{{background:#eef2f6;padding:.1rem .3rem;border-radius:3px;word-break:break-word}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #d5dbe1;text-align:left;padding:.5rem}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style></head><body>
<nav><a href='/'>Doc Writer</a><a href='/trial/new'>New conversational trial</a></nav>{body}</body></html>"""

    def _save_version(self, db: sqlite3.Connection, trial: sqlite3.Row, action: str) -> None:
        snapshot = json.dumps({key: trial[key] for key in trial.keys()}, sort_keys=True)
        db.execute("INSERT INTO trial_versions(trial_id, recorded_at, action, snapshot) VALUES(?,?,?,?)", (trial["trial_id"], utc_now(), action, snapshot))

    def _latest_attempt(self, db: sqlite3.Connection, trial_id: str) -> sqlite3.Row | None:
        return db.execute("SELECT * FROM generation_attempts WHERE trial_id=? ORDER BY started_at DESC LIMIT 1", (trial_id,)).fetchone()

    def _generate_trial(self, trial_id: str) -> tuple[str, str]:
        if not self._generation_lock.acquire(blocking=False):
            raise RuntimeError("another generation is already running")
        try:
            with self._db() as db:
                trial = db.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone()
                if not trial:
                    raise LookupError("trial not found")
                version = db.execute("SELECT * FROM trial_versions WHERE trial_id=? ORDER BY version_id DESC LIMIT 1", (trial_id,)).fetchone()
                if not version:
                    raise ValueError("source version is unavailable")
                attempt_id = f"generation-{secrets.token_hex(8)}"
                request_json = serialized_json(request_payload_for(trial["source_text"]))
                started_at = utc_now()
                db.execute("INSERT INTO generation_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (attempt_id, trial_id, version["version_id"], trial["source_text"], trial["source_sha256"], PROMPT_VERSION, prompt_for(trial["source_text"]), sha256_text(prompt_for(trial["source_text"])), request_json, MODEL, MODEL_DIGEST, serialized_json(GENERATION_SETTINGS), started_at, "", "", "", "[]", "", "", "", "{}", self.config.version, "RUNNING", ""))
            try:
                result = self.ollama_client.generate(trial["source_text"])
            except OllamaError as exc:
                with self._db() as db:
                    db.execute("UPDATE generation_attempts SET completed_at=?,raw_ollama_response=?,response_sha256=?,telemetry=?,status=?,error=? WHERE attempt_id=?", (utc_now(), exc.raw_response, sha256_text(exc.raw_response) if exc.raw_response else "", serialized_json(exc.response_payload), "FAILED", str(exc), attempt_id))
                return attempt_id, "failed"
            with self._db() as db:
                current = db.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone()
                if current["source_sha256"] != trial["source_sha256"]:
                    db.execute("UPDATE generation_attempts SET completed_at=?,raw_ollama_response=?,response_sha256=?,telemetry=?,status=?,error=? WHERE attempt_id=?", (result.completed_at, result.raw_ollama_response, result.response_hash, serialized_json(result.telemetry), "STALE_SOURCE", "source changed during generation", attempt_id))
                    return attempt_id, "stale"
                findings_json = json.dumps(result.integrity_findings, ensure_ascii=False, sort_keys=True)
                lineage = json.loads(current["revision_lineage"] or "[]")
                lineage.append(attempt_id)
                db.execute("UPDATE generation_attempts SET completed_at=?,raw_ollama_response=?,response_sha256=?,integrity_findings=?,normalized_proposal=?,proposal_sha256=?,source_to_proposal_diff=?,telemetry=?,status=? WHERE attempt_id=?", (result.completed_at, result.raw_ollama_response, result.response_hash, findings_json, result.proposal, result.proposal_hash, result.source_to_proposal_diff, serialized_json(result.telemetry), "COMPLETED", attempt_id))
                db.execute("UPDATE trials SET updated_at=?,model_identifier=?,model_digest=?,generation_parameters=?,integrity_findings=?,raw_output=?,normalized_output=?,review_status='REVIEW_REQUIRED',revision_lineage=? WHERE trial_id=?", (result.completed_at, result.model_identifier, result.model_digest, serialized_json(GENERATION_SETTINGS), findings_json, result.raw_ollama_response, result.proposal, json.dumps(lineage), trial_id))
                self._save_version(db, db.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone(), "GENERATED")
            return attempt_id, "completed"
        finally:
            self._generation_lock.release()

    def _render_home(self, csrf: str) -> str:
        with self._db() as db:
            count = db.execute("SELECT count(*) FROM trials WHERE review_status NOT IN ('ACCEPTED','REJECTED')").fetchone()[0]
        storage = "healthy" if self.config.runtime_root.is_dir() and os.access(self.config.state_dir, os.W_OK) else "unavailable"
        body = f"""<h1>Doc Writer</h1><p class='muted'>Authenticated local review surface. Model execution is enabled for server-owned observation-period generation.</p>
<div class='grid'><section><strong>Service health</strong><p class='status'>healthy</p></section><section><strong>Storage health</strong><p class='status'>{html.escape(storage)}</p></section><section><strong>Application version</strong><p><code>{html.escape(self.config.version)}</code></p></section><section><strong>Canonical hostname</strong><p><code>{html.escape(self.config.canonical_host)}</code></p></section><section><strong>Model execution</strong><p class='status'>enabled</p></section><section><strong>Open review trials</strong><p class='status'>{count}</p></section></div>
<section><p>Benchmark observation: strongest raw writing performance among tested candidates: Mistral Nemo.</p><p>Generated prose remains <code>REVIEW_REQUIRED</code>. Frozen benchmark evidence is read-only.</p></section>"""
        return self._html("Home", body, csrf)

    def _render_form(self, csrf: str, trial: sqlite3.Row | None = None) -> str:
        def value(key: str, default: str = "") -> str:
            return html.escape((trial[key] if trial else default) or "")
        trial_id = trial["trial_id"] if trial else ""
        action = f"/trial/{trial_id}/save" if trial_id else "/trial"
        selected = trial["model_identifier"] if trial else "mistral-nemo:12b-instruct-2407-q4_K_M"
        options = "".join(f"<option {'selected' if model == selected else ''}>{html.escape(model)}</option>" for model in MODEL_DIGESTS)
        body = f"""<h1>{'Edit trial' if trial else 'New conversational trial'}</h1><p class='muted'>This screen saves review material only. It never invokes a model.</p><form method='post' action='{action}'>
<input type='hidden' name='csrf' value='{html.escape(csrf)}'><label for='source_text'>Source paragraph</label><textarea id='source_text' name='source_text' maxlength='{MAX_SOURCE}' required>{value('source_text')}</textarea>
<label for='model_identifier'>Model-selection metadata</label><select id='model_identifier' name='model_identifier'>{options}</select>
<label for='generation_parameters'>Generation parameters (metadata only)</label><input id='generation_parameters' name='generation_parameters' maxlength='1000' value='{value('generation_parameters', '{"execution":"disabled"}')}' />
<label for='integrity_findings'>Integrity findings</label><textarea id='integrity_findings' name='integrity_findings' maxlength='{MAX_NOTES}'>{value('integrity_findings')}</textarea>
<label for='raw_output'>Raw model output (optional, operator-supplied; no execution)</label><textarea id='raw_output' name='raw_output' maxlength='{MAX_FIELD}'>{value('raw_output')}</textarea>
<label for='normalized_output'>Normalized conversational proposal (optional)</label><textarea id='normalized_output' name='normalized_output' maxlength='{MAX_FIELD}'>{value('normalized_output')}</textarea>
<label for='reviewer_notes'>Reviewer notes</label><textarea id='reviewer_notes' name='reviewer_notes' maxlength='{MAX_NOTES}'>{value('reviewer_notes')}</textarea><button type='submit'>Save draft</button></form>"""
        return self._html("New trial", body, csrf)

    def _render_trial(self, trial: sqlite3.Row, versions: list[sqlite3.Row], attempt: sqlite3.Row | None, csrf: str) -> str:
        def block(label: str, text: str) -> str:
            return f"<section><h2>{html.escape(label)}</h2><pre>{html.escape(text or '—')}</pre></section>"
        history = "".join(f"<tr><td>{v['version_id']}</td><td>{html.escape(v['recorded_at'])}</td><td>{html.escape(v['action'])}</td></tr>" for v in versions)
        generation = f"""<section><h2>Generate conversational proposal</h2><p>Server-owned model: <code>{MODEL}</code><br>Model status: installed digest reconciled before execution<br>Settings: context 8192, temperature 0.2, top-p 0.9, seed 42, streaming disabled, thinking disabled</p><p class='muted'>Execution uses local Ollama only. The result remains <code>REVIEW_REQUIRED</code> and is never accepted automatically.</p><form method='post' action='/trial/{html.escape(trial['trial_id'])}/generate' onsubmit="this.querySelector('button').disabled=true;this.querySelector('button').textContent='Generating…';"><input type='hidden' name='csrf' value='{html.escape(csrf)}'><button type='submit'>Generate conversational proposal</button></form></section>"""
        attempt_view = ""
        if attempt:
            if attempt["status"] == "FAILED":
                attempt_view = "<section><h2>Generation attempt</h2><p class='status'>Generation failed closed; the existing draft was preserved. An explicit retry creates a new attempt.</p></section>"
            elif attempt["status"] == "STALE_SOURCE":
                attempt_view = "<section><h2>Generation attempt</h2><p class='status'>Source changed during generation; the result was not applied to this draft.</p></section>"
            elif attempt["status"] == "COMPLETED":
                attempt_view = f"""<section><h2>Generation provenance</h2><p>Attempt <code>{html.escape(attempt['attempt_id'])}</code>; prompt contract <code>{html.escape(attempt['prompt_version'])}</code>; prompt SHA-256 <code>{html.escape(attempt['prompt_sha256'])}</code>; response SHA-256 <code>{html.escape(attempt['response_sha256'])}</code>; proposal SHA-256 <code>{html.escape(attempt['proposal_sha256'])}</code>; source version <code>{attempt['source_version_id']}</code>.</p><details><summary>Raw Ollama response</summary><pre>{html.escape(attempt['raw_ollama_response'])}</pre></details><h3>Exact source-to-proposal diff</h3><pre>{html.escape(attempt['source_to_proposal_diff'] or '(no textual difference)')}</pre><p>Telemetry: <code>{html.escape(attempt['telemetry'])}</code></p></section>"""
        body = f"""<h1>Trial <code>{html.escape(trial['trial_id'])}</code></h1><p class='status'>Review status: {html.escape(trial['review_status'])}</p><p>Created {html.escape(trial['created_at'])}; updated {html.escape(trial['updated_at'])}; source SHA-256 <code>{html.escape(trial['source_sha256'])}</code></p><p>Model: <code>{html.escape(trial['model_identifier'])}</code><br>Digest: <code>{html.escape(trial['model_digest'])}</code></p>
{generation}{attempt_view}
{block('Source paragraph', trial['source_text'])}{block('Integrity findings', trial['integrity_findings'])}{block('Raw model output', trial['raw_output'])}{block('Normalized proposal', trial['normalized_output'])}{block('Reviewer notes', trial['reviewer_notes'])}
<section><h2>Decision</h2><form method='post' action='/trial/{html.escape(trial['trial_id'])}/decision'><input type='hidden' name='csrf' value='{html.escape(csrf)}'><select name='decision'>{''.join(f'<option>{decision}</option>' for decision in sorted(DECISIONS))}</select><button type='submit'>Record decision</button></form></section><section><h2>Version history</h2><table><tr><th>Version</th><th>When</th><th>Action</th></tr>{history}</table></section><p><a href='/trial/{html.escape(trial['trial_id'])}/artifact'>View artifact/provenance</a> · <a href='/trial/{html.escape(trial['trial_id'])}/edit'>Edit</a></p><form method='post' action='/trial/{html.escape(trial['trial_id'])}/delete'><input type='hidden' name='csrf' value='{html.escape(csrf)}'><button class='danger' type='submit'>Delete trial</button></form>"""
        return self._html("Trial", body, csrf)

    def __call__(self, environ: dict, start_response: Callable):
        if not self._authenticated(environ):
            start_response("401 Unauthorized", [("WWW-Authenticate", 'Basic realm="Doc Writer"'), ("Cache-Control", "no-store")])
            return [b"Authentication required\n"]
        method, path = environ.get("REQUEST_METHOD", "GET"), environ.get("PATH_INFO", "/")
        csrf = self._csrf_token(environ) or secrets.token_urlsafe(24)
        try:
            if method == "GET" and path == "/":
                content = self._render_home(csrf)
            elif method == "GET" and path == "/trial/new":
                content = self._render_form(csrf)
            elif method == "POST" and path == "/trial":
                form = self._parse_form(environ); source = form.get("source_text", ""); model = form.get("model_identifier", "")
                if not self._csrf_valid(environ, form) or not source or len(source) > MAX_SOURCE or model not in MODEL_DIGESTS: raise ValueError("invalid draft or CSRF token")
                now, trial_id = utc_now(), f"trial-{secrets.token_hex(8)}"
                row = (trial_id, now, now, source, sha256_text(source), model, MODEL_DIGESTS[model], form.get("generation_parameters", "")[:1000], form.get("integrity_findings", "")[:MAX_NOTES], form.get("raw_output", "")[:MAX_FIELD], form.get("normalized_output", "")[:MAX_FIELD], "REVIEW_REQUIRED", form.get("reviewer_notes", "")[:MAX_NOTES], json.dumps([]))
                with self._db() as db:
                    db.execute("INSERT INTO trials VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row); self._save_version(db, db.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone(), "CREATED")
                start_response("303 See Other", [("Location", f"/trial/{trial_id}")]); return [b""]
            elif method == "GET" and path.startswith("/trial/"):
                parts, trial_id = path.strip("/").split("/"), path.strip("/").split("/")[1]
                with self._db() as db:
                    trial = db.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone()
                    if not trial: raise LookupError("trial not found")
                    if len(parts) == 3 and parts[2] == "edit": content = self._render_form(csrf, trial)
                    elif len(parts) == 3 and parts[2] == "artifact":
                        artifact = json.dumps({"trial_id": trial_id, "source_sha256": trial["source_sha256"], "model_identifier": trial["model_identifier"], "model_digest": trial["model_digest"], "generation_parameters": json.loads(trial["generation_parameters"] or "{}"), "review_status": trial["review_status"], "revision_lineage": json.loads(trial["revision_lineage"] or "[]")}, indent=2)
                        versions = db.execute("SELECT snapshot FROM trial_versions WHERE trial_id=? ORDER BY version_id", (trial_id,)).fetchall()
                        previous = json.loads(versions[-2]["snapshot"]) if len(versions) > 1 else {}
                        current = json.loads(versions[-1]["snapshot"]) if versions else {}
                        diff = "".join(difflib.unified_diff((previous.get("normalized_output", "") + "\n").splitlines(True), (current.get("normalized_output", "") + "\n").splitlines(True), fromfile="previous normalized proposal", tofile="current normalized proposal"))
                        content = self._html("Artifact", f"<h1>Artifact/provenance</h1><pre>{html.escape(artifact)}</pre><h2>Exact normalized-proposal diff</h2><pre>{html.escape(diff or '(no normalized proposal change)')}</pre>", csrf)
                    else: content = self._render_trial(trial, db.execute("SELECT * FROM trial_versions WHERE trial_id=? ORDER BY version_id", (trial_id,)).fetchall(), self._latest_attempt(db, trial_id), csrf)
            elif method == "POST" and path.startswith("/trial/"):
                parts, trial_id, form = path.strip("/").split("/"), path.strip("/").split("/")[1], self._parse_form(environ)
                if not self._csrf_valid(environ, form): raise PermissionError("CSRF validation failed")
                if len(parts) == 3 and parts[2] == "generate":
                    self._generate_trial(trial_id)
                    start_response("303 See Other", [("Location", f"/trial/{trial_id}")]); return [b""]
                with self._db() as db:
                    trial = db.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone()
                    if not trial: raise LookupError("trial not found")
                    if parts[2] == "delete":
                        db.execute("DELETE FROM trial_versions WHERE trial_id=?", (trial_id,)); db.execute("DELETE FROM trials WHERE trial_id=?", (trial_id,))
                    elif parts[2] == "decision":
                        decision = form.get("decision", "")
                        if decision not in DECISIONS: raise ValueError("invalid decision")
                        db.execute("UPDATE trials SET review_status=?,updated_at=? WHERE trial_id=?", (decision, utc_now(), trial_id)); self._save_version(db, db.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone(), f"DECISION_{decision}")
                    elif parts[2] == "save":
                        source, model = form.get("source_text", ""), form.get("model_identifier", "")
                        if not source or len(source) > MAX_SOURCE or model not in MODEL_DIGESTS: raise ValueError("invalid draft")
                        db.execute("UPDATE trials SET updated_at=?,source_text=?,source_sha256=?,model_identifier=?,model_digest=?,generation_parameters=?,integrity_findings=?,raw_output=?,normalized_output=?,reviewer_notes=?,review_status='REVIEW_REQUIRED' WHERE trial_id=?", (utc_now(), source, sha256_text(source), model, MODEL_DIGESTS[model], form.get("generation_parameters", "")[:1000], form.get("integrity_findings", "")[:MAX_NOTES], form.get("raw_output", "")[:MAX_FIELD], form.get("normalized_output", "")[:MAX_FIELD], form.get("reviewer_notes", "")[:MAX_NOTES], trial_id)); self._save_version(db, db.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone(), "EDITED")
                start_response("303 See Other", [("Location", f"/trial/{trial_id}")]); return [b""]
            else:
                start_response("404 Not Found", self._headers()); return [b"Not found\n"]
        except PermissionError as exc:
            start_response("403 Forbidden", self._headers()); return [str(exc).encode()]
        except RuntimeError as exc:
            start_response("409 Conflict", self._headers()); return [str(exc).encode()]
        except (LookupError, ValueError) as exc:
            start_response("400 Bad Request", self._headers()); return [str(exc).encode()]
        start_response("200 OK", self._headers(csrf)); return [content.encode("utf-8")]
