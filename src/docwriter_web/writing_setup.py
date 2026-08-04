"""Explicit, bounded writing intent and immutable setup serialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


SETUP_VERSION = "writing-setup-explicit-intent-v1"
LEGACY_SETUP_VERSION = "writing-setup-v1"
SETUP_STATES = {"DRAFT", "COMPLETE", "LEGACY_UNVERIFIED"}
PROVENANCE_OPERATOR = "OPERATOR_ENTERED"
PROVENANCE_LEGACY = "LEGACY_UNVERIFIED"
FIELDS = (
    "primary_audience",
    "tone",
    "purpose",
    "preservation_instructions",
    "clarification_policy",
)
LIMITS = {
    "primary_audience": 400,
    "tone": 400,
    "purpose": 2000,
    "preservation_instructions": 4000,
    "clarification_policy": 1000,
}


@dataclass(frozen=True)
class WritingSetup:
    primary_audience: str = ""
    tone: str = ""
    purpose: str = ""
    preservation_instructions: str = ""
    clarification_policy: str = ""
    completion_state: str = "DRAFT"
    field_provenance: dict[str, str] | None = None
    setup_contract_version: str = SETUP_VERSION
    confirmed_at: str | None = None
    confirmed_by: str | None = None

    def values(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in FIELDS}

    def as_dict(self) -> dict[str, object]:
        return {
            **self.values(),
            "completion_state": self.completion_state,
            "field_provenance": dict(self.field_provenance or {}),
            "setup_contract_version": self.setup_contract_version,
        }

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(field for field in FIELDS if not self.values()[field].strip())

    @property
    def explicit_complete(self) -> bool:
        provenance = self.field_provenance or {}
        return (
            self.completion_state == "COMPLETE"
            and not self.missing_fields
            and all(provenance.get(field) == PROVENANCE_OPERATOR for field in FIELDS)
        )

    def confirmed(self, confirmed_at: str, confirmed_by: str) -> "WritingSetup":
        if self.missing_fields:
            raise ValueError("finish every writing-setup decision before confirming")
        return WritingSetup(
            **self.values(),
            completion_state="COMPLETE",
            field_provenance={field: PROVENANCE_OPERATOR for field in FIELDS},
            setup_contract_version=SETUP_VERSION,
            confirmed_at=confirmed_at,
            confirmed_by=confirmed_by,
        )


def _clean(name: str, value: str | None) -> str:
    cleaned = (value or "").strip()
    if len(cleaned) > LIMITS[name]:
        raise ValueError(f"{name.replace('_', ' ')} exceeds its length limit")
    return cleaned


def from_form(form: dict[str, str]) -> WritingSetup:
    policy = form.get("clarification_policy") or form.get("clarification_policy_custom")
    values = {field: _clean(field, form.get(field)) for field in FIELDS if field != "clarification_policy"}
    values["clarification_policy"] = _clean("clarification_policy", policy)
    provenance = {field: PROVENANCE_OPERATOR for field, value in values.items() if value}
    # Saving values is not confirmation. A separate authenticated action
    # creates the COMPLETE immutable version.
    return WritingSetup(**values, completion_state="DRAFT", field_provenance=provenance)


def from_row(row) -> WritingSetup:
    keys = set(row.keys())
    values = {field: _clean(field, row[field] if field in keys else "") for field in FIELDS}
    if "completion_state" not in keys:
        return WritingSetup(**values, completion_state="LEGACY_UNVERIFIED", field_provenance={field: PROVENANCE_LEGACY for field in FIELDS}, setup_contract_version=LEGACY_SETUP_VERSION)
    try:
        provenance = json.loads(row["field_provenance_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        provenance = {}
    return WritingSetup(
        **values,
        completion_state=row["completion_state"] or "LEGACY_UNVERIFIED",
        field_provenance=provenance if isinstance(provenance, dict) else {},
        setup_contract_version=row["setup_contract_version"] or LEGACY_SETUP_VERSION,
        confirmed_at=row["confirmed_at"],
        confirmed_by=row["confirmed_by"],
    )


def serialize(setup: WritingSetup) -> str:
    return json.dumps(setup.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_serialized(serialized: str) -> str:
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def identity(setup: WritingSetup) -> tuple[str, str]:
    serialized = serialize(setup)
    return serialized, sha256_serialized(serialized)


def missing_labels(setup: WritingSetup) -> list[str]:
    labels = {
        "primary_audience": "who should understand this version first",
        "tone": "how the writing should feel to its reader",
        "purpose": "what this piece should accomplish",
        "preservation_instructions": "what the writer must not change or leave out",
        "clarification_policy": "what the writer should do when the meaning is genuinely unclear",
    }
    return [labels[field] for field in setup.missing_fields]
