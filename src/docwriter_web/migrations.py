"""Named, additive, idempotent Phase A migrations for Doc Writer."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Callable

from .failure_taxonomy import CLASSIFIER_VERSION, canonical_state


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
    "prompt-provenance-v2-v1",
    "generation-failure-taxonomy-v1",
    "generation-failure-taxonomy-v2",
    "editorial-review-target-v1",
    "editorial-review-stages-v1",
    "editorial-review-details-v1",
    "editorial-review-streams-v1",
    "accepted-baselines-v1",
    "baseline-review-events-v1",
    "baseline-immutability-v1",
    "baseline-supersession-v1",
    "audience-profiles-v1",
    "audience-adaptations-v1",
    "audience-generation-attempts-v1",
    "audience-review-events-v1",
    "accepted-audience-versions-v1",
    "audience-version-immutability-v1",
    "audience-request-conflicts-v1",
    "audience-attempt-before-request-v1",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _database_hash(db: sqlite3.Connection) -> str:
    # Hash the logical database rather than a live file path. This is stable
    # for tests and does not require reading private row bodies into evidence.
    rows = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
    return hashlib.sha256("\n".join(json.dumps(tuple(row), ensure_ascii=False) for row in rows).encode()).hexdigest()


def _counts(db: sqlite3.Connection) -> dict[str, int]:
    tables = ["projects", "trials", "trial_versions", "generation_attempts", "review_events", "project_migration_events", "accepted_baselines"]
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


def _prompt_provenance_v2(db: sqlite3.Connection, commit: str) -> None:
    name = "prompt-provenance-v2-v1"
    if _migration_applied(db, name):
        return
    before, before_hash = _counts(db), _database_hash(db)
    columns = {
        "transport_type": "TEXT NOT NULL DEFAULT ''",
        "transport_endpoint": "TEXT NOT NULL DEFAULT ''",
        "adapter_id": "TEXT NOT NULL DEFAULT ''",
        "adapter_version": "TEXT NOT NULL DEFAULT ''",
        "request_serializer_version": "TEXT NOT NULL DEFAULT ''",
        "message_roles": "TEXT NOT NULL DEFAULT ''",
        "canonical_contract_hashes": "TEXT NOT NULL DEFAULT '{}'",
        "composed_contract_hash": "TEXT NOT NULL DEFAULT ''",
        "schema_version": "TEXT NOT NULL DEFAULT ''",
        "schema_hash": "TEXT NOT NULL DEFAULT ''",
        "response_schema": "TEXT NOT NULL DEFAULT ''",
        "task_adherence_result": "TEXT NOT NULL DEFAULT 'not_run'",
    }
    for column, definition in columns.items():
        _add_column(db, "generation_attempts", column, definition)
    db.executescript("""
    CREATE TRIGGER IF NOT EXISTS generation_attempts_v2_provenance_immutable
    BEFORE UPDATE ON generation_attempts
    WHEN OLD.transport_type<>NEW.transport_type
      OR OLD.transport_endpoint<>NEW.transport_endpoint
      OR OLD.adapter_id<>NEW.adapter_id
      OR OLD.adapter_version<>NEW.adapter_version
      OR OLD.request_serializer_version<>NEW.request_serializer_version
      OR OLD.message_roles<>NEW.message_roles
      OR OLD.canonical_contract_hashes<>NEW.canonical_contract_hashes
      OR OLD.composed_contract_hash<>NEW.composed_contract_hash
      OR OLD.schema_version<>NEW.schema_version
      OR OLD.schema_hash<>NEW.schema_hash
      OR OLD.response_schema<>NEW.response_schema
      OR (OLD.task_adherence_result<>NEW.task_adherence_result
          AND NOT (OLD.status='RUNNING' AND OLD.task_adherence_result='not_run'
                   AND NEW.task_adherence_result IN ('passed','failed')))
    BEGIN SELECT RAISE(ABORT, 'v2 request provenance is immutable'); END;
    """)
    _ledger(db, name, commit, before, before_hash)


def _failure_taxonomy(db: sqlite3.Connection, commit: str) -> None:
    name = "generation-failure-taxonomy-v1"
    if _migration_applied(db, name):
        return
    before, before_hash = _counts(db), _database_hash(db)
    for column, definition in {
        "canonical_failure_class": "TEXT NOT NULL DEFAULT ''",
        "classifier_version": "TEXT NOT NULL DEFAULT ''",
        "safe_error_detail": "TEXT NOT NULL DEFAULT ''",
        "presentation_result": "TEXT NOT NULL DEFAULT 'not_applicable'",
        "recovery_spool_ref": "TEXT NOT NULL DEFAULT ''",
        "last_state_at": "TEXT NOT NULL DEFAULT ''",
        "worker_pid": "INTEGER",
        "worker_start_identity": "TEXT NOT NULL DEFAULT ''",
    }.items():
        _add_column(db, "generation_attempts", column, definition)
    # The Phase A trigger does not know the expanded vocabulary. Remove it
    # before adding the additive interpretation columns; the replacement below
    # is installed in the same transaction.
    db.execute("DROP TRIGGER IF EXISTS generation_attempts_safe_update")
    rows = db.execute("SELECT attempt_id,status,error_class,completed_at,started_at FROM generation_attempts").fetchall()
    for row in rows:
        state = canonical_state(row["status"], row["error_class"])
        db.execute(
            "UPDATE generation_attempts SET canonical_failure_class=?,classifier_version=?,safe_error_detail=?,last_state_at=? WHERE attempt_id=?",
            (state, CLASSIFIER_VERSION, "", row["completed_at"] or row["started_at"] or _now(), row["attempt_id"]),
        )
    # Replace the Phase A trigger with the same provenance protections and the
    # complete additive terminal-state vocabulary. Existing rows and events are
    # not rewritten; legacy FAILED events remain interpretable via the map.
    db.executescript("""
    CREATE TRIGGER generation_attempts_safe_update
    BEFORE UPDATE ON generation_attempts
    WHEN OLD.status NOT IN ('RUNNING','QUEUED')
      OR NEW.status NOT IN ('COMPLETED','INTERRUPTED','REQUEST_TIMEOUT','OLLAMA_UNAVAILABLE','OLLAMA_HTTP_ERROR','EMPTY_RESPONSE','MALFORMED_JSON','RESPONSE_SCHEMA_INVALID','PROPOSAL_FIELD_MISSING','TASK_ADHERENCE_FAILED','NORMALIZATION_FAILURE','PERSISTENCE_FAILURE','RENDER_FAILURE','STALE_SOURCE')
      OR OLD.attempt_id<>NEW.attempt_id OR OLD.trial_id<>NEW.trial_id
      OR OLD.source_version_id<>NEW.source_version_id OR OLD.source_text<>NEW.source_text
      OR OLD.source_sha256<>NEW.source_sha256 OR OLD.prompt_version<>NEW.prompt_version
      OR OLD.prompt_text<>NEW.prompt_text OR OLD.prompt_sha256<>NEW.prompt_sha256
      OR OLD.request_json<>NEW.request_json OR OLD.model_identifier<>NEW.model_identifier
      OR OLD.model_digest<>NEW.model_digest OR OLD.generation_settings<>NEW.generation_settings
      OR OLD.started_at<>NEW.started_at OR OLD.application_version<>NEW.application_version
      OR OLD.transport_type<>NEW.transport_type OR OLD.transport_endpoint<>NEW.transport_endpoint
      OR OLD.adapter_id<>NEW.adapter_id OR OLD.adapter_version<>NEW.adapter_version
      OR OLD.request_serializer_version<>NEW.request_serializer_version OR OLD.message_roles<>NEW.message_roles
      OR OLD.canonical_contract_hashes<>NEW.canonical_contract_hashes OR OLD.composed_contract_hash<>NEW.composed_contract_hash
      OR OLD.schema_version<>NEW.schema_version OR OLD.schema_hash<>NEW.schema_hash
      OR OLD.response_schema<>NEW.response_schema OR OLD.task_adherence_result<>NEW.task_adherence_result
      OR (OLD.classifier_version<>NEW.classifier_version AND OLD.classifier_version<>'')
      OR OLD.recovery_spool_ref<>NEW.recovery_spool_ref
      OR COALESCE(OLD.worker_pid,0)<>COALESCE(NEW.worker_pid,0)
      OR OLD.worker_start_identity<>NEW.worker_start_identity
      OR (OLD.status='RUNNING' AND NEW.presentation_result<>OLD.presentation_result AND NEW.presentation_result NOT IN ('not_applicable','failed'))
    BEGIN SELECT RAISE(ABORT, 'generation attempt provenance or lifecycle is immutable'); END;
    """)
    _ledger(db, name, commit, before, before_hash)


def _failure_taxonomy_v2(db: sqlite3.Connection, commit: str) -> None:
    name = "generation-failure-taxonomy-v2"
    if _migration_applied(db, name):
        return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("DROP TRIGGER IF EXISTS generation_attempts_safe_update")
    db.executescript("""
    CREATE TRIGGER generation_attempts_safe_update
    BEFORE UPDATE ON generation_attempts
    WHEN OLD.status NOT IN ('RUNNING','QUEUED')
      OR NEW.status NOT IN ('COMPLETED','INTERRUPTED','REQUEST_TIMEOUT','OLLAMA_UNAVAILABLE','OLLAMA_HTTP_ERROR','EMPTY_RESPONSE','MALFORMED_JSON','RESPONSE_SCHEMA_INVALID','PROPOSAL_FIELD_MISSING','TASK_ADHERENCE_FAILED','NORMALIZATION_FAILURE','PERSISTENCE_FAILURE','RENDER_FAILURE','STALE_SOURCE')
      OR OLD.attempt_id<>NEW.attempt_id OR OLD.trial_id<>NEW.trial_id
      OR OLD.source_version_id<>NEW.source_version_id OR OLD.source_text<>NEW.source_text
      OR OLD.source_sha256<>NEW.source_sha256 OR OLD.prompt_version<>NEW.prompt_version
      OR OLD.prompt_text<>NEW.prompt_text OR OLD.prompt_sha256<>NEW.prompt_sha256
      OR OLD.request_json<>NEW.request_json OR OLD.model_identifier<>NEW.model_identifier
      OR OLD.model_digest<>NEW.model_digest OR OLD.generation_settings<>NEW.generation_settings
      OR OLD.started_at<>NEW.started_at OR OLD.application_version<>NEW.application_version
      OR OLD.transport_type<>NEW.transport_type OR OLD.transport_endpoint<>NEW.transport_endpoint
      OR OLD.adapter_id<>NEW.adapter_id OR OLD.adapter_version<>NEW.adapter_version
      OR OLD.request_serializer_version<>NEW.request_serializer_version OR OLD.message_roles<>NEW.message_roles
      OR OLD.canonical_contract_hashes<>NEW.canonical_contract_hashes OR OLD.composed_contract_hash<>NEW.composed_contract_hash
      OR OLD.schema_version<>NEW.schema_version OR OLD.schema_hash<>NEW.schema_hash
      OR OLD.response_schema<>NEW.response_schema
      OR (OLD.task_adherence_result<>NEW.task_adherence_result
          AND NOT (OLD.status='RUNNING' AND OLD.task_adherence_result='not_run'
                   AND NEW.task_adherence_result IN ('passed','failed')))
      OR (OLD.canonical_failure_class<>NEW.canonical_failure_class AND OLD.status NOT IN ('RUNNING','QUEUED'))
      OR (OLD.classifier_version<>NEW.classifier_version AND OLD.classifier_version<>'')
      OR OLD.recovery_spool_ref<>NEW.recovery_spool_ref
      OR COALESCE(OLD.worker_pid,0)<>COALESCE(NEW.worker_pid,0)
      OR OLD.worker_start_identity<>NEW.worker_start_identity
    BEGIN SELECT RAISE(ABORT, 'generation attempt provenance or lifecycle is immutable'); END;
    """)
    _ledger(db, name, commit, before, before_hash)


def _editorial_review_schema(db: sqlite3.Connection, commit: str) -> None:
    names = ("editorial-review-target-v1", "editorial-review-stages-v1", "editorial-review-details-v1", "editorial-review-streams-v1")
    before, before_hash = _counts(db), _database_hash(db)
    for column, definition in {
        "source_version_id": "INTEGER REFERENCES trial_versions(version_id)",
        "source_sha256": "TEXT",
        "proposal_sha256": "TEXT",
        "stage": "TEXT",
        "preferred_replacement": "TEXT",
        "finding_codes": "TEXT",
        "operator_aside": "TEXT",
        "stream_id": "TEXT",
        "sequence_number": "INTEGER",
        "prior_content_hash": "TEXT",
        "event_content_hash": "TEXT",
    }.items():
        _add_column(db, "review_events", column, definition)
    db.execute("CREATE INDEX IF NOT EXISTS review_events_editorial_stream_idx ON review_events(stream_id, sequence_number)")
    db.execute("CREATE INDEX IF NOT EXISTS review_events_target_idx ON review_events(trial_id, generation_attempt_id, stage, created_at)")
    for name in names:
        if not _migration_applied(db, name):
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
      OR OLD.transport_type<>NEW.transport_type OR OLD.transport_endpoint<>NEW.transport_endpoint
      OR OLD.adapter_id<>NEW.adapter_id OR OLD.adapter_version<>NEW.adapter_version
      OR OLD.request_serializer_version<>NEW.request_serializer_version OR OLD.message_roles<>NEW.message_roles
      OR OLD.canonical_contract_hashes<>NEW.canonical_contract_hashes OR OLD.composed_contract_hash<>NEW.composed_contract_hash
      OR OLD.schema_version<>NEW.schema_version OR OLD.schema_hash<>NEW.schema_hash
      OR OLD.response_schema<>NEW.response_schema OR OLD.task_adherence_result<>NEW.task_adherence_result
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


def _accepted_baselines(db: sqlite3.Connection, commit: str) -> None:
    name = "accepted-baselines-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("""CREATE TABLE IF NOT EXISTS accepted_baselines (
        baseline_id TEXT PRIMARY KEY,
        trial_id TEXT NOT NULL REFERENCES trials(trial_id),
        source_version_id INTEGER NOT NULL REFERENCES trial_versions(version_id),
        generation_attempt_id TEXT NOT NULL REFERENCES generation_attempts(attempt_id),
        review_target_event_id TEXT NOT NULL REFERENCES review_events(event_id),
        integrity_review_event_id TEXT NOT NULL REFERENCES review_events(event_id),
        revision_review_event_id TEXT NOT NULL REFERENCES review_events(event_id),
        tone_review_event_id TEXT NOT NULL REFERENCES review_events(event_id),
        accepted_proposal TEXT NOT NULL,
        proposal_sha256 TEXT NOT NULL, source_sha256 TEXT NOT NULL,
        source_to_proposal_diff_sha256 TEXT NOT NULL,
        prompt_version TEXT NOT NULL, prompt_sha256 TEXT NOT NULL,
        writer_contract_sha256 TEXT NOT NULL, integrity_contract_sha256 TEXT NOT NULL,
        voice_contract_sha256 TEXT NOT NULL, response_schema_sha256 TEXT NOT NULL,
        model_identifier TEXT NOT NULL, model_digest TEXT NOT NULL,
        accepted_by TEXT NOT NULL, accepted_at TEXT NOT NULL,
        acceptance_note TEXT, supersedes_baseline_id TEXT REFERENCES accepted_baselines(baseline_id),
        created_at TEXT NOT NULL, CHECK(baseline_id <> supersedes_baseline_id)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS accepted_baselines_trial_idx ON accepted_baselines(trial_id, created_at)")
    db.execute("CREATE INDEX IF NOT EXISTS accepted_baselines_supersedes_idx ON accepted_baselines(supersedes_baseline_id)")
    _ledger(db, name, commit, before, before_hash)


def _baseline_review_events(db: sqlite3.Connection, commit: str) -> None:
    name = "baseline-review-events-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    _add_column(db, "review_events", "baseline_id", "TEXT REFERENCES accepted_baselines(baseline_id)")
    db.execute("CREATE INDEX IF NOT EXISTS review_events_baseline_idx ON review_events(baseline_id)")
    _ledger(db, name, commit, before, before_hash)


def _baseline_immutability(db: sqlite3.Connection, commit: str) -> None:
    name = "baseline-immutability-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    db.executescript("""
    CREATE TRIGGER IF NOT EXISTS accepted_baselines_no_update BEFORE UPDATE ON accepted_baselines
    BEGIN SELECT RAISE(ABORT, 'accepted baselines are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS accepted_baselines_no_delete BEFORE DELETE ON accepted_baselines
    BEGIN SELECT RAISE(ABORT, 'accepted baselines are immutable'); END;
    """)
    _ledger(db, name, commit, before, before_hash)


def _baseline_supersession(db: sqlite3.Connection, commit: str) -> None:
    name = "baseline-supersession-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS accepted_baselines_one_successor_idx ON accepted_baselines(supersedes_baseline_id) WHERE supersedes_baseline_id IS NOT NULL")
    _ledger(db, name, commit, before, before_hash)

def _audience_profiles(db: sqlite3.Connection, commit: str) -> None:
    name = "audience-profiles-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("CREATE TABLE IF NOT EXISTS audience_profiles (profile_id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, purpose TEXT NOT NULL, contract_version TEXT NOT NULL, contract_sha256 TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, retired_at TEXT)")
    profiles = [("audience-technical-peer", "technical-peer", "Technical peer", "A technically capable reader who needs precise behavior, boundaries, evidence, terminology, and operational consequences without introductory over-explanation.", "prompts/audiences/technical-peer.md"), ("audience-executive", "executive", "Executive or decision-maker", "A decision-maker who needs the outcome, importance, risk, tradeoffs, confidence, unresolved issues, and required decision without unnecessary implementation detail.", "prompts/audiences/executive.md"), ("audience-public", "public", "Public or non-specialist", "A reader without assumed specialist knowledge who needs accurate, understandable explanation without distortion, condescension, or false simplification.", "prompts/audiences/public.md")]
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    for profile_id, slug, title, purpose, rel in profiles:
        raw = (root / rel).read_bytes()
        db.execute("INSERT OR IGNORE INTO audience_profiles VALUES(?,?,?,?,?,?,?,?,?)", (profile_id, slug, title, purpose, "audience-adaptation-v1", hashlib.sha256(raw).hexdigest(), 1, _now(), None))
    _ledger(db, name, commit, before, before_hash)

def _audience_adaptations(db: sqlite3.Connection, commit: str) -> None:
    name = "audience-adaptations-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("""CREATE TABLE IF NOT EXISTS audience_adaptations (
      adaptation_id TEXT PRIMARY KEY, trial_id TEXT NOT NULL REFERENCES trials(trial_id), baseline_id TEXT NOT NULL REFERENCES accepted_baselines(baseline_id), profile_id TEXT NOT NULL REFERENCES audience_profiles(profile_id), baseline_sha256 TEXT NOT NULL, source_version_id INTEGER NOT NULL REFERENCES trial_versions(version_id), source_sha256 TEXT NOT NULL, integrity_review_event_id TEXT NOT NULL REFERENCES review_events(event_id), integrity_contract_sha256 TEXT NOT NULL, audience_contract_version TEXT NOT NULL, audience_contract_sha256 TEXT NOT NULL, profile_contract_sha256 TEXT NOT NULL, created_at TEXT NOT NULL, archived_at TEXT, UNIQUE(baseline_id, profile_id)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS audience_adaptations_trial_idx ON audience_adaptations(trial_id,profile_id)")
    _ledger(db, name, commit, before, before_hash)

def _audience_generation_attempts(db: sqlite3.Connection, commit: str) -> None:
    name = "audience-generation-attempts-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    for col, definition in {"kind":"TEXT NOT NULL DEFAULT 'CONVERSATIONAL'", "adaptation_id":"TEXT REFERENCES audience_adaptations(adaptation_id)", "baseline_id":"TEXT REFERENCES accepted_baselines(baseline_id)", "profile_id":"TEXT REFERENCES audience_profiles(profile_id)", "output_sha256":"TEXT"}.items(): _add_column(db, "generation_attempts", col, definition)
    db.execute("CREATE INDEX IF NOT EXISTS generation_attempts_audience_idx ON generation_attempts(adaptation_id,profile_id,started_at)")
    _ledger(db, name, commit, before, before_hash)

def _audience_review_events(db: sqlite3.Connection, commit: str) -> None:
    name = "audience-review-events-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    for col, definition in {"adaptation_id":"TEXT REFERENCES audience_adaptations(adaptation_id)", "baseline_id":"TEXT REFERENCES accepted_baselines(baseline_id)", "profile_id":"TEXT REFERENCES audience_profiles(profile_id)", "output_sha256":"TEXT"}.items(): _add_column(db, "review_events", col, definition)
    db.execute("CREATE INDEX IF NOT EXISTS review_events_audience_idx ON review_events(adaptation_id,profile_id,created_at)")
    _ledger(db, name, commit, before, before_hash)

def _accepted_audience_versions(db: sqlite3.Connection, commit: str) -> None:
    name = "accepted-audience-versions-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("""CREATE TABLE IF NOT EXISTS accepted_audience_versions (
      accepted_audience_version_id TEXT PRIMARY KEY, adaptation_id TEXT NOT NULL REFERENCES audience_adaptations(adaptation_id), trial_id TEXT NOT NULL REFERENCES trials(trial_id), baseline_id TEXT NOT NULL REFERENCES accepted_baselines(baseline_id), profile_id TEXT NOT NULL REFERENCES audience_profiles(profile_id), generation_attempt_id TEXT NOT NULL REFERENCES generation_attempts(attempt_id), review_target_event_id TEXT NOT NULL REFERENCES review_events(event_id), audience_review_event_id TEXT NOT NULL REFERENCES review_events(event_id), accepted_text TEXT NOT NULL, accepted_text_sha256 TEXT NOT NULL, baseline_sha256 TEXT NOT NULL, source_sha256 TEXT NOT NULL, integrity_contract_sha256 TEXT NOT NULL, audience_contract_sha256 TEXT NOT NULL, profile_contract_sha256 TEXT NOT NULL, prompt_version TEXT NOT NULL, prompt_sha256 TEXT NOT NULL, model_identifier TEXT NOT NULL, model_digest TEXT NOT NULL, accepted_by TEXT NOT NULL, accepted_at TEXT NOT NULL, acceptance_note TEXT, supersedes_accepted_version_id TEXT REFERENCES accepted_audience_versions(accepted_audience_version_id), created_at TEXT NOT NULL
    )""")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS accepted_audience_one_successor_idx ON accepted_audience_versions(supersedes_accepted_version_id) WHERE supersedes_accepted_version_id IS NOT NULL")
    db.execute("CREATE INDEX IF NOT EXISTS accepted_audience_adaptation_idx ON accepted_audience_versions(adaptation_id,created_at)")
    _ledger(db, name, commit, before, before_hash)

def _audience_version_immutability(db: sqlite3.Connection, commit: str) -> None:
    name = "audience-version-immutability-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    db.executescript("CREATE TRIGGER IF NOT EXISTS accepted_audience_versions_no_update BEFORE UPDATE ON accepted_audience_versions BEGIN SELECT RAISE(ABORT,'accepted audience versions are immutable'); END; CREATE TRIGGER IF NOT EXISTS accepted_audience_versions_no_delete BEFORE DELETE ON accepted_audience_versions BEGIN SELECT RAISE(ABORT,'accepted audience versions are immutable'); END;")
    _ledger(db, name, commit, before, before_hash)

def _audience_request_conflicts(db: sqlite3.Connection, commit: str) -> None:
    name = "audience-request-conflicts-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("""CREATE TABLE IF NOT EXISTS audience_request_conflicts (
      conflict_id TEXT PRIMARY KEY, adaptation_id TEXT REFERENCES audience_adaptations(adaptation_id),
      baseline_id TEXT REFERENCES accepted_baselines(baseline_id), profile_id TEXT REFERENCES audience_profiles(profile_id),
      request_timestamp TEXT NOT NULL, route TEXT NOT NULL, issuer TEXT NOT NULL, response_status INTEGER NOT NULL,
      safe_response_detail TEXT NOT NULL, ollama_reached INTEGER NOT NULL, model_execution INTEGER NOT NULL,
      classification TEXT NOT NULL, recovery_disposition TEXT NOT NULL, created_at TEXT NOT NULL
    )""")
    db.execute("""INSERT OR IGNORE INTO audience_request_conflicts
      SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM audience_adaptations WHERE adaptation_id=?)""", (
        "conflict-20260803-technical-peer", "adaptation-79d01e5fba83fa84", "baseline-42aca28fe9c5ed88",
        "audience-technical-peer", "2026-08-03T23:47:00-04:00",
        "/trial/trial-08ef25706ca0155b/audience/technical-peer/generate", "DOC_WRITER_APPLICATION", 409,
        "Application returned 409 after Ollama returned 200; exact response body was not retained (37-byte HTTP body).",
        1, 1, "PRE_PERSISTENCE_FAILURE", "Preserved as sanitized forensic evidence; no attempt row was fabricated.", _now(), "adaptation-79d01e5fba83fa84"))
    _ledger(db, name, commit, before, before_hash)

def _audience_attempt_before_request(db: sqlite3.Connection, commit: str) -> None:
    name = "audience-attempt-before-request-v1"
    if _migration_applied(db, name): return
    before, before_hash = _counts(db), _database_hash(db)
    db.execute("DROP TRIGGER IF EXISTS generation_attempts_safe_update")
    db.executescript("""
    CREATE TRIGGER generation_attempts_safe_update
    BEFORE UPDATE ON generation_attempts
    WHEN OLD.status NOT IN ('RUNNING','QUEUED')
      OR NEW.status NOT IN ('RUNNING','COMPLETED','INTERRUPTED','REQUEST_TIMEOUT','OLLAMA_UNAVAILABLE','OLLAMA_HTTP_ERROR','EMPTY_RESPONSE','MALFORMED_JSON','RESPONSE_SCHEMA_INVALID','PROPOSAL_FIELD_MISSING','TASK_ADHERENCE_FAILED','NORMALIZATION_FAILURE','PERSISTENCE_FAILURE','RENDER_FAILURE','STALE_SOURCE')
      OR OLD.attempt_id<>NEW.attempt_id OR OLD.trial_id<>NEW.trial_id
      OR OLD.source_version_id<>NEW.source_version_id OR OLD.source_text<>NEW.source_text
      OR OLD.source_sha256<>NEW.source_sha256 OR OLD.prompt_version<>NEW.prompt_version
      OR OLD.prompt_text<>NEW.prompt_text OR OLD.prompt_sha256<>NEW.prompt_sha256
      OR OLD.request_json<>NEW.request_json OR OLD.model_identifier<>NEW.model_identifier
      OR OLD.model_digest<>NEW.model_digest OR OLD.generation_settings<>NEW.generation_settings
      OR OLD.started_at<>NEW.started_at OR OLD.application_version<>NEW.application_version
      OR OLD.transport_type<>NEW.transport_type OR OLD.transport_endpoint<>NEW.transport_endpoint
      OR OLD.adapter_id<>NEW.adapter_id OR OLD.adapter_version<>NEW.adapter_version
      OR OLD.request_serializer_version<>NEW.request_serializer_version OR OLD.message_roles<>NEW.message_roles
      OR OLD.canonical_contract_hashes<>NEW.canonical_contract_hashes OR OLD.composed_contract_hash<>NEW.composed_contract_hash
      OR OLD.schema_version<>NEW.schema_version OR OLD.schema_hash<>NEW.schema_hash OR OLD.response_schema<>NEW.response_schema
      OR (OLD.task_adherence_result<>NEW.task_adherence_result AND NOT (NEW.task_adherence_result IN ('passed','failed') AND OLD.status IN ('RUNNING','QUEUED')))
      OR (OLD.classifier_version<>NEW.classifier_version AND OLD.classifier_version<>'')
      OR OLD.recovery_spool_ref<>NEW.recovery_spool_ref OR COALESCE(OLD.worker_pid,0)<>COALESCE(NEW.worker_pid,0)
      OR OLD.worker_start_identity<>NEW.worker_start_identity
    BEGIN SELECT RAISE(ABORT, 'generation attempt provenance or lifecycle is immutable'); END;
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
    _prompt_provenance_v2(db, application_commit)
    _failure_taxonomy(db, application_commit)
    _failure_taxonomy_v2(db, application_commit)
    _editorial_review_schema(db, application_commit)
    _attempt_events(db, application_commit)
    _immutability(db, application_commit)
    _review_append_only(db, application_commit)
    _review_chain(db, application_commit)
    _supersession(db, application_commit)
    _accepted_baselines(db, application_commit)
    _baseline_review_events(db, application_commit)
    _baseline_immutability(db, application_commit)
    _baseline_supersession(db, application_commit)
    _audience_profiles(db, application_commit)
    _audience_adaptations(db, application_commit)
    _audience_generation_attempts(db, application_commit)
    _audience_review_events(db, application_commit)
    _accepted_audience_versions(db, application_commit)
    _audience_version_immutability(db, application_commit)
    _audience_request_conflicts(db, application_commit)
    _audience_attempt_before_request(db, application_commit)
