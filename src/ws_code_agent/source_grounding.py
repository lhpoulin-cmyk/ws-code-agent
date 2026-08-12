"""Evaluator-owned source grounding for V3 existing-file replacements."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .readonly_executor import ReadResult, RepositorySnapshot


POLICY_ID = "SOURCE_GROUNDED_STRUCTURED_EDIT_V1"
SOURCE_GROUNDED = "SOURCE_GROUNDED"
SOURCE_READ_REQUIRED = "SOURCE_READ_REQUIRED"
SOURCE_GROUNDING_INVALIDATED = "SOURCE_GROUNDING_INVALIDATED"
SOURCE_GROUNDING_NONCOMPLIANCE = "SOURCE_GROUNDING_NONCOMPLIANCE"
EVIDENCE_VERSION = "source-grounding-read/v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def record_successful_read(
    result: ReadResult,
    snapshot: RepositorySnapshot,
    *,
    turn: int,
) -> dict[str, Any]:
    """Bind one real successful READ_FILE fact to path, session snapshot, and turn."""

    fact = result.fact
    observed = fact.observed_result
    if not (
        fact.origin == "executor"
        and fact.component == "ws-code-agent-readonly-executor/v1"
        and fact.operation == "READ_FILE"
        and fact.success is True
        and fact.snapshot_identity == snapshot.snapshot_identity
        and observed.get("relative_path") == result.relative_path
        and observed.get("content_sha256") == hashlib.sha256(result.content).hexdigest()
        and isinstance(turn, int)
        and turn > 0
    ):
        raise ValueError("successful executor READ_FILE evidence is required")
    return {
        "version": EVIDENCE_VERSION,
        "policy_id": POLICY_ID,
        "status": SOURCE_GROUNDED,
        "path": result.relative_path,
        "path_sha256": hashlib.sha256(result.relative_path.encode("utf-8")).hexdigest(),
        "file_content_sha256": hashlib.sha256(result.content).hexdigest(),
        "source_snapshot_identity": snapshot.snapshot_identity,
        "turn": turn,
        "executor_fact_identity": _canonical_sha256(asdict(fact)),
    }


def valid_read_evidence(
    evidence: Mapping[str, Any],
    *,
    path: str,
    source_snapshot_identity: str,
    before_turn: int,
) -> bool:
    """Accept only complete, prior-turn evidence for the exact path and snapshot."""

    required = {
        "version", "policy_id", "status", "path", "path_sha256",
        "file_content_sha256", "source_snapshot_identity", "turn",
        "executor_fact_identity",
    }
    if set(evidence) != required:
        return False
    turn = evidence.get("turn")
    return bool(
        evidence.get("version") == EVIDENCE_VERSION
        and evidence.get("policy_id") == POLICY_ID
        and evidence.get("status") == SOURCE_GROUNDED
        and evidence.get("path") == path
        and evidence.get("path_sha256") == hashlib.sha256(path.encode("utf-8")).hexdigest()
        and evidence.get("source_snapshot_identity") == source_snapshot_identity
        and isinstance(turn, int)
        and 0 < turn < before_turn
        and isinstance(evidence.get("file_content_sha256"), str)
        and _SHA256.fullmatch(evidence["file_content_sha256"]) is not None
        and isinstance(evidence.get("executor_fact_identity"), str)
        and _SHA256.fullmatch(evidence["executor_fact_identity"]) is not None
    )


def grounded_paths_from_turns(
    turns: Sequence[Mapping[str, Any]],
    *,
    source_snapshot_identity: str,
    before_turn: int,
) -> dict[str, dict[str, Any]]:
    """Derive grounding only from durable evaluator evidence, never conversation text."""

    grounded: dict[str, dict[str, Any]] = {}
    for item in turns:
        evidence = item.get("evaluator_evidence", {}).get("source_grounding_read")
        if not isinstance(evidence, Mapping) or not _read_turn_matches_evidence(item, evidence):
            continue
        path = evidence.get("path")
        if isinstance(path, str) and valid_read_evidence(
            evidence,
            path=path,
            source_snapshot_identity=source_snapshot_identity,
            before_turn=before_turn,
        ):
            grounded[path] = dict(evidence)
    return grounded


def _read_turn_matches_evidence(
    item: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> bool:
    arguments = item.get("parsed_arguments")
    projection = item.get("projection")
    return bool(
        item.get("request_type") == "READ"
        and item.get("validation_outcome") == "VALID"
        and item.get("authority_outcome") == "AUTHORIZED"
        and item.get("executor_operation") == "READ_FILE"
        and isinstance(arguments, Mapping)
        and arguments.get("path") == evidence.get("path")
        and isinstance(projection, Mapping)
        and projection.get("status") == "OK"
        and projection.get("path") == evidence.get("path")
    )


def replay_precondition(
    turns: Sequence[Mapping[str, Any]],
    *,
    source_snapshot_identity: str,
) -> dict[str, Any]:
    """Replay grounding only; it never re-executes a historical structured edit."""

    grounded: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    consecutive_ungrounded_writes = 0
    repeated = False
    for number, item in enumerate(turns, 1):
        evidence = item.get("evaluator_evidence", {}).get("source_grounding_read")
        if isinstance(evidence, Mapping) and _read_turn_matches_evidence(item, evidence):
            path = evidence.get("path")
            if isinstance(path, str) and valid_read_evidence(
                evidence,
                path=path,
                source_snapshot_identity=source_snapshot_identity,
                before_turn=number + 1,
            ):
                grounded[path] = dict(evidence)
                consecutive_ungrounded_writes = 0
                events.append({"turn": number, "path": path, "result": SOURCE_GROUNDED})
                continue
        if item.get("request_type") != "PROPOSE_TEXT_REPLACEMENT":
            consecutive_ungrounded_writes = 0
            continue
        arguments = item.get("parsed_arguments")
        path = arguments.get("path") if isinstance(arguments, Mapping) else None
        if not isinstance(path, str):
            continue
        if path in grounded:
            consecutive_ungrounded_writes = 0
            events.append({"turn": number, "path": path, "result": "PRECONDITION_PASS"})
            continue
        consecutive_ungrounded_writes += 1
        repeated = repeated or consecutive_ungrounded_writes >= 2
        events.append({"turn": number, "path": path, "result": SOURCE_READ_REQUIRED})
    return {
        "policy_id": POLICY_ID,
        "events": events,
        "grounded_paths": sorted(grounded),
        "classification": SOURCE_GROUNDING_NONCOMPLIANCE if repeated else None,
        "disposition": "ESCALATION_REQUIRED" if repeated else "CONTINUE",
    }
