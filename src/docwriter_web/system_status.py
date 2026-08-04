"""Bounded, read-only status probes for the authenticated Developer surface."""

from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import sqlite3
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Probe:
    probe_id: str
    state: str
    value: str
    timestamp: str
    source: str
    detail: str
    details: dict[str, Any]


_CACHE: dict[str, tuple[float, dict[str, Probe]]] = {}
CACHE_SECONDS = 20.0


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _probe(probe_id: str, state: str, value: str, source: str, detail: str, **details: Any) -> Probe:
    return Probe(probe_id, state, value, _timestamp(), source, detail, details)


def _database(config: Any) -> Probe:
    path = config.database
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1)
        db.row_factory = sqlite3.Row
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        fk = db.execute("PRAGMA foreign_key_check").fetchall()
        counts = {}
        for table in ("projects", "trials", "generation_attempts", "review_events", "accepted_baselines", "audience_adaptations", "accepted_audience_versions", "generation_attempt_reconciliations"):
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            counts[table] = int(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]) if exists else 0
        migration = db.execute("SELECT migration_name,applied_at,application_commit FROM schema_migrations ORDER BY rowid DESC LIMIT 1").fetchone()
        db.close()
        state = "OK" if integrity == "ok" and not fk else "FAILED"
        return _probe("sqlite", state, str(path), "SQLite read-only probe", "integrity_check and foreign_key_check completed", size=path.stat().st_size, counts=counts, schema_version=migration["migration_name"] if migration else "unknown", latest_migration_at=migration["applied_at"] if migration else "unknown", migration_commit=migration["application_commit"] if migration else "unknown", integrity_check=integrity, foreign_key_violations=len(fk), lineage_verifier="run separately with tools/verify_lineage.py")
    except (OSError, sqlite3.Error) as exc:
        return _probe("sqlite", "UNKNOWN", str(path), "SQLite read-only probe", "The database probe could not complete.", error=type(exc).__name__)


def _storage(config: Any) -> Probe:
    try:
        usage = os.statvfs(config.runtime_root)
        total = usage.f_blocks * usage.f_frsize
        available = usage.f_bavail * usage.f_frsize
        writable = os.access(config.state_dir, os.W_OK)
        state = "OK" if writable else "DEGRADED"
        return _probe("storage", state, str(config.runtime_root), "statvfs and application path probe", "Application storage is present and writable." if writable else "Application storage is present but not writable.", total_bytes=total, available_bytes=available, writable=writable, mount_device="unavailable to unprivileged probe", filesystem="unavailable to unprivileged probe", quota="unavailable to unprivileged probe")
    except OSError as exc:
        return _probe("storage", "UNKNOWN", str(config.runtime_root), "statvfs probe", "Storage evidence is unavailable.", error=type(exc).__name__)


def _service(config: Any) -> Probe:
    try:
        pid = os.getpid()
        fields = Path(f"/proc/{pid}/stat").read_text().split()
        start_ticks = int(fields[21])
        ticks_per_second = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        uptime = max(0, time.clock_gettime(time.CLOCK_BOOTTIME) - (start_ticks / ticks_per_second))
        return _probe("docwriter-service", "OK", "docwriter.service active", "/proc and application process", "The current application process is serving the request.", pid=pid, uptime_seconds=round(uptime), user=os.environ.get("USER", "unknown"), build=config.version, backend="127.0.0.1:8787", systemd_unit="docwriter.service", listener_evidence="application launch configuration")
    except (AttributeError, OSError):
        return _probe("docwriter-service", "UNKNOWN", "docwriter.service", "application process", "Process uptime evidence is unavailable.")


def _ollama(config: Any) -> Probe:
    parsed = urllib.parse.urlparse(config.ollama_url)
    endpoint = f"{parsed.scheme}://{parsed.netloc}"
    try:
        with urllib.request.urlopen(f"{endpoint}/api/version", timeout=1) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return _probe("ollama", "OK", endpoint, "GET /api/version", "The local model service responded; no model request was made.", version=payload.get("version", "unknown"), transport="/api/chat", observation_model="mistral-nemo:12b-instruct-2407-q4_K_M", model_digest="sha256:daf6737417121831e572a9c482e92a221ee0c33537f35f1f857c7b4f7191df55")
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return _probe("ollama", "UNKNOWN", endpoint, "GET /api/version", "The local model service could not be probed without making a model request.", error=type(exc).__name__, transport="/api/chat")


def _network(config: Any) -> Probe:
    hosts = (config.canonical_host, "docwriter")
    answers = {}
    try:
        for host in hosts:
            answers[host] = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        return _probe("dns-tls", "OK", ", ".join(f"{host}={answers[host]}" for host in hosts), "getaddrinfo", "Internal hostname resolution completed. Certificate details require the reverse-proxy probe.", canonical_host=config.canonical_host, answers=answers, tls="not probed by application process")
    except OSError as exc:
        return _probe("dns-tls", "UNKNOWN", config.canonical_host, "getaddrinfo", "Internal DNS evidence is unavailable.", error=type(exc).__name__, tls="not probed")


def _contracts(bundle: Any, profiles: dict[str, Any]) -> Probe:
    hashes = dict(bundle.contract_hashes)
    hashes["response_schema"] = bundle.schema_hash
    return _probe("contracts", "OK", bundle.version, "repository contract loader", "Active writing contracts and adapter profiles loaded.", hashes=hashes, audience_profiles={key: value.profile_version for key, value in profiles.items()})


def collect(config: Any, bundle: Any, profiles: dict[str, Any], refresh: bool = False) -> dict[str, Probe]:
    key = str(config.database)
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and not refresh and now - cached[0] < CACHE_SECONDS:
        return cached[1]
    probes = {probe.probe_id: probe for probe in (_service(config), _storage(config), _database(config), _ollama(config), _network(config), _contracts(bundle, profiles))}
    _CACHE[key] = (now, probes)
    return probes
