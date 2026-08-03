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
        return cls(runtime, os.environ.get("DOCWRITER_OPERATOR_USER", "operator"), password_file, secret, canonical_host=os.environ.get("DOCWRITER_CANONICAL_HOST", "docwriter.home.arpa"), version=os.environ.get("DOCWRITER_APP_VERSION", "generation-v1"), ollama_url=os.environ.get("DOCWRITER_OLLAMA_URL", "http://127.0.0.1:11434"))


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
                CREATE TABLE IF NOT EXISTS review_events (
                    event_id TEXT PRIMARY KEY, trial_id TEXT NOT NULL REFERENCES trials(trial_id),
                    generation_attempt_id TEXT REFERENCES generation_attempts(attempt_id),
                    event_type TEXT NOT NULL, decision TEXT, note_text TEXT,
                    private_steering INTEGER NOT NULL DEFAULT 0, related_passage TEXT,
                    reviewer_identity TEXT, created_at TEXT NOT NULL, prior_event_id TEXT,
                    content_hash TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS review_events_trial_idx ON review_events(trial_id, created_at);
            """)
            legacy = db.execute("SELECT trial_id, recorded_at, action, snapshot FROM trial_versions WHERE action LIKE 'DECISION_%'").fetchall()
            for row in legacy:
                decision = row["action"][len("DECISION_"):]
                if decision not in DECISIONS:
                    continue
                event_id = f"review-legacy-{row['trial_id']}-{row['recorded_at']}"
                exists = db.execute("SELECT 1 FROM review_events WHERE event_id=?", (event_id,)).fetchone()
                if exists:
                    continue
                payload = {"event_id": event_id, "trial_id": row["trial_id"], "event_type": "DECISION", "decision": decision, "note_text": "", "private_steering": False, "related_passage": "", "reviewer_identity": "", "created_at": row["recorded_at"], "prior_event_id": None}
                db.execute("INSERT INTO review_events(event_id,trial_id,generation_attempt_id,event_type,decision,note_text,private_steering,related_passage,reviewer_identity,created_at,prior_event_id,content_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (event_id, row["trial_id"], None, "DECISION", decision, "", 0, "", "", row["recorded_at"], None, sha256_text(json.dumps(payload, sort_keys=True))))

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

    def _authenticated_user(self, environ: dict) -> str:
        header = environ.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Basic "):
            return ""
        try:
            user, password = base64.b64decode(header[6:], validate=True).decode("utf-8").split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return ""
        return user if self._password_ok(user, password) else ""

    def _review_events(self, db: sqlite3.Connection, trial_id: str) -> list[sqlite3.Row]:
        return db.execute("SELECT * FROM review_events WHERE trial_id=? ORDER BY created_at, event_id", (trial_id,)).fetchall()

    def _review_rationale_missing(self, events: list[sqlite3.Row], status: str) -> bool:
        if status not in {"REJECTED", "REVISION_REQUIRED"}:
            return False
        return not any(event["event_type"] == "REVIEW_NOTE" and (event["note_text"] or "").strip() for event in events)

    def _insert_review_event(self, db: sqlite3.Connection, trial_id: str, event_type: str, decision: str | None, note_text: str, private_steering: bool, related_passage: str, reviewer_identity: str, generation_attempt_id: str | None = None, created_at: str | None = None) -> str:
        prior = db.execute("SELECT event_id FROM review_events WHERE trial_id=? ORDER BY created_at DESC, event_id DESC LIMIT 1", (trial_id,)).fetchone()
        event_id, timestamp = f"review-{secrets.token_hex(8)}", created_at or utc_now()
        payload = {"event_id": event_id, "trial_id": trial_id, "generation_attempt_id": generation_attempt_id, "event_type": event_type, "decision": decision, "note_text": note_text, "private_steering": bool(private_steering), "related_passage": related_passage, "reviewer_identity": reviewer_identity, "created_at": timestamp, "prior_event_id": prior["event_id"] if prior else None}
        db.execute("INSERT INTO review_events(event_id,trial_id,generation_attempt_id,event_type,decision,note_text,private_steering,related_passage,reviewer_identity,created_at,prior_event_id,content_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (event_id, trial_id, generation_attempt_id, event_type, decision, note_text, int(private_steering), related_passage, reviewer_identity, timestamp, payload["prior_event_id"], sha256_text(json.dumps(payload, sort_keys=True))))
        return event_id

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
        style = """        :root {
          color-scheme: light;
          --ink: #182631;
          --ink-soft: #526575;
          --paper: #fbfcfd;
          --canvas: #e9eef1;
          --line: #d3dde2;
          --blue: #176b91;
          --blue-deep: #0e4058;
          --copper: #b76638;
          --green: #26734d;
          --amber: #8a6417;
          --red: #a23b35;
        }
        * { box-sizing: border-box; }
        body { margin: 0; min-height: 100vh; background: var(--canvas); color: var(--ink); font: 16px/1.65 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        body::before { content: ""; display: block; height: 4px; background: linear-gradient(90deg, var(--copper) 0 18%, var(--blue) 18% 100%); }
        a { color: var(--blue-deep); text-decoration: none; }
        a:hover { color: var(--copper); text-decoration: underline; }
        header { background: var(--ink); color: #eef4f6; padding: 1.2rem max(1.25rem, calc((100vw - 1180px) / 2)); box-shadow: 0 3px 12px #10212c33; }
        .brand { color: #fff; font-size: 1.45rem; font-weight: 800; letter-spacing: -.025em; }
        header nav { display: flex; flex-wrap: wrap; gap: .45rem 1.2rem; align-items: center; margin-top: .7rem; }
        header nav a { color: #c9d9df; font-size: .94rem; font-weight: 650; }
        header nav a:hover { color: #fff; }
        .health { margin-left: auto; color: #a9bbc3; font-size: .85rem; }
        main { max-width: 1040px; margin: 0 auto; padding: 2.5rem 1.25rem 5rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: -.02em; }
        h1 { margin: 0 0 .45rem; font-size: clamp(1.85rem, 4vw, 2.7rem); line-height: 1.08; }
        h2 { margin: .1rem 0 .7rem; font-size: 1.25rem; line-height: 1.25; }
        h3 { margin: 0 0 .25rem; font-size: 1rem; }
        section, form, .panel { margin: 1.1rem 0; padding: 1.35rem; background: var(--paper); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 8px 22px #20323d0b; }
        .actions { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; }
        .muted, .meta { color: var(--ink-soft); }
        .meta { font-size: .88rem; }
        label { display: block; margin: .8rem 0 .3rem; color: var(--ink); font-weight: 750; }
        textarea, input, select { width: 100%; padding: .7rem .75rem; border: 1px solid #aebdc5; border-radius: 7px; background: #fff; color: var(--ink); font: inherit; }
        textarea { min-height: 9rem; }
        textarea:focus, input:focus, select:focus, button:focus, a.button:focus { outline: 3px solid #6db5d2; outline-offset: 2px; }
        input[type="checkbox"] { width: auto; margin-right: .4rem; accent-color: var(--blue); }
        button, .button { display: inline-block; padding: .68rem 1rem; border: 1px solid transparent; border-radius: 7px; background: var(--blue); color: #fff; font-weight: 750; cursor: pointer; text-decoration: none; transition: background .12s ease, transform .12s ease; }
        button:hover, .button:hover { background: var(--blue-deep); color: #fff; text-decoration: none; transform: translateY(-1px); }
        button.secondary, .button.secondary { background: #e3ebee; color: var(--blue-deep); }
        button.danger { background: var(--red); }
        .badge { display: inline-block; padding: .22rem .65rem; border-radius: 999px; background: #e1ebef; color: var(--blue-deep); font-size: .78rem; font-weight: 800; letter-spacing: .025em; white-space: nowrap; }
        .badge.review { background: #fff0c2; color: var(--amber); }
        .badge.accepted { background: #dcefe3; color: var(--green); }
        .badge.rejected { background: #f6dfdc; color: var(--red); }
        .badge.revision { background: #f9e8d8; color: #934b1d; }
        .badge.failed { background: #eadff1; color: #70437e; }
        .notice { padding: .75rem 1rem; border-left: 4px solid var(--green); border-radius: 6px; background: #e7f4eb; color: #1d5c3e; font-weight: 700; }
        .error { padding: .75rem 1rem; border-left: 4px solid var(--red); border-radius: 6px; background: #fbe8e5; color: #862f2b; font-weight: 700; }
        .trial-list { display: grid; gap: .85rem; }
        .trial-card { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1rem; align-items: center; padding: 1.1rem 1.2rem; background: var(--paper); border: 1px solid var(--line); border-left: 4px solid #9fb6c0; border-radius: 10px; box-shadow: 0 4px 12px #20323d0b; }
        .trial-card:hover { border-left-color: var(--copper); box-shadow: 0 7px 18px #20323d18; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: .85rem; }
        .grid section { margin: 0; }
        .prose { max-width: 72ch; margin: 0 auto; padding: 1.15rem 1.35rem; background: #fff; border-left: 4px solid var(--blue); border-radius: 4px; font-family: Georgia, "Times New Roman", serif; font-size: 1.16rem; line-height: 1.82; white-space: pre-wrap; }
        pre { white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; }
        table { width: 100%; border-collapse: collapse; font-size: .93rem; }
        th, td { padding: .62rem .55rem; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
        th { color: var(--ink-soft); font-size: .76rem; letter-spacing: .06em; text-transform: uppercase; }
        .quiet { background: #f4f7f8; border-color: #dce5e8; }
        .filters { display: flex; flex-wrap: wrap; gap: .45rem; align-items: center; }
        .filters a { padding: .35rem .72rem; border: 1px solid var(--line); border-radius: 999px; background: #f5f8f9; color: var(--blue-deep); font-size: .9rem; font-weight: 650; }
        .filters a.active { border-color: var(--blue); background: var(--blue); color: #fff; }
        details > summary { cursor: pointer; color: var(--blue-deep); font-weight: 750; }
        details > summary:hover { color: var(--copper); }
        code { padding: .1rem .3rem; border-radius: 4px; background: #e8eef0; color: var(--blue-deep); font-size: .9em; }
        @media (max-width: 700px) { main { padding-top: 1.5rem; } .trial-card { grid-template-columns: 1fr; } .health { width: 100%; margin-left: 0; } }
        """
        return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{html.escape(title)} · Doc Writer</title><style>{style}</style></head><body><header><a class='brand' href='/'>Doc Writer</a><nav><a href='/'>Review queue</a><a href='/trials'>All trials</a><a href='/trial/new'>New trial</a><a href='/system'>System status</a><span class='health'>Local review service · <a href='/system'>status</a></span></nav></header><main>{body}</main></body></html>"""
        return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{html.escape(title)} · Doc Writer</title>
<style>:root{{color-scheme:light}}body{{font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:1180px;margin:0 auto;padding:0 1.25rem 4rem;color:#1f2933;background:#f6f7f9}}a{{color:#075985;text-decoration:none}}a:hover{{text-decoration:underline}}header{{padding:1.25rem 0 1rem;border-bottom:1px solid #d9e0e7;margin-bottom:2rem}}.brand{{font-size:1.35rem;font-weight:750;color:#18212b}}nav{{display:flex;flex-wrap:wrap;gap:1rem;margin-top:.7rem;align-items:center}}.health{{margin-left:auto;color:#52606d;font-size:.9rem}}main{{max-width:1040px;margin:0 auto}}section,form,.panel{{background:#fff;border:1px solid #d9e0e7;border-radius:10px;padding:1.25rem;margin:1rem 0;box-shadow:0 1px 2px #172b4d0d}}h1{{font-size:2rem;line-height:1.2;margin:0 0 .5rem}}h2{{font-size:1.25rem;line-height:1.3;margin:.1rem 0 .75rem}}h3{{font-size:1rem;margin:1.25rem 0 .5rem}}label{{display:block;font-weight:700;margin:.8rem 0 .25rem}}textarea,input,select{{width:100%;box-sizing:border-box;padding:.7rem;border:1px solid #aeb8c2;border-radius:6px;font:inherit;background:#fff}}textarea{{min-height:9rem}}input[type=checkbox]{{width:auto;margin-right:.4rem}}button,.button{{display:inline-block;padding:.65rem 1rem;border:0;border-radius:6px;background:#075985;color:white;font-weight:700;cursor:pointer;text-decoration:none}}button:hover,.button:hover{{background:#064a6b;text-decoration:none}}button.secondary,.button.secondary{{background:#e7eef3;color:#164e63}}button.danger{{background:#991b1b}}.muted{{color:#52606d}}.status{{font-weight:700}}.badge{{display:inline-block;border-radius:999px;padding:.2rem .65rem;font-size:.82rem;font-weight:750;white-space:nowrap;background:#e7eef3;color:#164e63}}.badge.review{{background:#fff1c7;color:#7a4d00}}.badge.accepted{{background:#dcfce7;color:#166534}}.badge.rejected{{background:#fee2e2;color:#991b1b}}.badge.revision{{background:#ffedd5;color:#9a3412}}.badge.failed{{background:#f3e8ff;color:#6b21a8}}.notice{{padding:.7rem 1rem;border-radius:6px;background:#ecfdf5;color:#166534;font-weight:700}}.error{{padding:.7rem 1rem;border-radius:6px;background:#fef2f2;color:#991b1b;font-weight:650}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}}.trial-list{{display:grid;gap:.8rem}}.trial-card{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:1rem;align-items:center;background:#fff;border:1px solid #d9e0e7;border-radius:10px;padding:1rem 1.15rem}}.trial-card h3{{margin:0 0 .25rem}}.meta{{color:#52606d;font-size:.9rem}}.actions{{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}}table{{border-collapse:collapse;width:100%;font-size:.94rem}}td,th{{border-bottom:1px solid #d5dbe1;text-align:left;padding:.6rem;vertical-align:top}}th{{color:#52606d;font-size:.85rem;text-transform:uppercase;letter-spacing:.03em}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}}.prose{{font-family:Georgia,'Times New Roman',serif;font-size:1.12rem;line-height:1.75;white-space:pre-wrap}}.quiet{{background:#f8fafc;border-color:#e5e7eb}}.filters{{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}}.filters a{{padding:.35rem .7rem;border-radius:999px;background:#e7eef3}}.filters a.active{{background:#075985;color:#fff}}@media(max-width:700px){{.trial-card{{grid-template-columns:1fr}}.health{{margin-left:0;width:100%}}}}
</style></head><body><header><a class='brand' href='/'>Doc Writer</a><nav><a href='/'>Review queue</a><a href='/trials'>All trials</a><a href='/trial/new'>New trial</a><a href='/system'>System status</a><span class='health'>Local review service · <a href='/system'>status</a></span></nav></header><main>{body}</main></body></html>"""

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

    def _status_badge(self, status: str, rationale_missing: bool = False) -> str:
        style = {"ACCEPTED": "accepted", "REJECTED": "rejected", "REVISION_REQUIRED": "revision", "REVIEW_REQUIRED": "review"}.get(status, "")
        label = status + (" · REVIEW_RATIONALE_MISSING" if rationale_missing else "")
        return f"<span class='badge {style}'>{html.escape(label)}</span>"

    def _trial_rows(self, db: sqlite3.Connection, status_filter: str = "all", search: str = "") -> list[sqlite3.Row]:
        conditions, params = [], []
        if status_filter in DECISIONS or status_filter == "REVIEW_REQUIRED":
            conditions.append("t.review_status=?"); params.append(status_filter)
        elif status_filter == "needs_review":
            conditions.append("(t.review_status IN ('REVIEW_REQUIRED','REVISION_REQUIRED') OR (t.review_status IN ('REJECTED','REVISION_REQUIRED') AND NOT EXISTS (SELECT 1 FROM review_events rn WHERE rn.trial_id=t.trial_id AND rn.event_type='REVIEW_NOTE' AND trim(COALESCE(rn.note_text,''))<>'')))")
        elif status_filter == "generation_failed":
            conditions.append("EXISTS (SELECT 1 FROM generation_attempts gf WHERE gf.trial_id=t.trial_id AND gf.status='FAILED')")
        elif status_filter == "rationale_missing":
            conditions.append("t.review_status IN ('REJECTED','REVISION_REQUIRED') AND NOT EXISTS (SELECT 1 FROM review_events rn WHERE rn.trial_id=t.trial_id AND rn.event_type='REVIEW_NOTE' AND trim(COALESCE(rn.note_text,''))<>'')")
        if search:
            term = f"%{search}%"
            conditions.append("(t.trial_id LIKE ? OR t.source_text LIKE ? OR t.model_identifier LIKE ? OR EXISTS (SELECT 1 FROM review_events rs WHERE rs.trial_id=t.trial_id AND rs.event_type='REVIEW_NOTE' AND rs.private_steering=0 AND rs.note_text LIKE ?))")
            params.extend([term, term, term, term])
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        return db.execute(f"""SELECT t.*, (SELECT count(*) FROM generation_attempts ga WHERE ga.trial_id=t.trial_id) AS attempt_count,
            EXISTS (SELECT 1 FROM review_events rn WHERE rn.trial_id=t.trial_id AND rn.event_type='REVIEW_NOTE' AND trim(COALESCE(rn.note_text,''))<>'') AS has_notes,
            EXISTS (SELECT 1 FROM review_events ps WHERE ps.trial_id=t.trial_id AND ps.event_type='REVIEW_NOTE' AND ps.private_steering=1) AS has_private,
            (SELECT decision FROM review_events de WHERE de.trial_id=t.trial_id AND de.event_type='DECISION' ORDER BY de.created_at DESC, de.event_id DESC LIMIT 1) AS latest_decision,
            EXISTS (SELECT 1 FROM generation_attempts gf WHERE gf.trial_id=t.trial_id AND gf.status='FAILED') AS has_failed
            FROM trials t{where} ORDER BY t.updated_at DESC, t.trial_id DESC""", params).fetchall()

    def _render_trial_card(self, row: sqlite3.Row) -> str:
        rationale_missing = row["review_status"] in {"REJECTED", "REVISION_REQUIRED"} and not row["has_notes"]
        excerpt = " ".join((row["source_text"] or "").split())[:180]
        flags = []
        if row["has_notes"]: flags.append("notes")
        if row["has_private"]: flags.append("private steering")
        if row["has_failed"]: flags.append("generation failed")
        flag_text = " · ".join(flags) if flags else "no reviewer notes"
        return f"<article class='trial-card'><div><h3>{html.escape(excerpt or 'Untitled trial')}</h3><div class='meta'><code>{html.escape(row['trial_id'])}</code> · created {html.escape(row['created_at'])} · updated {html.escape(row['updated_at'])}</div><p>{self._status_badge(row['review_status'], rationale_missing)} <span class='meta'>{html.escape(row['model_identifier'])} · {row['attempt_count']} generation attempt(s) · {html.escape(flag_text)}</span></p></div><div class='actions'><a class='button' href='/trial/{html.escape(row['trial_id'])}'>Open</a></div></article>"

    def _render_trials(self, csrf: str, status_filter: str = "all", search: str = "") -> str:
        with self._db() as db:
            rows = self._trial_rows(db, status_filter, search)
        filters = [("all", "All"), ("needs_review", "Needs review"), ("REVISION_REQUIRED", "Revision required"), ("ACCEPTED", "Accepted"), ("REJECTED", "Rejected"), ("generation_failed", "Generation failed"), ("rationale_missing", "Rationale missing")]
        filter_links = "".join(f"<a class='{('active' if status_filter == key else '')}' href='/trials{('?status=' + key if key != 'all' else '')}'>{label}</a>" for key, label in filters)
        cards = "".join(self._render_trial_card(row) for row in rows) or "<section class='quiet'><h2>No trials found</h2><p class='muted'>Try another filter or search, or create a new conversational trial.</p></section>"
        body = f"""<div class='actions'><div><h1>All trials</h1><p class='muted'>Every non-deleted writing review, including closed and failed attempts.</p></div><a class='button' href='/trial/new'>New conversational trial</a></div><form method='post' action='/trials'><input type='hidden' name='csrf' value='{html.escape(csrf)}'><label for='trial-search'>Search trials</label><input id='trial-search' name='search' value='{html.escape(search)}' placeholder='Trial ID, source excerpt, model, or reviewer note'><button type='submit'>Search</button></form><div class='filters' aria-label='Trial filters'>{filter_links}</div><p class='muted'>{len(rows)} trial(s)</p><div class='trial-list'>{cards}</div>"""
        return self._html("All trials", body, csrf)

    def _render_home(self, csrf: str) -> str:
        with self._db() as db:
            queue = self._trial_rows(db, "needs_review")[:8]
            recent = self._trial_rows(db, "all")[:8]
        queue_cards = "".join(self._render_trial_card(row) for row in queue) or "<section class='quiet'><h2>Queue clear</h2><p class='muted'>No trial currently needs review.</p></section>"
        recent_cards = "".join(self._render_trial_card(row) for row in recent) or "<section class='quiet'><h2>No trials yet</h2><p class='muted'>Start with a new conversational trial.</p></section>"
        body = f"""<div class='actions'><div><h1>Review queue</h1><p class='muted'>Read the source, compare the proposal, and leave a durable review record.</p></div><a class='button' href='/trial/new'>New conversational trial</a></div><section><h2>Trials needing review</h2><div class='trial-list'>{queue_cards}</div></section><section><h2>Recently updated</h2><div class='trial-list'>{recent_cards}</div></section><section class='quiet'><p><strong>Model observation:</strong> Mistral Nemo showed the strongest raw writing performance among tested candidates. Generated prose remains <code>REVIEW_REQUIRED</code> until an operator decision.</p><p><a href='/system'>System status</a> · <a href='/trials'>Browse all trials</a></p></section>"""
        return self._html("Review queue", body, csrf)

    def _render_system(self, csrf: str) -> str:
        with self._db() as db:
            trial_count = db.execute("SELECT count(*) FROM trials").fetchone()[0]
        storage = "healthy" if self.config.runtime_root.is_dir() and os.access(self.config.state_dir, os.W_OK) else "unavailable"
        version = self.config.version if self.config.version else "unversioned"
        body = f"""<h1>System status</h1><p class='muted'>Operational details for the authenticated local review service.</p><div class='grid'><section><strong>Service</strong><p class='status'>healthy</p></section><section><strong>Storage</strong><p class='status'>{html.escape(storage)}</p></section><section><strong>Model execution</strong><p class='status'>enabled · local only</p></section><section><strong>Application version</strong><p>{html.escape('Doc Writer review application · ' + version[:12])}</p></section><section><strong>Canonical hostname</strong><p><code>{html.escape(self.config.canonical_host)}</code></p></section><section><strong>Trials retained</strong><p class='status'>{trial_count}</p></section></div><p><a href='/'>Return to review queue</a></p>"""
        return self._html("System status", body, csrf)

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

    def _render_trial(self, trial: sqlite3.Row, versions: list[sqlite3.Row], attempts: list[sqlite3.Row], review_events: list[sqlite3.Row], csrf: str, review_error: str = "", review_notice: str = "") -> str:
        attempt = attempts[0] if attempts else None
        def block(label: str, text: str) -> str:
            return f"<section><h2>{html.escape(label)}</h2><pre>{html.escape(text or '—')}</pre></section>"
        history = "".join(f"<tr><td>{v['version_id']}</td><td>{html.escape(v['recorded_at'])}</td><td>{html.escape(v['action'])}</td></tr>" for v in versions)
        rationale_missing = self._review_rationale_missing(review_events, trial["review_status"])
        review_status = html.escape(trial["review_status"] + (" · REVIEW_RATIONALE_MISSING" if rationale_missing else ""))
        review_history = "".join(f"<tr><td>{html.escape(event['created_at'])}</td><td>{html.escape(event['reviewer_identity'] or 'legacy / unavailable')}</td><td>{html.escape(event['event_type'])}</td><td>{html.escape(event['decision'] or '')}</td><td>{html.escape(event['note_text'] or '—')}</td><td>{'private steering' if event['private_steering'] else 'review note'}</td></tr>" for event in review_events)
        review_error_html = f"<p class='error' id='review-error'>{html.escape(review_error)}</p>" if review_error else (f"<p class='status' id='review-saved'>{html.escape(review_notice)}</p>" if review_notice else "")
        current_note = next((event["note_text"] for event in reversed(review_events) if event["event_type"] == "REVIEW_NOTE" and (event["note_text"] or "").strip()), "")
        review_form = f"""<section><h2>Operator review record</h2>{review_error_html}<p>Review notes are durable review material, not publishable document prose. Private steering is stored and displayed separately.</p><form method='post' action='/trial/{html.escape(trial['trial_id'])}/review'><input type='hidden' name='csrf' value='{html.escape(csrf)}'><label for='review_note'>Current reviewer note / rationale</label><textarea id='review_note' name='note_text' maxlength='{MAX_NOTES}' aria-describedby='review-help'>{html.escape(current_note)}</textarea><p id='review-help' class='muted'>Describe what sounded generic, what did not sound like the operator, exact rejected passages, and preferred replacement wording.</p><label for='related_passage'>Exact phrase or passage, if applicable</label><textarea id='related_passage' name='related_passage' maxlength='{MAX_NOTES}'></textarea><label><input type='checkbox' name='private_steering' value='1'> Private operator aside / steering note (never publishable prose)</label><button type='submit'>Save review note</button></form><h3>Review history</h3><table><tr><th>Timestamp</th><th>Reviewer</th><th>Event</th><th>Decision</th><th>Note</th><th>Visibility</th></tr>{review_history or '<tr><td colspan="6">No review events recorded.</td></tr>'}</table></section>"""
        generation = f"""<section><h2>Generate conversational proposal</h2><p>Server-owned model: <code>{MODEL}</code><br>Model status: installed digest reconciled before execution<br>Settings: context 8192, temperature 0.2, top-p 0.9, seed 42, streaming disabled, thinking disabled</p><p class='muted'>Execution uses local Ollama only. The result remains <code>REVIEW_REQUIRED</code> and is never accepted automatically.</p><form method='post' action='/trial/{html.escape(trial['trial_id'])}/generate' onsubmit="this.querySelector('button').disabled=true;this.querySelector('button').textContent='Generating…';"><input type='hidden' name='csrf' value='{html.escape(csrf)}'><button type='submit'>Generate conversational proposal</button></form></section>"""
        attempt_view = ""
        diff_view = ""
        if attempt:
            if attempt["status"] == "FAILED":
                attempt_view = "<section><h2>Generation attempt</h2><p class='status'>Generation failed closed; the existing draft was preserved. An explicit retry creates a new attempt.</p></section>"
            elif attempt["status"] == "STALE_SOURCE":
                attempt_view = "<section><h2>Generation attempt</h2><p class='status'>Source changed during generation; the result was not applied to this draft.</p></section>"
            elif attempt["status"] == "COMPLETED":
                diff_view = f"""<section><h2>Exact diff</h2><pre class='prose'>{html.escape(attempt['source_to_proposal_diff'] or '(no textual difference)')}</pre></section>"""
                attempt_view = f"""<details class='panel'><summary><strong>Full provenance and raw model output</strong></summary><p>Attempt <code>{html.escape(attempt['attempt_id'])}</code>; prompt contract <code>{html.escape(attempt['prompt_version'])}</code>; prompt SHA-256 <code>{html.escape(attempt['prompt_sha256'])}</code>; response SHA-256 <code>{html.escape(attempt['response_sha256'])}</code>; proposal SHA-256 <code>{html.escape(attempt['proposal_sha256'])}</code>; source version <code>{attempt['source_version_id']}</code>.</p><details><summary>Raw Ollama response</summary><pre>{html.escape(attempt['raw_ollama_response'])}</pre></details><p>Telemetry: <code>{html.escape(attempt['telemetry'])}</code></p></details>"""
        generation_history = "".join(f"<tr><td>{html.escape(item['started_at'])}</td><td>{html.escape(item['completed_at'] or 'running')}</td><td>{html.escape(item['status'])}</td><td>{html.escape(item['model_identifier'])}</td><td>{item['source_version_id']}</td><td>{html.escape(item['error'] or '—')}</td></tr>" for item in attempts) or "<tr><td colspan='6'>No generation attempts recorded.</td></tr>"
        body = f"""<h1>Trial <code>{html.escape(trial['trial_id'])}</code></h1><p class='status'>Review status: {review_status}</p><p>Created {html.escape(trial['created_at'])}; updated {html.escape(trial['updated_at'])}; source SHA-256 <code>{html.escape(trial['source_sha256'])}</code></p><p>Model: <code>{html.escape(trial['model_identifier'])}</code><br>Digest: <code>{html.escape(trial['model_digest'])}</code></p>
{generation}{block('Source paragraph', trial['source_text'])}<section><h2>Conversational proposal</h2><div class='prose'>{html.escape(trial['normalized_output'] or 'No normalized proposal recorded.')}</div></section>{diff_view}{block('Integrity findings', trial['integrity_findings'])}{review_form}{attempt_view}
<section><h2>Decision</h2><form method='post' action='/trial/{html.escape(trial['trial_id'])}/decision'><input type='hidden' name='csrf' value='{html.escape(csrf)}'><label for='decision'>Decision</label><select id='decision' name='decision'>{''.join(f'<option>{decision}</option>' for decision in sorted(DECISIONS))}</select><label for='decision_reason'>Decision rationale (required for rejection or revision)</label><textarea id='decision_reason' name='decision_reason' maxlength='{MAX_NOTES}'></textarea><button type='submit'>Record decision</button></form></section><section><h2>Generation-attempt history</h2><table><tr><th>Started</th><th>Completed</th><th>Status</th><th>Model</th><th>Source version</th><th>Result</th></tr>{generation_history}</table></section><section><h2>Draft version history</h2><table><tr><th>Version</th><th>When</th><th>Action</th></tr>{history}</table></section><p><a href='/trial/{html.escape(trial['trial_id'])}/artifact'>View artifact/provenance</a> · <a href='/trial/{html.escape(trial['trial_id'])}/edit'>Edit</a></p><form method='post' action='/trial/{html.escape(trial['trial_id'])}/delete'><input type='hidden' name='csrf' value='{html.escape(csrf)}'><button class='danger' type='submit'>Delete trial</button></form>"""
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
            elif method == "GET" and path == "/system":
                content = self._render_system(csrf)
            elif method == "GET" and path == "/trials":
                query = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))
                status_filter = query.get("status", ["all"])[0]
                content = self._render_trials(csrf, status_filter if status_filter else "all")
            elif method == "POST" and path == "/trials":
                form = self._parse_form(environ)
                if not self._csrf_valid(environ, form):
                    raise PermissionError("CSRF validation failed")
                content = self._render_trials(csrf, "all", form.get("search", "").strip()[:MAX_NOTES])
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
                    else: content = self._render_trial(trial, db.execute("SELECT * FROM trial_versions WHERE trial_id=? ORDER BY version_id", (trial_id,)).fetchall(), db.execute("SELECT * FROM generation_attempts WHERE trial_id=? ORDER BY started_at DESC", (trial_id,)).fetchall(), self._review_events(db, trial_id), csrf, review_notice="Review note saved." if urllib.parse.parse_qs(environ.get("QUERY_STRING", "")).get("review_saved") == ["1"] else "")
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
                        db.execute("DELETE FROM review_events WHERE trial_id=?", (trial_id,))
                        db.execute("DELETE FROM trial_versions WHERE trial_id=?", (trial_id,)); db.execute("DELETE FROM trials WHERE trial_id=?", (trial_id,))
                    elif parts[2] == "review":
                        note_text = form.get("note_text", "").strip()[:MAX_NOTES]
                        related_passage = form.get("related_passage", "").strip()[:MAX_NOTES]
                        private_steering = form.get("private_steering", "") == "1"
                        if not note_text:
                            raise ValueError("Reviewer note is required; enter the rationale or operator aside beside the review field.")
                        self._insert_review_event(db, trial_id, "REVIEW_NOTE", None, note_text, private_steering, related_passage, self._authenticated_user(environ))
                        db.execute("UPDATE trials SET updated_at=? WHERE trial_id=?", (utc_now(), trial_id))
                        start_response("303 See Other", [("Location", f"/trial/{trial_id}?review_saved=1")]); return [b""]
                    elif parts[2] == "decision":
                        decision = form.get("decision", "")
                        if decision not in DECISIONS: raise ValueError("invalid decision")
                        reason = form.get("decision_reason", "").strip()[:MAX_NOTES]
                        if decision in {"REJECTED", "REVISION_REQUIRED"} and not reason:
                            raise ValueError(f"{decision} requires a non-empty rationale beside the decision field.")
                        now = utc_now()
                        event_id = self._insert_review_event(db, trial_id, "DECISION", decision, reason, False, "", self._authenticated_user(environ))
                        db.execute("UPDATE trials SET review_status=?,updated_at=? WHERE trial_id=?", (decision, now, trial_id)); self._save_version(db, db.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone(), f"DECISION_{decision}")
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
            start_response("400 Bad Request", self._headers()); return [f"<p class='error' id='review-error'>{html.escape(str(exc))}</p>".encode()]
        start_response("200 OK", self._headers(csrf)); return [content.encode("utf-8")]
