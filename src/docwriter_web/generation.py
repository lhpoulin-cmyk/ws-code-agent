"""Bounded local Ollama generation and deterministic provenance helpers."""

from __future__ import annotations

import difflib
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

MODEL = "mistral-nemo:12b-instruct-2407-q4_K_M"
MODEL_DIGEST = "sha256:daf6737417121831e572a9c482e92a221ee0c33537f35f1f857c7b4f7191df55"
PROMPT_VERSION = "conversational-proposal-v1"
GENERATION_SETTINGS = {"context": 8192, "temperature": 0.2, "top_p": 0.9, "seed": 42, "streaming": False, "thinking": False}
REQUEST_TIMEOUT_SECONDS = 90
MAX_MODEL_RESPONSE = 50000
INTEGRITY_CATEGORIES = {"confirmed conflict", "apparent conflict requiring authority review", "unsupported claim", "ambiguity", "no material issue found"}
ERROR_CLASSES = {
    "OLLAMA_UNAVAILABLE",
    "REQUEST_TIMEOUT",
    "OLLAMA_HTTP_ERROR",
    "EMPTY_RESPONSE",
    "RESPONSE_SCHEMA_INVALID",
    "PROPOSAL_FIELD_MISSING",
    "UNKNOWN_FAILURE",
}

PROMPT_CONTRACT = """You are Doc Writer's conversational proposal reviewer.

Return exactly one JSON object with these fields:
{{"integrity_findings":[{{"category":"...","detail":"..."}}],"conversational_proposal":"..."}}

The category must be one of: confirmed conflict; apparent conflict requiring authority review; unsupported claim; ambiguity; no material issue found.
Preserve facts, authority, uncertainty, identifiers, status, and unresolved matters. Identify claims that conflict, lack support, or are ambiguous. Never silently repair a factual conflict or introduce a recommendation, decision, fact, or certainty. Produce exactly one natural, direct conversational proposal. Keep it to one paragraph unless one paragraph would materially distort meaning. Avoid bureaucratic, academic, or consultant-style prose.

Portfolio voice contract: direct technical prose; evidence before conclusions; distinguish observed, intended, proposed, prepared, deployed, validated, accepted, blocked, deferred, and unresolved; preserve exact terminology and factual limits.

Source paragraph:
{source}
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def serialized_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def exact_diff(source: str, proposal: str) -> str:
    return "".join(difflib.unified_diff((source + "\n").splitlines(True), (proposal + "\n").splitlines(True), fromfile="source paragraph", tofile="conversational proposal"))


def prompt_for(source: str) -> str:
    return PROMPT_CONTRACT.format(source=source)


def response_schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": ["integrity_findings", "conversational_proposal"], "properties": {"integrity_findings": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["category", "detail"], "properties": {"category": {"type": "string", "enum": sorted(INTEGRITY_CATEGORIES)}, "detail": {"type": "string", "maxLength": 4000}}}}, "conversational_proposal": {"type": "string", "minLength": 1, "maxLength": 12000}}}


def request_payload_for(source: str) -> dict[str, Any]:
    return {"model": MODEL, "prompt": prompt_for(source), "stream": False, "format": response_schema(), "think": False, "options": {"num_ctx": GENERATION_SETTINGS["context"], "temperature": GENERATION_SETTINGS["temperature"], "top_p": GENERATION_SETTINGS["top_p"], "seed": GENERATION_SETTINGS["seed"]}}


class ResponseSchemaError(ValueError):
    def __init__(self, message: str, error_class: str = "RESPONSE_SCHEMA_INVALID"):
        super().__init__(message)
        self.error_class = error_class


def parse_response(raw_response: str) -> tuple[list[dict[str, str]], str]:
    if len(raw_response.encode("utf-8")) > MAX_MODEL_RESPONSE:
        raise ResponseSchemaError("model response exceeds output limit")
    try:
        decoded = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ResponseSchemaError("model response is not valid JSON") from exc
    if not isinstance(decoded, dict) or set(decoded) != {"integrity_findings", "conversational_proposal"}:
        if isinstance(decoded, dict) and "conversational_proposal" not in decoded:
            raise ResponseSchemaError("structured response is missing conversational_proposal", "PROPOSAL_FIELD_MISSING")
        raise ResponseSchemaError("structured response fields are invalid")
    findings, proposal = decoded["integrity_findings"], decoded["conversational_proposal"]
    if not isinstance(findings, list) or not isinstance(proposal, str) or not proposal.strip():
        if not isinstance(proposal, str) or not proposal.strip():
            raise ResponseSchemaError("conversational_proposal is empty", "PROPOSAL_FIELD_MISSING")
        raise ResponseSchemaError("structured response types are invalid")
    normalized: list[dict[str, str]] = []
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {"category", "detail"}:
            raise ResponseSchemaError("integrity finding shape is invalid")
        category, detail = finding["category"], finding["detail"]
        if category not in INTEGRITY_CATEGORIES or not isinstance(detail, str) or len(detail) > 4000:
            raise ResponseSchemaError("integrity finding value is invalid")
        normalized.append({"category": category, "detail": detail})
    return normalized, proposal.strip()


@dataclass(frozen=True)
class GenerationResult:
    model_identifier: str
    model_digest: str
    request_json: str
    prompt: str
    prompt_hash: str
    started_at: str
    completed_at: str
    raw_ollama_response: str
    response_payload: dict[str, Any]
    integrity_findings: list[dict[str, str]]
    proposal: str
    source_to_proposal_diff: str
    response_hash: str
    proposal_hash: str
    telemetry: dict[str, Any]


class OllamaError(RuntimeError):
    def __init__(self, message: str, raw_response: str = "", response_payload: dict[str, Any] | None = None, error_class: str = "UNKNOWN_FAILURE"):
        super().__init__(message)
        self.raw_response = raw_response
        self.response_payload = response_payload or {}
        self.error_class = error_class if error_class in ERROR_CLASSES else "UNKNOWN_FAILURE"


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", opener: Callable = urllib.request.urlopen):
        self.base_url = base_url.rstrip("/")
        self.opener = opener

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else serialized_json(payload).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data, headers={"Content-Type": "application/json"} if data else {})
        try:
            with self.opener(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                raw = response.read(MAX_MODEL_RESPONSE + 1)
        except urllib.error.HTTPError as exc:
            raw = exc.read(MAX_MODEL_RESPONSE + 1)
            try:
                payload_value = json.loads(raw.decode("utf-8"))
                payload = payload_value if isinstance(payload_value, dict) else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}
            raise OllamaError(f"Ollama HTTP status {exc.code}", raw.decode("utf-8", errors="replace"), payload, "OLLAMA_HTTP_ERROR") from exc
        except TimeoutError as exc:
            raise OllamaError("local Ollama request timed out", error_class="REQUEST_TIMEOUT") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise OllamaError("local Ollama request timed out", error_class="REQUEST_TIMEOUT") from exc
            raise OllamaError("local Ollama is unavailable", error_class="OLLAMA_UNAVAILABLE") from exc
        except OSError as exc:
            raise OllamaError("local Ollama is unavailable", error_class="OLLAMA_UNAVAILABLE") from exc
        if len(raw) > MAX_MODEL_RESPONSE:
            raise OllamaError("local Ollama response exceeds output limit", error_class="RESPONSE_SCHEMA_INVALID")
        if not raw:
            raise OllamaError("local Ollama returned an empty response", error_class="EMPTY_RESPONSE")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaError("local Ollama returned invalid JSON", raw.decode("utf-8", errors="replace"), error_class="RESPONSE_SCHEMA_INVALID") from exc
        if not isinstance(value, dict):
            raise OllamaError("local Ollama response is not an object", raw.decode("utf-8", errors="replace"), error_class="RESPONSE_SCHEMA_INVALID")
        return value

    def installed_digest(self, model: str) -> str:
        tags = self._request("/api/tags")
        for item in tags.get("models", []):
            if item.get("name") == model or item.get("model") == model:
                digest = item.get("digest")
                if isinstance(digest, str):
                    return digest if digest.startswith("sha256:") else "sha256:" + digest
        raise OllamaError("configured model is not installed locally")

    def generate(self, source: str) -> GenerationResult:
        digest = self.installed_digest(MODEL)
        if digest != MODEL_DIGEST:
            raise OllamaError("installed model digest does not match the pinned digest")
        prompt = prompt_for(source)
        request_payload = request_payload_for(source)
        started_at = utc_now()
        started_monotonic = time.monotonic()
        response_payload = self._request("/api/generate", request_payload)
        completed_at = utc_now()
        raw = response_payload.get("response")
        if not isinstance(raw, str) or not raw.strip():
            raise OllamaError("local Ollama response has no structured response text", serialized_json(response_payload), response_payload, "EMPTY_RESPONSE")
        try:
            findings, proposal = parse_response(raw)
        except ResponseSchemaError as exc:
            raise OllamaError(str(exc), raw, response_payload, exc.error_class) from exc
        telemetry = {key: response_payload[key] for key in ("total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration") if key in response_payload and isinstance(response_payload[key], (int, float))}
        telemetry["wall_seconds"] = round(time.monotonic() - started_monotonic, 6)
        return GenerationResult(MODEL, digest, serialized_json(request_payload), prompt, sha256_text(prompt), started_at, completed_at, raw, response_payload, findings, proposal, exact_diff(source, proposal), sha256_text(raw), sha256_text(proposal), telemetry)
