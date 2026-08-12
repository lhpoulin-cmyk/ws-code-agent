"""Trusted objective-derived validation registry for supervised work."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping

from .validation import ValidationDescriptor, ValidationRole


VISIBLE_VALIDATION_ID = "task10k-c-write-visible-v1"
HIDDEN_VALIDATION_ID = "task10k-c-write-hidden-v1"
WRITE_VALIDATION_IDS = (VISIBLE_VALIDATION_ID, HIDDEN_VALIDATION_ID)
TASK11J_VISIBLE_VALIDATION_ID = "task11j-ws-doc-writer-src-readme-visible-v1"
TASK11J_HIDDEN_VALIDATION_ID = "task11j-ws-doc-writer-src-readme-hidden-v1"
TASK11J_VALIDATION_IDS = (
    TASK11J_VISIBLE_VALIDATION_ID,
    TASK11J_HIDDEN_VALIDATION_ID,
)
REGISTRY_ROOT = Path(__file__).resolve().parents[2] / "validation-assets"
VISIBLE_SOURCE = REGISTRY_ROOT / f"{VISIBLE_VALIDATION_ID}.py"
HIDDEN_SOURCE = REGISTRY_ROOT / f"{HIDDEN_VALIDATION_ID}.py"
TASK11J_VISIBLE_SOURCE = REGISTRY_ROOT / f"{TASK11J_VISIBLE_VALIDATION_ID}.py"
TASK11J_HIDDEN_SOURCE = REGISTRY_ROOT / f"{TASK11J_HIDDEN_VALIDATION_ID}.py"


def validation_registry() -> dict[str, ValidationDescriptor]:
    visible = ValidationDescriptor(
        VISIBLE_VALIDATION_ID,
        "v1",
        "/usr/bin/python3",
        ("-B", str(VISIBLE_SOURCE)),
        ".",
        10,
        ValidationRole.VISIBLE,
        True,
        repository_writes_allowed=False,
        containment_required=True,
    )
    hidden = ValidationDescriptor(
        HIDDEN_VALIDATION_ID,
        "v1",
        "/usr/bin/python3",
        ("-B", str(HIDDEN_SOURCE)),
        ".",
        10,
        ValidationRole.HIDDEN_ORACLE,
        True,
        repository_writes_allowed=False,
        containment_required=True,
    )
    task11j_visible = ValidationDescriptor(
        TASK11J_VISIBLE_VALIDATION_ID,
        "v1",
        "/usr/bin/python3",
        ("-B", str(TASK11J_VISIBLE_SOURCE)),
        ".",
        10,
        ValidationRole.VISIBLE,
        True,
        repository_writes_allowed=False,
        containment_required=True,
    )
    task11j_hidden = ValidationDescriptor(
        TASK11J_HIDDEN_VALIDATION_ID,
        "v1",
        "/usr/bin/python3",
        ("-B", str(TASK11J_HIDDEN_SOURCE)),
        ".",
        10,
        ValidationRole.HIDDEN_ORACLE,
        True,
        repository_writes_allowed=False,
        containment_required=True,
    )
    descriptors = (visible, hidden, task11j_visible, task11j_hidden)
    return {descriptor.descriptor_id: descriptor for descriptor in descriptors}


def descriptor_source(descriptor_id: str) -> Path:
    sources = {
        VISIBLE_VALIDATION_ID: VISIBLE_SOURCE,
        HIDDEN_VALIDATION_ID: HIDDEN_SOURCE,
        TASK11J_VISIBLE_VALIDATION_ID: TASK11J_VISIBLE_SOURCE,
        TASK11J_HIDDEN_VALIDATION_ID: TASK11J_HIDDEN_SOURCE,
    }
    try:
        source = sources[descriptor_id]
    except KeyError as error:
        raise ValueError("validation descriptor is not registry-owned") from error
    if not source.is_file() or source.is_symlink():
        raise ValueError("validation descriptor source is unavailable")
    return source


def descriptor_binding(descriptor: ValidationDescriptor) -> dict[str, object]:
    source = descriptor_source(descriptor.descriptor_id)
    payload = {
        "descriptor_id": descriptor.descriptor_id,
        "version": descriptor.version,
        "role": descriptor.role.value,
        "executable": descriptor.executable,
        "arguments": list(descriptor.arguments),
        "working_directory": descriptor.working_directory,
        "timeout_seconds": descriptor.timeout_seconds,
        "model_visible_by_id_only": descriptor.model_visible_by_id_only,
        "repository_writes_allowed": descriptor.repository_writes_allowed,
        "requires_post_patch": descriptor.requires_post_patch,
        "containment_required": descriptor.containment_required,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    payload["descriptor_identity"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def bind_validation_ids(validation_ids: Iterable[str]) -> dict[str, object]:
    ids = tuple(validation_ids)
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate validation descriptor")
    registry = validation_registry()
    if any(identifier not in registry for identifier in ids):
        raise ValueError("validation descriptor unknown or unauthorized")
    descriptors = [descriptor_binding(registry[identifier]) for identifier in ids]
    return {"authorized_validation_ids": list(ids), "descriptors": descriptors}


def binding_matches(contract: dict[str, object]) -> bool:
    try:
        ids = tuple(str(item) for item in contract["authorized_validation_ids"])
        return contract == bind_validation_ids(ids)
    except (KeyError, TypeError, ValueError):
        return False


def bound_descriptor_ids_by_role(contract: Mapping[str, object]) -> dict[ValidationRole, str]:
    """Resolve the exact evaluator-bound validation pair without a fallback."""

    material = dict(contract)
    if not binding_matches(material):
        raise ValueError("validation descriptor binding mismatch")
    descriptors = material.get("descriptors")
    if not isinstance(descriptors, list):
        raise ValueError("validation descriptor binding mismatch")
    resolved: dict[ValidationRole, str] = {}
    for item in descriptors:
        if not isinstance(item, dict):
            raise ValueError("validation descriptor binding mismatch")
        try:
            role = ValidationRole(str(item["role"]))
            descriptor_id = str(item["descriptor_id"])
        except (KeyError, ValueError) as error:
            raise ValueError("validation descriptor binding mismatch") from error
        if role in resolved:
            raise ValueError("validation descriptor role is ambiguous")
        resolved[role] = descriptor_id
    if set(resolved) != {ValidationRole.VISIBLE, ValidationRole.HIDDEN_ORACLE}:
        raise ValueError("visible and hidden validation descriptors are required")
    return resolved
