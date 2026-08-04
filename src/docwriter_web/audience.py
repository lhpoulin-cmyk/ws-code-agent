"""Audience contracts, deterministic states, and safe input binding."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AUDIENCE_VERSION = "audience-adaptation-v2"
PROFILES = {slug: ROOT / f"prompts/audiences/{slug}.md" for slug in ("technical-peer", "executive", "public")}
CATEGORIES = {"confirmed_conflict", "apparent_conflict_requiring_authority_review", "unsupported_claim", "ambiguity", "no_material_issue_found"}

def sha256_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha256_text(value: str) -> str: return sha256_bytes(value.encode())
def profile_contract(slug: str) -> tuple[str, str]:
    path = PROFILES.get(slug)
    if not path or not path.is_file(): raise ValueError("unknown audience profile")
    raw = path.read_bytes(); return raw.decode(), sha256_bytes(raw)
def audience_schema() -> dict[str, Any]:
    return {"type":"object","additionalProperties":False,"required":["integrity_findings","audience_adaptation"],"properties":{"integrity_findings":{"type":"array","minItems":1,"maxItems":8,"items":{"type":"object","additionalProperties":False,"required":["category","detail"],"properties":{"category":{"type":"string","enum":sorted(CATEGORIES)},"detail":{"type":"string","minLength":1,"maxLength":4000}}}},"audience_adaptation":{"type":"string","minLength":1}}}
def parse_audience_response(raw: str) -> tuple[list[dict[str, str]], str]:
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {"integrity_findings", "audience_adaptation"}: raise ValueError("audience response schema is invalid")
    text = value["audience_adaptation"]
    if not isinstance(text, str) or not text.strip(): raise ValueError("audience adaptation is missing")
    findings = value["integrity_findings"]
    if not isinstance(findings, list): raise ValueError("audience integrity findings are invalid")
    if not findings: raise ValueError("audience integrity findings must contain exactly one no_material_issue_found finding or substantive findings")
    no_issue = [finding for finding in findings if isinstance(finding, dict) and finding.get("category") == "no_material_issue_found"]
    if no_issue and (len(findings) != 1 or not isinstance(no_issue[0].get("detail"), str) or not no_issue[0]["detail"].strip() or len(no_issue[0]["detail"]) > 4000):
        raise ValueError("no_material_issue_found must be the sole concise non-blocking finding")
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {"category", "detail"} or finding["category"] not in CATEGORIES or not isinstance(finding["detail"], str) or not finding["detail"].strip() or len(finding["detail"]) > 4000: raise ValueError("audience integrity finding is invalid")
    return findings, text.strip()
def derived_state(adaptation: Any, attempts: list[Any], events: list[Any], accepted: list[Any] = ()) -> str:
    if not attempts: return "AUDIENCE_GENERATION_REQUIRED"
    attempt = sorted(attempts, key=lambda r: (r["started_at"], r["attempt_id"]))[-1]
    if attempt["status"] == "RUNNING": return "AUDIENCE_GENERATION_RUNNING"
    if attempt["status"] != "COMPLETED" or not (attempt["normalized_proposal"] or "").strip(): return "AUDIENCE_GENERATION_FAILED"
    target = [e for e in events if e["event_type"] == "AUDIENCE_REVIEW_TARGET_SELECTED"]
    if not target: return "AUDIENCE_REVIEW_TARGET_REQUIRED"
    outcome = [e for e in events if e["stage"] == "AUDIENCE"]
    latest = sorted(outcome, key=lambda r: (r["created_at"], r["event_id"]))[-1] if outcome else None
    if latest is None: return "AUDIENCE_REVIEW_REQUIRED"
    if latest["decision"] == "AUDIENCE_REVISION_REQUIRED": return "AUDIENCE_REVISION_REQUIRED"
    if latest["decision"] == "AUDIENCE_REJECTED": return "AUDIENCE_REJECTED"
    if latest["decision"] == "AUDIENCE_ACCEPTED": return "AUDIENCE_ACCEPTED"
    return "AUDIENCE_REVIEW_REQUIRED"
