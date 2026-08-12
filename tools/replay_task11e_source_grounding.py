#!/usr/bin/env python3
"""Replay Task 11E grounding policy over immutable Task 11A/11D evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.readonly_executor import CompareStatus, ReadOnlyExecutor, RepositorySnapshot  # noqa: E402
from ws_code_agent.source_grounding import (  # noqa: E402
    SOURCE_GROUNDED,
    SOURCE_GROUNDING_NONCOMPLIANCE,
    record_successful_read,
    replay_precondition,
)


TASK11A = Path(
    "/home/louis/.local/share/ws-code-agent/work/"
    "work-task11a-qwen25-14b-positive-20260812T142051Z"
)
TASK11D = Path(
    "/home/louis/.local/share/ws-code-agent/work/"
    "work-task11d-qwen25-14b-v3-20260812T154829Z"
)
EXPECTED = {
    "Task11A": (
        "f52783b9c7e1b6cabdc432c68e9384e66da391aa1f201051802127857b9962fb",
        "7b367e7154161e9b727d4727226f9dde4fdb73d3aa3917e53cfc773332be688a",
        "a766d876888b62252091dec4fb0fccf5774aa9e84122b3172b90179352e158a5",
    ),
    "Task11D": (
        "9d719ea17a11813671271e9378b34cfd5caef9815413e7439e1c2dd486cc24d0",
        "69596c9a4b86e9e224c0e5ddcd3b543455058ccb976155a66c934bd322e23fdb",
    ),
}


def load_session(path: Path, label: str) -> tuple[dict, list[dict]]:
    case = json.loads((path / "cases/WORK/case.json").read_text(encoding="utf-8"))
    turns = []
    for number in range(1, int(case["turn_committed"]) + 1):
        directory = path / "cases/WORK/turns" / f"{number:04d}"
        result = json.loads((directory / "harness-result.json").read_text(encoding="utf-8"))
        raw_sha = hashlib.sha256((directory / "raw-response.txt").read_bytes()).hexdigest()
        if raw_sha != result["raw_sha256"] or raw_sha != EXPECTED[label][number - 1]:
            raise RuntimeError(f"{label} turn {number} raw evidence mismatch")
        turns.append(result)
    return case, turns


def snapshot(value: dict) -> RepositorySnapshot:
    value = dict(value)
    value["untracked_inventory"] = tuple(tuple(item) for item in value["untracked_inventory"])
    return RepositorySnapshot(**value)


def main() -> int:
    case_a, turns_a = load_session(TASK11A, "Task11A")
    snap_a = snapshot(case_a["snapshot_x"])
    observer = ReadOnlyExecutor()
    if observer.compare_snapshot(snap_a).status is not CompareStatus.MATCH:
        raise RuntimeError("Task11A Source Snapshot X mismatch")
    first = turns_a[0]
    if first.get("request_type") != "READ" or first.get("parsed_arguments") != {
        "path": "src/message.py"
    }:
        raise RuntimeError("Task11A turn 1 is not the bound exact-path READ")
    read_evidence = record_successful_read(
        observer.read_file(snap_a, "src/message.py"), snap_a, turn=1
    )
    task11a_writes = []
    for number, result in enumerate(turns_a[1:], 2):
        paths = result.get("parsed_arguments", {}).get("proposed_paths", [])
        task11a_writes.append({
            "turn": number,
            "request_type": result.get("request_type"),
            "path": "src/message.py" if paths == ["src/message.py"] else None,
            "precondition": "PASS" if paths == [read_evidence["path"]] else "FAIL",
            "historical_executor_result": result.get("authority_outcome"),
        })

    case_d, turns_d = load_session(TASK11D, "Task11D")
    replay_d = replay_precondition(
        turns_d,
        source_snapshot_identity=case_d["snapshot_x"]["snapshot_identity"],
    )
    if (
        read_evidence["status"] != SOURCE_GROUNDED
        or any(item["precondition"] != "PASS" for item in task11a_writes)
        or replay_d["classification"] != SOURCE_GROUNDING_NONCOMPLIANCE
        or replay_d["disposition"] != "ESCALATION_REQUIRED"
    ):
        raise RuntimeError("Task11E retrospective control failed")
    print(json.dumps({
        "policy_id": "SOURCE_GROUNDED_STRUCTURED_EDIT_V1",
        "model_inference_count": 0,
        "Task11A": {
            "historical_disposition": "UNCHANGED",
            "read_evidence": read_evidence,
            "subsequent_writes": task11a_writes,
            "conclusion": "GROUNDING_PRECONDITION_PASS_PATCH_TRANSPORT_FAILED",
        },
        "Task11D": {
            "historical_disposition": "UNCHANGED",
            "replay": replay_d,
            "conclusion": "GROUNDING_PRECONDITION_FAIL_STRUCTURED_TRANSPORT_NOT_ATTEMPTED",
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
