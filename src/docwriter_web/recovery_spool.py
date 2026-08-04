"""Restricted pre-persistence evidence spool; never replays model requests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def spool_path(runtime_root: Path, attempt_id: str) -> Path:
    root = runtime_root / "recovery"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root / f"{attempt_id}.json"


def write_spool(runtime_root: Path, attempt_id: str, evidence: dict[str, Any]) -> Path:
    path = spool_path(runtime_root, attempt_id)
    payload = {"attempt_id": attempt_id, "evidence": evidence, "request_sha256": hashlib.sha256(str(evidence.get("request_json", "")).encode()).hexdigest(), "response_sha256": hashlib.sha256(str(evidence.get("raw_response", "")).encode()).hexdigest(), "replay": False}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)
    return path


def read_spool(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def remove_after_verified_persistence(path: Path) -> None:
    path.unlink()
