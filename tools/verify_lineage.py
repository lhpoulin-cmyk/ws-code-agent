#!/usr/bin/env python3
"""Read-only structural verifier for generation and review evidence streams."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

STATES = {
    "REQUEST_NOT_STARTED", "QUEUED", "RUNNING", "COMPLETED", "INTERRUPTED",
    "REQUEST_TIMEOUT", "OLLAMA_UNAVAILABLE", "OLLAMA_HTTP_ERROR", "EMPTY_RESPONSE",
    "MALFORMED_JSON", "RESPONSE_SCHEMA_INVALID", "PROPOSAL_FIELD_MISSING",
    "TASK_ADHERENCE_FAILED", "NORMALIZATION_FAILURE", "PERSISTENCE_FAILURE",
    "RENDER_FAILURE", "STALE_SOURCE",
}
TERMINAL_STATES = STATES - {"REQUEST_NOT_STARTED", "QUEUED", "RUNNING"}
LEGACY = {"FAILED:REQUEST_TIMEOUT":"REQUEST_TIMEOUT", "FAILED:OLLAMA_UNAVAILABLE":"OLLAMA_UNAVAILABLE", "FAILED:OLLAMA_HTTP_ERROR":"OLLAMA_HTTP_ERROR", "FAILED:EMPTY_RESPONSE":"EMPTY_RESPONSE", "FAILED:RESPONSE_SCHEMA_INVALID":"RESPONSE_SCHEMA_INVALID", "FAILED:PROPOSAL_FIELD_MISSING":"PROPOSAL_FIELD_MISSING", "FAILED:TASK_ADHERENCE_FAILED":"TASK_ADHERENCE_FAILED", "FAILED:":"INTERRUPTED", "STALE_SOURCE:":"STALE_SOURCE", "INTERRUPTED:":"INTERRUPTED", "REQUEST_TIMEOUT:REQUEST_TIMEOUT":"REQUEST_TIMEOUT", "COMPLETED:":"COMPLETED", "RUNNING:":"RUNNING", "QUEUED:":"QUEUED"}

def canonical_state(status, error_class="", explicit=""):
    if explicit in STATES: return explicit
    if status in STATES: return status
    return LEGACY.get(f"{status}:{error_class}", LEGACY.get(f"{status}:", "INTERRUPTED"))


TERMINAL = TERMINAL_STATES
ALLOWED = {
    (None, "REQUEST_NOT_STARTED"),
    ("REQUEST_NOT_STARTED", "QUEUED"),
    (None, "RUNNING"),
    (None, "COMPLETED"),
    (None, "FAILED"),
    (None, "STALE_SOURCE"),
    (None, "INTERRUPTED"),
    (None, "REQUEST_TIMEOUT"),
    ("QUEUED", "RUNNING"),
    ("RUNNING", "COMPLETED"),
    ("RUNNING", "FAILED"),
    ("RUNNING", "STALE_SOURCE"),
    ("RUNNING", "INTERRUPTED"),
    ("RUNNING", "REQUEST_TIMEOUT"),
}
for _source in STATES:
    for _target in STATES:
        if _source == "QUEUED" and _target in {"RUNNING", "INTERRUPTED"}:
            ALLOWED.add((_source, _target))
        if _source == "RUNNING" and _target in TERMINAL_STATES:
            ALLOWED.add((_source, _target))


def digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def fail(message: str) -> int:
    print(f"FAIL {message}")
    return 1


def verify(db: sqlite3.Connection) -> int:
    db.execute("PRAGMA foreign_keys=ON")
    if db.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        return fail("foreign_keys=0")
    fk = db.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        return fail(f"foreign_key_check rows={len(fk)}")

    attempts = {row["attempt_id"]: row for row in db.execute("SELECT * FROM generation_attempts")}
    events_by_attempt: dict[str, list[sqlite3.Row]] = {}
    for row in db.execute("SELECT * FROM generation_attempt_events ORDER BY attempt_id,sequence_number"):
        events_by_attempt.setdefault(row["attempt_id"], []).append(row)
    if set(events_by_attempt) != set(attempts):
        return fail("generation attempt/event coverage mismatch")
    for attempt_id, rows in events_by_attempt.items():
        previous_hash = None
        previous_status = None
        for expected, row in enumerate(rows, 1):
            if row["sequence_number"] != expected:
                return fail(f"attempt={attempt_id} sequence={row['sequence_number']}")
            if row["prior_event_hash"] != previous_hash:
                return fail(f"attempt={attempt_id} prior_hash")
            event_status = canonical_state(row["to_status"], row["error_class"])
            previous_canonical = canonical_state(previous_status, rows[-1]["error_class"] if rows else "") if previous_status else None
            if (previous_canonical, event_status) not in ALLOWED:
                return fail(f"attempt={attempt_id} transition={previous_canonical}->{event_status}")
            payload = {key: row[key] for key in ("event_id", "attempt_id", "sequence_number", "from_status", "to_status", "error_class", "created_at", "prior_event_hash")}
            if row["event_hash"] != digest(payload):
                return fail(f"attempt={attempt_id} event_hash")
            previous_hash = row["event_hash"]
            previous_status = row["to_status"]
        status = canonical_state(attempts[attempt_id]["status"], attempts[attempt_id]["error_class"], attempts[attempt_id].get("canonical_failure_class", "") if hasattr(attempts[attempt_id], "get") else "")
        last_event = canonical_state(previous_status, rows[-1]["error_class"] if rows else "")
        if status != last_event and not (status == "RUNNING" and last_event == "RUNNING"):
            return fail(f"attempt={attempt_id} terminal_status={status}")

    streams: dict[str, list[sqlite3.Row]] = {}
    for row in db.execute("SELECT * FROM review_event_chain ORDER BY stream_id,sequence_number"):
        streams.setdefault(row["stream_id"], []).append(row)
    review_ids = {row["event_id"] for row in db.execute("SELECT event_id FROM review_events")}
    if {row["event_id"] for rows in streams.values() for row in rows} != review_ids:
        return fail("review event/witness coverage mismatch")
    for stream_id, rows in streams.items():
        previous_hash = None
        authoritative_sequences = set()
        for expected, witness in enumerate(rows, 1):
            if witness["sequence_number"] != expected:
                return fail(f"stream={stream_id} sequence={witness['sequence_number']}")
            if witness["prior_content_hash"] != previous_hash:
                return fail(f"stream={stream_id} prior_hash")
            event = db.execute("SELECT * FROM review_events WHERE event_id=?", (witness["event_id"],)).fetchone()
            if not event:
                return fail(f"stream={stream_id} missing_event={witness['event_id']}")
            if event["content_hash"] != witness["event_content_hash"]:
                return fail(f"stream={stream_id} content_hash event={witness['event_id']}")
            if event["stream_id"] and event["stream_id"] != stream_id:
                return fail(f"stream={stream_id} event_stream={event['event_id']}")
            if event["sequence_number"] is not None and event["sequence_number"] != witness["sequence_number"]:
                return fail(f"stream={stream_id} event_sequence={event['event_id']}")
            if event["event_content_hash"] and event["event_content_hash"] != witness["event_content_hash"]:
                return fail(f"stream={stream_id} event_content_hash={event['event_id']}")
            if stream_id.startswith("editorial:"):
                parts = stream_id.split(":", 2)
                if len(parts) != 3 or event["trial_id"] != parts[1] or event["generation_attempt_id"] != parts[2]:
                    return fail(f"stream={stream_id} target_binding={event['event_id']}")
                attempt = db.execute("SELECT status,source_version_id,source_sha256,proposal_sha256 FROM generation_attempts WHERE attempt_id=?", (event["generation_attempt_id"],)).fetchone()
                if not attempt or attempt["status"] != "COMPLETED":
                    return fail(f"stream={stream_id} ineligible_attempt")
                if event["source_version_id"] != attempt["source_version_id"] or event["source_sha256"] != attempt["source_sha256"] or event["proposal_sha256"] != attempt["proposal_sha256"]:
                    return fail(f"stream={stream_id} evidence_binding={event['event_id']}")
            if witness["authoritative"]:
                if witness["sequence_number"] in authoritative_sequences:
                    return fail(f"stream={stream_id} duplicate_authoritative_sequence")
                authoritative_sequences.add(witness["sequence_number"])
            elif not witness["superseded_event_id"]:
                return fail(f"stream={stream_id} nonauthoritative_without_link={witness['event_id']}")
            if witness["superseded_event_id"]:
                target = db.execute("SELECT 1 FROM review_events WHERE event_id=?", (witness["superseded_event_id"],)).fetchone()
                if not target:
                    return fail(f"stream={stream_id} missing_superseded_event")
            previous_hash = witness["event_content_hash"]
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='accepted_baselines'").fetchone():
        baselines = db.execute("SELECT * FROM accepted_baselines ORDER BY trial_id,created_at,baseline_id").fetchall()
        baseline_ids = {row["baseline_id"] for row in baselines}
        accepts = db.execute("SELECT * FROM review_events WHERE event_type='BASELINE_ACCEPT'").fetchall()
        if len(accepts) != len(baselines): return fail("baseline/event coverage mismatch")
        for baseline in baselines:
            linked = [event for event in accepts if event["baseline_id"] == baseline["baseline_id"]]
            if len(linked) != 1 or linked[0]["decision"] != "BASELINE_ACCEPTED": return fail(f"baseline={baseline['baseline_id']} acceptance_event")
            if hashlib.sha256(baseline["accepted_proposal"].encode()).hexdigest() != baseline["proposal_sha256"]: return fail(f"baseline={baseline['baseline_id']} proposal_hash")
            if baseline["supersedes_baseline_id"] and baseline["supersedes_baseline_id"] not in baseline_ids: return fail(f"baseline={baseline['baseline_id']} supersedes_missing")
            if baseline["supersedes_baseline_id"] and db.execute("SELECT trial_id FROM accepted_baselines WHERE baseline_id=?", (baseline["supersedes_baseline_id"],)).fetchone()[0] != baseline["trial_id"]: return fail(f"baseline={baseline['baseline_id']} cross_trial_supersession")
            for field in ("review_target_event_id", "integrity_review_event_id", "revision_review_event_id", "tone_review_event_id"):
                event = db.execute("SELECT * FROM review_events WHERE event_id=?", (baseline[field],)).fetchone()
                if not event or event["trial_id"] != baseline["trial_id"] or event["generation_attempt_id"] != baseline["generation_attempt_id"] or event["stream_id"] != linked[0]["stream_id"]: return fail(f"baseline={baseline['baseline_id']} gate_binding={field}")
            if linked[0]["proposal_sha256"] != baseline["proposal_sha256"] or linked[0]["source_sha256"] != baseline["source_sha256"]: return fail(f"baseline={baseline['baseline_id']} evidence_hash")
        for baseline in baselines:
            seen = set(); cursor = baseline["baseline_id"]
            while cursor:
                if cursor in seen: return fail(f"baseline={baseline['baseline_id']} cycle")
                seen.add(cursor); row = next((r for r in baselines if r["baseline_id"] == cursor), None); cursor = row["supersedes_baseline_id"] if row else None
    print(f"OK attempts={len(attempts)} attempt_events={sum(map(len, events_by_attempt.values()))} review_events={len(review_ids)} streams={len(streams)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=os.environ.get("DOCWRITER_DATABASE", "/srv/ws-doc-writer/app/state/docwriter.sqlite3"))
    args = parser.parse_args(argv)
    path = Path(args.database).resolve()
    if not path.is_file():
        return fail("database_not_found")
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        return verify(db)
    except sqlite3.Error as exc:
        return fail(f"sqlite={type(exc).__name__}")
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
