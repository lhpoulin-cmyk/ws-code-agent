#!/usr/bin/env python3
"""Deterministic ws-doc-writer benchmark runner.

The runner reads frozen application inputs and writes only beneath the approved
runtime benchmark volume. It never writes portfolio repositories or selects a
model winner.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get("WS_DOC_WRITER_RUNTIME", "/srv/ws-doc-writer"))
BENCH = RUNTIME / "benchmarks"
RUNNER_VERSION = "ws-doc-writer-benchmark-runner/v1"
CASE_IDS = [
    "architecture-from-notes", "discovery-to-evidence", "decisions-to-ledger",
    "peer-conflict", "incident-addendum", "concise-revision",
    "stale-correction", "appropriate-humor", "unresolved-claims", "reconciliation",
]
MODELS = [
    ("qwen3:14b-q4_K_M", "sha256:bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8", "blind-amber"),
    ("gemma3:12b-it-q4_K_M", "sha256:f4031aab637d1ffa37b425704ae0e4fad0314754d17ded67322e4b95836f8a", "blind-cobalt"),
    ("mistral-nemo:12b-instruct-2407-q4_K_M", "sha256:daf6737417121831e572a9c482e92a221ee0c33537f35f1f857c7b4f7191df55", "blind-verdant"),
]
SETTINGS = {"num_ctx": 8192, "temperature": 0.2, "top_p": 0.9, "seed": 42}
PROMPTS = {
    "architecture section": "prompts/architecture-writer.md",
    "factual evidence report": "prompts/evidence-summarizer.md",
    "decision-ledger entry": "prompts/decision-ledger-writer.md",
    "fail-closed explanation": "prompts/evidence-summarizer.md",
    "factual addendum": "prompts/factual-correction-editor.md",
    "diff-friendly revision": "prompts/concise-technical-editor.md",
    "correction preserving history": "prompts/factual-correction-editor.md",
    "readable status note": "prompts/concise-technical-editor.md",
    "blocked requirements note": "prompts/evidence-summarizer.md",
    "reconciled technical section": "prompts/architecture-writer.md",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        value = yaml.safe_load(f)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected mapping: {path}")
    return value


def cmd(*args: str, check: bool = True) -> str:
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout


def api(path: str, payload: dict[str, Any] | None = None) -> tuple[bytes, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    request = urllib.request.Request("http://127.0.0.1:11434" + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            raw = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama API failure: {exc}") from exc
    return raw, json.loads(raw)


def validate_frozen() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    cases_path = ROOT / "benchmarks/cases.yaml"
    manifest_path = ROOT / "benchmarks/fixture-manifest.yaml"
    manifest = read_yaml(manifest_path)
    if manifest.get("runner_version") != RUNNER_VERSION:
        raise RuntimeError("runner version mismatch")
    expected_cases_hash = manifest["cases_manifest_sha256"]
    if sha256_file(cases_path) != expected_cases_hash:
        raise RuntimeError("cases manifest hash mismatch")
    cases = read_yaml(cases_path).get("cases", [])
    if [case.get("id") for case in cases] != CASE_IDS:
        raise RuntimeError("authoritative case IDs mismatch")
    fixtures: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("fixtures", []):
        case_id = entry["case_id"]
        path = ROOT / entry["path"]
        if case_id in fixtures or sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"fixture hash mismatch: {case_id}")
        fixture = read_yaml(path)
        if fixture.get("case_id") != case_id:
            raise RuntimeError(f"fixture ID mismatch: {case_id}")
        source_case = next(case for case in cases if case["id"] == case_id)
        for field in ("required_facts", "forbidden_inventions", "authority_boundaries", "exact_terminology"):
            if fixture.get(field) != source_case[field]:
                raise RuntimeError(f"fixture contract mismatch: {case_id}:{field}")
        fixtures[case_id] = fixture
    if set(fixtures) != set(CASE_IDS):
        raise RuntimeError("fixture set mismatch")
    for path_text, expected in manifest["contract_hashes"].items():
        if sha256_file(ROOT / path_text) != expected:
            raise RuntimeError(f"contract hash mismatch: {path_text}")
    runner_hash = sha256_file(Path(__file__))
    if manifest.get("runner_sha256") != runner_hash:
        raise RuntimeError("runner hash mismatch")
    return manifest, fixtures


def validate_runtime() -> None:
    source, target, fstype, options = cmd("findmnt", "-no", "SOURCE,TARGET,FSTYPE,OPTIONS", str(RUNTIME)).strip().split()
    if target != str(RUNTIME) or fstype != "xfs" or "rw" not in options.split(",") or "prjquota" not in options.split(","):
        raise RuntimeError(f"runtime mount invariant failed: {source} {target} {fstype} {options}")
    stat = cmd("xfs_io", "-c", "stat", str(BENCH)).lower()
    if "project = 1002" not in stat and "project: 1002" not in stat:
        raise RuntimeError("benchmark directory is not project 1002")
    quota = cmd("xfs_quota", "-x", "-c", "report -h", str(RUNTIME))
    line = next((line for line in quota.splitlines() if line.strip().startswith("benchmarks")), "")
    if "20G" not in line:
        raise RuntimeError("benchmark quota is not 20 GiB")
    if not os.access(BENCH, os.W_OK):
        raise RuntimeError("benchmark runtime is not writable")


def validate_api_and_models() -> dict[str, Any]:
    listeners = cmd("ss", "-lnt").splitlines()
    matches = [line for line in listeners if ":11434" in line]
    if len(matches) != 1 or "127.0.0.1:11434" not in matches[0]:
        raise RuntimeError(f"API is not loopback-only: {matches}")
    _, version = api("/api/version")
    raw, tags = api("/api/tags")
    observed = {item["name"]: item["digest"] for item in tags.get("models", [])}
    expected = {tag: digest for tag, digest, _ in MODELS}
    if observed != expected:
        raise RuntimeError(f"model inventory mismatch: {observed}")
    return {"version": version, "tags_sha256": sha256_bytes(raw)}


def residency(model: str) -> tuple[str, str]:
    output = cmd("ollama", "ps")
    rows = [line for line in output.splitlines() if model in line]
    if len(rows) != 1 or "100% GPU" not in rows[0] or "8192" not in rows[0]:
        raise RuntimeError(f"residency gate failed for {model}: {output}")
    return rows[0], output


def gpu_snapshot() -> str:
    return cmd("rocm-smi", "--showuse", "--showmemuse", "--showtemp", "--showpower", check=False)


def planned_pairs() -> list[tuple[str, str]]:
    return [(model, case_id) for model, _, _ in MODELS for case_id in CASE_IDS]


def request_prompt(model: str, fixture: dict[str, Any], contract: str) -> tuple[bytes, dict[str, Any]]:
    prompt = (contract + "\n\nFrozen source material:\n" + fixture["payload"] +
              "\n\nWrite only the requested " + fixture["expected_output_type"] +
              ". Maximum length: " + str(fixture["max_output"]) + " words.")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "keep_alive": "5m",
        "options": SETTINGS,
    }
    return api("/api/generate", payload)


def write_json(path: Path, value: Any, mode: int = 0o640) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, mode)


def run(run_id: str | None = None) -> Path:
    manifest, fixtures = validate_frozen()
    validate_runtime()
    service = validate_api_and_models()
    if cmd("git", "-C", str(ROOT), "status", "--porcelain").strip():
        raise RuntimeError("application repository is dirty; commit benchmark revision first")
    run_id = run_id or dt.datetime.now(dt.timezone.utc).strftime("benchmark-%Y%m%dT%H%M%SZ")
    raw_root = BENCH / "runs" / run_id
    blind_root = BENCH / "blinded" / run_id
    raw_root.mkdir(parents=True, exist_ok=False)
    blind_root.mkdir(parents=True, exist_ok=False)
    mapping = {blind: {"model": model, "digest": digest} for model, digest, blind in MODELS}
    write_json(raw_root / "mapping.json", mapping, 0o600)
    write_json(raw_root / "run-metadata.json", {"status": "incomplete", "run_id": run_id, "runner_version": RUNNER_VERSION, "application_commit": cmd("git", "-C", str(ROOT), "rev-parse", "HEAD").strip(), "service": service, "settings": SETTINGS, "planned_outputs": 30}, 0o640)
    records: list[dict[str, Any]] = []
    try:
        for model, digest, blind in MODELS:
            contract_paths = {fixture["expected_output_type"]: PROMPTS[fixture["expected_output_type"]] for fixture in fixtures.values()}
            for case_id in CASE_IDS:
                fixture = fixtures[case_id]
                contract_path = ROOT / contract_paths[fixture["expected_output_type"]]
                contract = contract_path.read_text(encoding="utf-8")
                started = dt.datetime.now(dt.timezone.utc)
                raw, response = request_prompt(model, fixture, contract)
                completed = dt.datetime.now(dt.timezone.utc)
                ps_row, ps_full = residency(model)
                raw_dir = raw_root / blind / case_id
                blind_dir = blind_root / case_id
                raw_dir.mkdir(parents=True, exist_ok=True)
                blind_dir.mkdir(parents=True, exist_ok=True)
                (raw_dir / "response.json").write_bytes(raw)
                os.chmod(raw_dir / "response.json", 0o640)
                output = response.get("response", "")
                (raw_dir / "output.txt").write_text(output, encoding="utf-8")
                os.chmod(raw_dir / "output.txt", 0o640)
                (blind_dir / f"{blind}.txt").write_text(output, encoding="utf-8")
                os.chmod(blind_dir / f"{blind}.txt", 0o640)
                record = {
                    "benchmark_revision": manifest["benchmark_revision"], "case_id": case_id,
                    "blind_model_id": blind, "model_tag": model, "resolved_model_digest": digest,
                    "ollama_version": service["version"], "rocm_version": cmd("rpm", "-q", "rocm-runtime", check=False).strip(),
                    "gpu_identity": "0000:03:00.0 1002:7550 148c:2435 gfx1201",
                    "context_size": 8192, "generation_parameters": {**SETTINGS, "think": False, "stream": False},
                    "prompt_contract_hash": sha256_file(contract_path), "voice_hash": sha256_file(ROOT / "VOICE.md"),
                    "source_fixture_hash": sha256_file(ROOT / "benchmarks" / "fixtures" / f"{case_id}.yaml"),
                    "start_timestamp": started.isoformat(), "completion_timestamp": completed.isoformat(),
                    "load_duration": response.get("load_duration"), "first_token_latency": None,
                    "total_generation_duration": response.get("total_duration"), "output_token_count": response.get("eval_count"),
                    "generation_rate": ((response.get("eval_count") or 0) / (response.get("eval_duration") or 1)) * 1_000_000_000,
                    "processor_residency": ps_row, "gpu_snapshot": gpu_snapshot(),
                    "raw_output_sha256": sha256_bytes(raw), "execution_disposition": "generated-review-required",
                    "raw_reference": str(raw_dir.relative_to(raw_root)),
                }
                write_json(raw_dir / "metadata.json", record)
                records.append(record)
            api("/api/generate", {"model": model, "prompt": "", "stream": False, "keep_alive": 0})
        review = {"benchmark_revision": manifest["benchmark_revision"], "status": "REVIEW_REQUIRED", "operator_disposition": "unresolved", "cases": [{"case_id": case_id, "output_type": fixtures[case_id]["expected_output_type"], "required_fact_checklist": fixtures[case_id]["required_facts"], "forbidden_invention_checklist": fixtures[case_id]["forbidden_inventions"], "outputs": [blind for _, _, blind in MODELS]} for case_id in CASE_IDS]}
        write_json(blind_root / "review-bundle.json", review)
        write_json(raw_root / "records.json", records)
        write_json(raw_root / "run-metadata.json", {"status": "complete", "run_id": run_id, "runner_version": RUNNER_VERSION, "benchmark_revision": manifest["benchmark_revision"], "expected_outputs": 30, "actual_outputs": len(records), "application_commit": cmd("git", "-C", str(ROOT), "rev-parse", "HEAD").strip(), "operator_disposition": "unresolved"})
        return blind_root
    except Exception as exc:
        write_json(raw_root / "run-metadata.json", {"status": "incomplete", "run_id": run_id, "actual_outputs": len(records), "error": str(exc)})
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    validate_frozen()
    if args.dry_run:
        print(json.dumps({"status": "dry-run", "planned_outputs": len(planned_pairs()), "settings": SETTINGS, "sequential": True}))
        return 0
    print(run(args.run_id))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"benchmark runner failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
