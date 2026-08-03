"""Named, additive, idempotent Phase A migrations for Doc Writer."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Callable


TERMINAL_ATTEMPT_STATUSES = {
    "COMPLETED",
    "FAILED",
    "STALE_SOURCE",
    "INTERRUPTED",
    "REQUEST_TIMEOUT",
}
MIGRATION_NAMES = (
    "archive-and-recovery-v1",
    "foreign-keys-per-connection-v1",
    "canonical-trial-routing-v1",
    "generation-attempt-events-v1",
    "terminal-attempt-immutability-v1",
    "review-events-append-only-v1",
    "review-event-chain-v1",
    "legacy-review-supersession-v1",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _database_hash(db: sqlite3.Connection) -> str:
    # Hash the logical database rather than a live file path. This is stable
    # for tests and does not require reading private row bodies into evidence.
    rows = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
    return hashlib.sha256("\n".join(json.dumps(tuple(row), ensure_ascii=False) for row in rows).encode()).hexdigest()


def _counts(db: sqlite3.Connection) -> dict[str, int]:
    tables = ["projects", "trials", "trial_versions", "generation_attempts", "review_events", "project_migration_events"]
    return {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in tables if _table_exists(db, table)}


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _column_exists(db: sqlite3.Connection, table: str, column: str) -> bool:
    return column in {row[1] for row in db.execute(f"PRAGMA table_info({table})")}


def _ledger(db: sqlite3.Connection, name: str, commit: str, before: dict[str, int], before_hash: str, result: str = "validated") -> None:
    after = _counts(db)
    db.execute(
        "INSERT INTO schema_migrations(migration_name,applied_at,application_commit,rows_before,rows_after,database_sha256_before,validation_result) VALUES(?,?,?,?,?,?,?)",
        (name, _now(), commit, json.dumps(before, sort_keys=True), json.dumps(after, sort_keys=True), before_hash, result),
    )


def _migration_applied(db: sqlite3.Connection, name: str) -> bool:
    return db.execute("SELECT 1 FROM schema_migrations WHERE migration_name=?", (name,)).fetchone() is not None


def _add_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not _column_exists(db, table, column):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _archive_and_recovery(db: sqlite3.Connection, commit: str) -> None:
    name = "archive-and-recovery-v1"
    if _migration_applied(db, name):
        return
    before, before_hash = _counts(db), _database_hash(db)
    _add_column(db, "trials", "lifecycle_state", "TEXT NOT NULL DEFAULT 'ACTIVE'")
    _add_column(db, "trials", "archived_at", "TEXT")
    _add_column(db, "trials", "archived_by", "TEXT")
    _add_column(db, "trials", "archive_reason", "TEXT")
    _add_column(db, "trials", "source_state", "TEXT NOT NULL DEFAULT 'PRESENT'")
    _add_column(db, "trials", "recovery_state", "TEXT")
    _add_column(db, "trials", "recovery_evidence_ref", "TEXT")
    _add_column(db, "trials", "recovered_at", "TEXT")
    db.execute("CREATE INDEX IF NOT EXISTS trials_lifecycle_idx ON trials(lifecycle_state, project_id, updated_at)")
    db.execute("""CREATE TABLE IF NOT EXISTS recovery_attestations (
        attestation_id TEXT PRIMARY KEY, clarified_at TEXT NOT NULL,
        statement TEXT NOT NULL, authorization TEXT NOT NULL,
        prose_recovery_required INTEGER NOT NULL, restoration_mechanism TEXT NOT NULL
    )""")
    db.execute(
        "INSERT OR IGNORE INTO recovery_attestations VALUES(?,?,?,?,?,?)",
        (
            "phase-a-live-state-reconciliation-20260803",
            "2026-08-03",
            "Removed material was disposable test data; preserve only surviving provenance.",
            "Operator authorized deletion and accepted the current live database as baseline.",
            0,
            "RESTORATION_PATH_UNKNOWN",
        ),
    )
    # Build only provenance shells for the two specifically authorized test
    # deletions. No source/proposal body is reconstructed.
    for attempt_id in ("generation-a19ffb25a535b770", "generation-379edf2edfd99f24"):
        attempt = db.execute("SELECT * FROM generation_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        if not attempt:
            continue
        if db.execute("SELECT 1 FROM trials WHERE trial_id=?", (attempt["trial_id"],)).fetchone():
            continue
        project = db.execute("SELECT project_id FROM projects WHERE status='ACTIVE' ORDER BY project_id LIMIT 1").fetchone()
        if not project:
            raise RuntimeError("cannot create provenance shell without an active project")
        created = attempt["started_at"] or _now()
        db.execute(
            """INSERT INTO trials(trial_id,created_at,updated_at,source_text,source_sha256,model_identifier,model_digest,
               generation_parameters,integrity_findings,raw_output,normalized_output,review_status,reviewer_notes,
               revision_lineage,project_id,lifecycle_state,archived_at,archived_by,archive_reason,source_state,
               recovery_state,recovery_evidence_ref,recovered_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                attempt["trial_id"], created, created, "", attempt["source_sha256"], attempt["model_identifier"], attempt["model_digest"],
                attempt["generation_settings"] or "{}", "[]", "", "", "REVIEW_REQUIRED", "", json.dumps([attempt_id]), project[0],
                "ARCHIVED", created, "operator", "OPERATOR_AUTHORIZED_TEST_CLEANUP", "OPERATOR_DELETED_TEST_CONTENT",
                "PROVENANCE_ONLY", f"attempt:{attempt_id};attestation:phase-a-live-state-reconciliation-20260803", _now(),
            ),
        )
        snapshot = json.dumps({"trial_id": attempt["trial_id"], "source_state": "OPERATOR_DELETED_TEST_CONTENT", "source_sha256": attempt["source_sha256"], "recovery_state": "PROVENANCE_ONLY", "recovery_evidence_ref": f"attempt:{attempt_id}"}, sort_keys=True)
        db.execute("INSERT INTO trial_versions(trial_id,recorded_at,action,snapshot) VALUES(?,?,?,?)", (attempt["trial_id"], created, "RECOVERED_PROVENANCE_ONLY", snapshot))
    _ledger(db, name, commit, before, before_hash)


def _foreign_keys_and_routing(db: sqlite3.Connection, commit: str) -> None:
    for name in ("foreign-keys-per-connection-v1", "canonical-trial-routing-v1"):
        if not _migration_applied(db, name):
            before, before_hash = _counts(db), _database_hash(db)
            _ledger(db, name, commit, before, before_hash)


def _attempt_events(db: sqlite3.Connection, commit: str) -> None:
    name = "generation-attempt-events-v1"
    if _migration_applied(db, name):
        return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("""CREATE TABLE IF NOT EXISTS generation_attempt_events (
        event_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES generation_attempts(attempt_id),
        sequence_number INTEGER NOT NULL, from_status TEXT, to_status TEXT NOT NULL,
        error_class TEXT, created_at TEXT NOT NULL, prior_event_hash TEXT, event_hash TEXT NOT NULL,
        UNIQUE(attempt_id, sequence_number), UNIQUE(attempt_id, event_hash)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS generation_attempt_events_attempt_idx ON generation_attempt_events(attempt_id, sequence_number)")
    for row in db.execute("SELECT * FROM generation_attempts ORDER BY rowid"):
        to_status = row["status"]
        if to_status == "FAILED" and row["error_class"] == "REQUEST_TIMEOUT":
            to_status = "REQUEST_TIMEOUT"
        event_id = f"attempt-event-legacy-{row['attempt_id']}"
        payload = {"event_id": event_id, "attempt_id": row["attempt_id"], "sequence_number": 1, "from_status": None, "to_status": to_status, "error_class": row["error_class"] or "LEGACY_STATE_IMPORTED", "created_at": row["completed_at"] or row["started_at"] or _now(), "prior_event_hash": None}
        db.execute("INSERT OR IGNORE INTO generation_attempt_events VALUES(?,?,?,?,?,?,?,?,?)", (event_id, row["attempt_id"], 1, None, to_status, payload["error_class"], payload["created_at"], None, hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()))
    _ledger(db, name, commit, before, before_hash)


def _immutability(db: sqlite3.Connection, commit: str) -> None:
    name = "terminal-attempt-immutability-v1"
    if _migration_applied(db, name):
        return
    before, before_hash = _counts(db), _database_hash(db)
    db.executescript("""
    CREATE TRIGGER IF NOT EXISTS generation_attempts_no_delete
    BEFORE DELETE ON generation_attempts BEGIN SELECT RAISE(ABORT, 'generation attempts are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS generation_attempts_safe_update
    BEFORE UPDATE ON generation_attempts
    WHEN OLD.status NOT IN ('RUNNING','QUEUED')
      OR NEW.status NOT IN ('COMPLETED','FAILED','STALE_SOURCE','INTERRUPTED','REQUEST_TIMEOUT')
      OR OLD.attempt_id<>NEW.attempt_id OR OLD.trial_id<>NEW.trial_id
      OR OLD.source_version_id<>NEW.source_version_id OR OLD.source_text<>NEW.source_text
      OR OLD.source_sha256<>NEW.source_sha256 OR OLD.prompt_version<>NEW.prompt_version
      OR OLD.prompt_text<>NEW.prompt_text OR OLD.prompt_sha256<>NEW.prompt_sha256
      OR OLD.request_json<>NEW.request_json OR OLD.model_identifier<>NEW.model_identifier
      OR OLD.model_digest<>NEW.model_digest OR OLD.generation_settings<>NEW.generation_settings
      OR OLD.started_at<>NEW.started_at OR OLD.application_version<>NEW.application_version
    BEGIN SELECT RAISE(ABORT, 'generation attempt provenance is immutable'); END;
    CREATE TRIGGER IF NOT EXISTS generation_attempt_events_no_update
    BEFORE UPDATE ON generation_attempt_events BEGIN SELECT RAISE(ABORT, 'attempt events are append-only'); END;
    CREATE TRIGGER IF NOT EXISTS generation_attempt_events_no_delete
    BEFORE DELETE ON generation_attempt_events BEGIN SELECT RAISE(ABORT, 'attempt events are append-only'); END;
    """)
    _ledger(db, name, commit, before, before_hash)


def _review_append_only(db: sqlite3.Connection, commit: str) -> None:
    name = "review-events-append-only-v1"
    if _migration_applied(db, name):
        return
    before, before_hash = _counts(db), _database_hash(db)
    db.executescript("""
    CREATE TRIGGER IF NOT EXISTS review_events_no_update
    BEFORE UPDATE ON review_events BEGIN SELECT RAISE(ABORT, 'review events are append-only'); END;
    CREATE TRIGGER IF NOT EXISTS review_events_no_delete
    BEFORE DELETE ON review_events BEGIN SELECT RAISE(ABORT, 'review events are append-only'); END;
    """)
    _ledger(db, name, commit, before, before_hash)


def _review_chain(db: sqlite3.Connection, commit: str) -> None:
    name = "review-event-chain-v1"
    if _migration_applied(db, name):
        return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("""CREATE TABLE IF NOT EXISTS review_event_chain (
        event_id TEXT PRIMARY KEY REFERENCES review_events(event_id), stream_id TEXT NOT NULL,
        sequence_number INTEGER NOT NULL, prior_content_hash TEXT, event_content_hash TEXT NOT NULL,
        authoritative INTEGER NOT NULL DEFAULT 1, superseded_event_id TEXT REFERENCES review_events(event_id),
        UNIQUE(stream_id, sequence_number)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS review_event_chain_stream_idx ON review_event_chain(stream_id, sequence_number)")
    _rebuild_review_chain(db)
    _ledger(db, name, commit, before, before_hash)


def _rebuild_review_chain(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM review_event_chain")
    streams: dict[str, list[sqlite3.Row]] = {}
    for row in db.execute("SELECT * FROM review_events ORDER BY trial_id,created_at,event_id"):
        streams.setdefault(f"trial:{row['trial_id']}", []).append(row)
    for stream_id, rows in streams.items():
        prior = None
        for sequence, row in enumerate(rows, 1):
            db.execute("INSERT INTO review_event_chain(event_id,stream_id,sequence_number,prior_content_hash,event_content_hash,authoritative,superseded_event_id) VALUES(?,?,?,?,?,?,NULL)", (row["event_id"], stream_id, sequence, prior, row["content_hash"], 1))
            prior = row["content_hash"]


def _supersession(db: sqlite3.Connection, commit: str) -> None:
    name = "legacy-review-supersession-v1"
    if _migration_applied(db, name):
        return
    before, before_hash = _counts(db), _database_hash(db)
    duplicates = db.execute("""SELECT event_type,decision,created_at,trial_id,count(*) n
        FROM review_events WHERE event_type='DECISION' GROUP BY trial_id,event_type,decision,created_at HAVING count(*)>1""").fetchall()
    for dup in duplicates:
        rows = db.execute("SELECT * FROM review_events WHERE trial_id=? AND event_type=? AND decision=? AND created_at=? ORDER BY event_id", (dup["trial_id"], dup["event_type"], dup["decision"], dup["created_at"])).fetchall()
        authoritative = next((r for r in rows if not r["event_id"].startswith("review-legacy-")), rows[-1])
        for row in rows:
            if row["event_id"] == authoritative["event_id"]:
                continue
            corrective_id = f"review-superseded-{row['event_id']}"
            payload = {"event_id": corrective_id, "trial_id": row["trial_id"], "event_type": "SUPERSEDED_BACKFILL", "decision": None, "note_text": "", "private_steering": False, "related_passage": "", "reviewer_identity": "system", "created_at": _now(), "prior_event_id": None}
            db.execute("INSERT OR IGNORE INTO review_events(event_id,trial_id,generation_attempt_id,event_type,decision,note_text,private_steering,related_passage,reviewer_identity,created_at,prior_event_id,content_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (corrective_id, row["trial_id"], None, "SUPERSEDED_BACKFILL", None, "", 0, "", "system", payload["created_at"], None, hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()))
    _rebuild_review_chain(db)
    for dup in duplicates:
        rows = db.execute("SELECT * FROM review_events WHERE trial_id=? AND event_type='DECISION' AND decision=? AND created_at=? ORDER BY event_id", (dup["trial_id"], dup["decision"], dup["created_at"])).fetchall()
        authoritative = next((r for r in rows if not r["event_id"].startswith("review-legacy-")), rows[-1])
        for row in rows:
            if row["event_id"] != authoritative["event_id"]:
                db.execute("UPDATE review_event_chain SET authoritative=0,superseded_event_id=? WHERE event_id=?", (f"review-superseded-{row['event_id']}", row["event_id"]))
    db.executescript("""
    CREATE TRIGGER IF NOT EXISTS review_event_chain_no_update
    BEFORE UPDATE ON review_event_chain BEGIN SELECT RAISE(ABORT, 'review event witnesses are append-only'); END;
    CREATE TRIGGER IF NOT EXISTS review_event_chain_no_delete
    BEFORE DELETE ON review_event_chain BEGIN SELECT RAISE(ABORT, 'review event witnesses are append-only'); END;
    """)
    _ledger(db, name, commit, before, before_hash)


def apply_migrations(db: sqlite3.Connection, application_commit: str) -> None:
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        migration_name TEXT PRIMARY KEY, applied_at TEXT NOT NULL, application_commit TEXT NOT NULL,
        rows_before TEXT NOT NULL, rows_after TEXT NOT NULL, database_sha256_before TEXT NOT NULL,
        validation_result TEXT NOT NULL
    )""")
    _archive_and_recovery(db, application_commit)
    _foreign_keys_and_routing(db, application_commit)
    _attempt_events(db, application_commit)
    _immutability(db, application_commit)
    _review_append_only(db, application_commit)
    _review_chain(db, application_commit)
    _supersession(db, application_commit)
