"""Runtime-selected, non-secret Ollama backend definitions."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Backend:
    backend_id: str
    display_name: str
    base_url: str
    enabled: bool
    accelerator_family: str = ""
    host_label: str = ""


def _default() -> dict[str, Backend]:
    return {"local": Backend("local", "Local Ollama", "http://127.0.0.1:11434", True)}


def load_backends(path: Path | None) -> dict[str, Backend]:
    """Load an operator-owned backend file, preserving the safe local default."""
    if path is None or not path.exists():
        return _default()
    value: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = value.get("backends") if isinstance(value, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError("backend configuration requires a non-empty backends list")
    result: dict[str, Backend] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("backend entry must be a mapping")
        allowed = {"id", "display_name", "base_url", "enabled", "accelerator_family", "host_label"}
        if set(item) - allowed or not all(isinstance(item.get(k), str) and item[k] for k in ("id", "display_name", "base_url")) or not isinstance(item.get("enabled"), bool):
            raise ValueError("backend entry is incomplete or contains unsupported fields")
        backend_id = item["id"]
        if backend_id in result or "/" in backend_id or any(c.isspace() for c in backend_id):
            raise ValueError("backend id must be unique and URL-safe")
        base_url = item["base_url"].rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("backend base_url must be HTTP(S)")
        result[backend_id] = Backend(backend_id, item["display_name"], base_url, item["enabled"], item.get("accelerator_family", ""), item.get("host_label", ""))
    return result
