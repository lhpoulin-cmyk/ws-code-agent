"""Canonical, bounded writing setup values and immutable serialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


SETUP_VERSION = "writing-setup-v1"
DEFAULT_PRIMARY_AUDIENCE = "Not specified"
DEFAULT_TONE = "Not specified"
DEFAULT_PURPOSE = "Preserve the source's material meaning, facts, uncertainty, and point of view."
DEFAULT_PRESERVATION = "Preserve the source's material meaning, facts, uncertainty, and point of view."
DEFAULT_CLARIFICATION_POLICY = "Ask one focused question when ambiguity would materially change meaning; otherwise preserve the ambiguity."
LIMITS = {
    "primary_audience": 400,
    "tone": 400,
    "purpose": 2000,
    "preservation_instructions": 4000,
    "clarification_policy": 1000,
}


@dataclass(frozen=True)
class WritingSetup:
    primary_audience: str
    tone: str
    purpose: str
    preservation_instructions: str
    clarification_policy: str

    def as_dict(self) -> dict[str, str]:
        return {
            "primary_audience": self.primary_audience,
            "tone": self.tone,
            "purpose": self.purpose,
            "preservation_instructions": self.preservation_instructions,
            "clarification_policy": self.clarification_policy,
        }


def _clean(name: str, value: str | None, default: str) -> str:
    value = (value or "").strip() or default
    if len(value) > LIMITS[name]:
        raise ValueError(f"{name.replace('_', ' ')} exceeds its length limit")
    return value


def from_form(form: dict[str, str]) -> WritingSetup:
    return WritingSetup(
        _clean("primary_audience", form.get("primary_audience"), DEFAULT_PRIMARY_AUDIENCE),
        _clean("tone", form.get("tone"), DEFAULT_TONE),
        _clean("purpose", form.get("purpose"), DEFAULT_PURPOSE),
        _clean("preservation_instructions", form.get("preservation_instructions"), DEFAULT_PRESERVATION),
        _clean("clarification_policy", form.get("clarification_policy"), DEFAULT_CLARIFICATION_POLICY),
    )


def from_row(row) -> WritingSetup:
    return WritingSetup(
        _clean("primary_audience", row["primary_audience"], DEFAULT_PRIMARY_AUDIENCE),
        _clean("tone", row["tone"], DEFAULT_TONE),
        _clean("purpose", row["purpose"], DEFAULT_PURPOSE),
        _clean("preservation_instructions", row["preservation_instructions"], DEFAULT_PRESERVATION),
        _clean("clarification_policy", row["clarification_policy"], DEFAULT_CLARIFICATION_POLICY),
    )


def serialize(setup: WritingSetup) -> str:
    return json.dumps(setup.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_serialized(serialized: str) -> str:
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def identity(setup: WritingSetup) -> tuple[str, str]:
    serialized = serialize(setup)
    return serialized, sha256_serialized(serialized)
