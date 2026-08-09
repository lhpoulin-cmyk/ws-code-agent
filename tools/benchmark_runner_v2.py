#!/usr/bin/env python3
"""Frozen ten-case benchmark v2 with an explicit logical Ollama backend.

This runner deliberately imports v1's read-only fixture verifier; it does not
modify the historical runner, manifest, run directory, or blind mapping.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from tools import benchmark_runner as v1
from docwriter_web.backends import Backend, load_backends

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get("WS_DOC_WRITER_RUNTIME", "/srv/ws-doc-writer"))
RUNNER_VERSION = "ws-doc-writer-benchmark-runner/v2"
MODELS = [("qwen3:14b-q4_K_M", "sha256:bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8", "blind-amber"), ("gemma3:12b-it-q4_K_M", "sha256:f4031aab637d1ffa37b42570452ae0e4fad0314754d17ded67322e4b95836f8a", "blind-cobalt"), ("mistral-nemo:12b-instruct-2407-q4_K_M", "sha256:daf6737417121831e572a9c482e92a221ee0c33537f35f1f857c7b4f7191df55", "blind-verdant")]
SETTINGS = {"num_ctx": 8192, "temperature": 0.2, "top_p": 0.9, "seed": 42}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def api(backend: Backend, path: str, payload: dict[str, Any] | None = None) -> tuple[bytes, dict[str, Any]]:
    data = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    request = urllib.request.Request(backend.base_url + path, data=data, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"backend {backend.backend_id} API failure: {exc}") from exc
    return raw, json.loads(raw)


def expected_models() -> dict[str, str]:
    return {tag: digest for tag, digest, _ in MODELS}


def validate_contract() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest, fixtures = v1.validate_frozen()
    models = yaml.safe_load((ROOT / "manifests/models.yaml").read_text(encoding="utf-8"))
    observed = {entry["tag"]: entry["digest"] for entry in models["candidates"]}
    if observed != expected_models() or models.get("common_benchmark") != {"context": 8192, "temperature": 0.2, "top_p": 0.9, "seed": 42, "streaming": False, "thinking": "disabled"}:
        raise RuntimeError("frozen model registry contract mismatch")
    return manifest, fixtures


def inventory(backend: Backend) -> tuple[dict[str, Any], dict[str, str]]:
    _, version = api(backend, "/api/version")
    _, tags = api(backend, "/api/tags")
    found = {entry["name"]: "sha256:" + entry["digest"].removeprefix("sha256:") for entry in tags.get("models", [])}
    missing = {tag: digest for tag, digest in expected_models().items() if found.get(tag) != digest}
    if missing:
        raise RuntimeError(f"backend {backend.backend_id} frozen inventory mismatch: {missing}")
    return version, found


def processor_residency(backend: Backend, model: str) -> Any:
    _, value = api(backend, "/api/ps")
    matched = [entry for entry in value.get("models", []) if entry.get("name") == model]
    if len(matched) != 1:
        raise RuntimeError(f"backend {backend.backend_id} did not retain a single loaded model: {model}")
    return matched[0].get("size_vram", 0), matched[0]


def prompt(fixture: dict[str, Any]) -> str:
    contract = (ROOT / v1.PROMPTS[fixture["expected_output_type"]]).read_text(encoding="utf-8")
    return contract + "\n\nFrozen source material:\n" + fixture["payload"] + "\n\nWrite only the requested " + fixture["expected_output_type"] + ". Maximum length: " + str(fixture["max_output"]) + " words."


def rate(tokens: Any, duration_ns: Any) -> float | None:
    return round(float(tokens) / (float(duration_ns) / 1_000_000_000), 6) if isinstance(tokens, (int, float)) and isinstance(duration_ns, (int, float)) and duration_ns else None


def run(backend_id: str, model_selection: str, run_id: str | None = None) -> Path:
    manifest, fixtures = validate_contract()
    config_path = Path(os.environ.get("WS_DOC_WRITER_BACKENDS_FILE", "/etc/ws-doc-writer/backends.yaml"))
    backend = load_backends(config_path).get(backend_id)
    if not backend or not backend.enabled:
        raise RuntimeError(f"backend is unavailable: {backend_id}")
    requested = set(model_selection.split(",")) if model_selection != "all" else {item[0] for item in MODELS}
    selected = [item for item in MODELS if item[0] in requested]
    if not selected or len(selected) != len(requested):
        raise RuntimeError("--models must be all or a comma-separated frozen tag list")
    version, _ = inventory(backend)
    run_id = run_id or dt.datetime.now(dt.timezone.utc).strftime("benchmark-v2-%Y%m%dT%H%M%SZ")
    root = RUNTIME / "benchmarks" / "runs" / run_id
    blinded = RUNTIME / "benchmarks" / "blinded" / run_id
    root.mkdir(parents=True, exist_ok=False); blinded.mkdir(parents=True, exist_ok=False)
    metadata = {"status": "incomplete", "run_id": run_id, "runner_version": RUNNER_VERSION, "backend_id": backend.backend_id, "backend_display_name": backend.display_name, "application_commit": v1.cmd("git", "-C", str(ROOT), "rev-parse", "HEAD").strip(), "service": {"ollama_version": version}, "settings": SETTINGS, "planned_outputs": len(selected) * len(v1.CASE_IDS), "v1_fixture_manifest_sha256": sha256((ROOT / "benchmarks/fixture-manifest.yaml").read_bytes())}
    (root / "run-metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    records: list[dict[str, Any]] = []
    try:
        for model, digest, blind in selected:
            for case_id in v1.CASE_IDS:
                fixture = fixtures[case_id]
                payload = {"model": model, "prompt": prompt(fixture), "stream": False, "think": False, "keep_alive": "10m", "options": SETTINGS}
                started = dt.datetime.now(dt.timezone.utc).isoformat()
                raw, result = api(backend, "/api/generate", payload)
                vram, ps = processor_residency(backend, model)
                output = result.get("response")
                if not isinstance(output, str) or not output.strip():
                    raise RuntimeError(f"empty model output: {model}/{case_id}")
                record = {"backend_id": backend.backend_id, "model_tag": model, "model_digest": digest, "blind_id": blind, "case_id": case_id, "started_at": started, "settings": SETTINGS, "prompt_sha256": sha256(payload["prompt"].encode()), "response_sha256": sha256(output.encode()), "output": output, "processor_residency": ps, "vram_bytes": vram}
                for field in ("load_duration", "prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration", "total_duration"):
                    record[field] = result.get(field)
                record["prompt_tokens_per_second"] = rate(record["prompt_eval_count"], record["prompt_eval_duration"])
                record["generation_tokens_per_second"] = rate(record["eval_count"], record["eval_duration"])
                (root / f"{model.replace(':', '_')}-{case_id}.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
                (blinded / f"{blind}-{case_id}.json").write_text(json.dumps({k: v for k, v in record.items() if k not in {"backend_id", "model_tag", "model_digest", "processor_residency", "vram_bytes"}}, indent=2, sort_keys=True) + "\n")
                records.append(record)
        metadata.update({"status": "complete", "completed_outputs": len(records)})
    finally:
        (root / "run-metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--models", default="all")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    print(run(args.backend, args.models, args.run_id))


if __name__ == "__main__":
    main()
