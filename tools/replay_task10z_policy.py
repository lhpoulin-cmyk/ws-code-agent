#!/usr/bin/env python3
"""Classify the immutable Task 10Y sessions under Task 10Z without inference."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.interactive_work_policy import classify  # noqa: E402


WORK_ROOT = Path.home() / ".local/share/ws-code-agent/work"
SESSIONS = {
    "write": {
        "name": "work-task10y-qwen25-14b-write-20260811T235900Z",
        "patch_authorized": True,
        "raw_shas": (
            "c71599a739e700cab11516bb8f82e7e6ca8a7566966c6e9c44f4d87cdd955a91",
            "24e413c7a46e952f86471004bc7dcd916dc0e4c4b82d0dd8df70337bb7b19e55",
        ),
    },
    "clarification": {
        "name": "work-task10y-qwen25-14b-clarification-20260811T235900Z",
        "patch_authorized": False,
        "raw_shas": (
            "ecaef9559fa11f5ba2f70dec92f09357e57f4a682dcc559f52455f3ced3c2113",
            "36846434d9faeeac3e864cf539f7655d6c2ecf5ef1ab5601a423b56eb07bfa3e",
            "46747037f102c8de20b4f7000045536ac0a286d52837baafc942771a60ff6784",
        ),
    },
}


def replay(name: str, record: dict[str, object]) -> dict[str, object]:
    root = WORK_ROOT / str(record["name"])
    turns = []
    for number, expected_sha in enumerate(record["raw_shas"], 1):
        directory = root / "cases/WORK/turns" / f"{number:04d}"
        raw = (directory / "raw-response.txt").read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise RuntimeError(f"{name}: PRESERVED_RAW_IDENTITY_MISMATCH")
        turns.append(json.loads((directory / "harness-result.json").read_text(encoding="utf-8")))
    decision = classify(turns, patch_authorized=bool(record["patch_authorized"]))
    return {
        "session": record["name"],
        "turn_count": len(turns),
        "raw_response_identity": "MATCH",
        "request_sequence": [item.get("request_type") for item in turns],
        "authority_sequence": [item.get("authority_outcome") for item in turns],
        "decision": decision.evidence(),
    }


def main() -> int:
    result = {
        "policy_id": "INTERACTIVE_BOUNDED_WORK_V1",
        "historical_task10y_disposition_changed": False,
        "model_inference_count": 0,
        "sessions": {name: replay(name, record) for name, record in SESSIONS.items()},
    }
    expected = {
        "write": ("INTERACTIVE_RECOVERY_FAILED", "NO_CHANGE_AFTER_PATCH_REJECTED"),
        "clarification": ("INTERACTIVE_AUTHORITY_MISJUDGMENT", "AUTHORITY_MISJUDGMENT"),
    }
    for name, pair in expected.items():
        decision = result["sessions"][name]["decision"]
        if (decision["classification"], decision["reason"]) != pair:
            raise RuntimeError(f"{name}: UNEXPECTED_POLICY_CLASSIFICATION")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
