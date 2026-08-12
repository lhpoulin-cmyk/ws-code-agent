"""Frozen Task 11F production envelope and fail-closed pilot binding.

This module is supervisor authority only.  It does not start a session, invoke
a model, mutate a repository, or promote a candidate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

from .interactive_work_policy import (
    POLICY_ID as INTERACTIVE_WORK_POLICY_ID,
    bind_entry as bind_interactive_entry,
)
from .katra_ollama_backend import (
    QWEN25_MODEL_DIGEST,
    QWEN25_MODEL_QUANTIZATION,
    QWEN25_MODEL_TAG,
    QWEN25_RUNTIME_PROFILE,
)
from .request_protocol import (
    STRUCTURED_EDIT_PROTOCOL,
    STRUCTURED_EDIT_PROTOCOL_ID,
)
from .response_normalization import ADAPTER_ID, ADAPTER_VERSION
from .source_grounding import POLICY_ID as SOURCE_GROUNDING_POLICY_ID
from .supervised_validation import (
    WRITE_VALIDATION_IDS,
    bind_validation_ids,
    binding_matches,
)


ENVELOPE_ID = "INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1"
ENVELOPE_STATUS = "FROZEN"
WORK_ROLE = "INTERACTIVE_PRACTICAL_CODER"
PROTOCOL_RENDER_SHA256 = "d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993"
PILOT_POLICY_ID = "INTERACTIVE_PRACTICAL_CODER_REAL_REPOSITORY_PILOT_V1"
PILOT_DESIGN_STATUS = "DESIGN_READY"
PILOT_TARGET_PENDING = "REAL_REPOSITORY_PILOT_TARGET_PENDING_OPERATOR_SELECTION"
PILOT_NOT_RUN = "NOT_YET_RUN"
GENERAL_PRODUCTION_NOT_GRANTED = "NOT_YET_GRANTED"
PROMOTION_AUTHORITY = "OPERATOR_ONLY"
TURN_LIMIT = 8
TASK11J_PILOT_INSTANCE_PATH = Path(
    "docs/work/task11j-ws-doc-writer-real-repository-pilot-v1.json"
)
TASK11J_PILOT_INSTANCE_ID = "task11j-ws-doc-writer-src-readme-stale-boundary/v1"
TASK11J_TARGET_PATH = "/home/louis/src/ws-doc-writer"
TASK11J_TARGET_ORIGIN = "git@github.com:lhpoulin-cmyk/ws-doc-writer.git"
TASK11J_TARGET_BRANCH = "work/multi-backend-multi-model-v1-20260809"
TASK11J_TARGET_HEAD = "d52c923d4a13949a2345fb5791ee59a82d389c4e"
TASK11J_TARGET_SNAPSHOT = "6a4a913f0258a0e35c812d147ee2a5e4b1830684bfae56978e41911202d82047"
TASK11J_README_SHA256 = "a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970"

TASK11F_CHECKPOINT = "TASK11F-FRESH-V3-SOURCE-GROUNDED-INTERACTIVE-ACCEPTANCE"
TASK11F_DISPOSITION = "INTERACTIVE_PRACTICAL_CODER_V3_SOURCE_GROUNDED_ACCEPTANCE_PASS"
TASK11F_COMMIT = "762f5e21ddcaab09815679384240a8f75131023d"
TASK11F_EVIDENCE_PATH = "docs/experiments/task11f-source-grounded-v3-interactive-acceptance.md"
TASK11F_EVIDENCE_SHA256 = "83bcd7ebceae55ad4bb6f6da1fe8509694a73181cbd6e4134a7daa319462a660"
TASK11F_FIXTURE_ID = "task11f-source-grounded-structured-existing-file/synthetic-v1"
TASK11F_FIXTURE_CONTRACT_SHA256 = "2e11f5fac2952ee90dba867e129466a7f6b619c057a952348713035ddc33ed16"
TASK11F_SOURCE_SNAPSHOT_X = "b1e5f6c43fe763645bb62f349e42661b6f2402cf94d29cc405d10dcb160e297f"
TASK11F_CANDIDATE_IDENTITY = "ac813e35c939b2bfc64aaa4a5fd3237e284ca80fbd2dbaac351fe25ad755d7a5"
TASK11F_CANONICAL_DIFF_SHA256 = "52f56438548ceb2ae079583b4fb357d130d8adac1514510965ec1740c0a4389c"

WRITE_SCOPE = {
    "existing_file_only": True,
    "regular_file": True,
    "encoding": "UTF-8",
    "nul_allowed": False,
    "replacement": "EXACT_LITERAL",
    "old_text_non_empty": True,
    "required_occurrence_count": 1,
    "authorized_writable_file_count": 1,
}

EXCLUDED_CAPABILITIES = (
    "NEW_FILE_CREATION",
    "WHOLE_FILE_DELETION",
    "MULTIPLE_WRITABLE_FILES",
    "MULTI_REPOSITORY_WORK",
    "CROSS_REPOSITORY_EDITS",
    "FUZZY_MATCHING",
    "REGEX_REPLACEMENT",
    "REPLACE_ALL",
    "OCCURRENCE_SELECTION",
    "AST_REPAIR",
    "SEMANTIC_REPAIR",
    "REQUIREMENTS_DISCOVERY",
    "ARCHITECTURE_SELECTION",
    "UNRESOLVED_PRODUCT_AMBIGUITY",
    "SECURITY_POLICY_INTERPRETATION",
    "AUTOMATIC_PROMOTION",
    "AUTOMATIC_OVERNIGHT_CODER_INVOCATION",
)

PILOT_STOP_CONDITIONS = (
    "SOURCE_STATE_DRIFT",
    "AUTHORITY_DISAGREEMENT",
    "SOURCE_GROUNDING_NONCOMPLIANCE",
    "STRUCTURED_EDIT_REPAIR_EXHAUSTED",
    "VALIDATION_FAILED",
    "VALIDATION_INFRASTRUCTURE_FAILURE",
    "RUNTIME_BINDING_DRIFT",
    "UNEXPECTED_CHANGED_PATH",
    "CROSS_REPOSITORY_REQUEST",
    "TURN_LIMIT",
    "MODEL_REPEAT_LIMIT",
)

_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_HEAD = re.compile(r"[0-9a-f]{40,64}")


class PilotManifestError(RuntimeError):
    """A proposed real-repository pilot does not match the frozen envelope."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def acceptance_evidence(root: Path | None = None) -> dict[str, Any]:
    """Return the exact Task 11F evidence binding and verify its immutable file."""

    repository = root or Path(__file__).resolve().parents[2]
    evidence = repository / TASK11F_EVIDENCE_PATH
    if not evidence.is_file() or _sha256(evidence.read_bytes()) != TASK11F_EVIDENCE_SHA256:
        raise PilotManifestError("TASK11F_ACCEPTANCE_EVIDENCE_MISMATCH")
    return {
        "checkpoint": TASK11F_CHECKPOINT,
        "disposition": TASK11F_DISPOSITION,
        "commit": TASK11F_COMMIT,
        "evidence_path": TASK11F_EVIDENCE_PATH,
        "evidence_sha256": TASK11F_EVIDENCE_SHA256,
        "fixture_id": TASK11F_FIXTURE_ID,
        "fixture_contract_sha256": TASK11F_FIXTURE_CONTRACT_SHA256,
        "source_snapshot_x": TASK11F_SOURCE_SNAPSHOT_X,
        "candidate_identity": TASK11F_CANDIDATE_IDENTITY,
        "canonical_diff_sha256": TASK11F_CANONICAL_DIFF_SHA256,
        "behavior": (
            "WRITE_BEFORE_READ_DENIED",
            "EXACT_TARGET_READ",
            "SOURCE_GROUNDED",
            "SOURCE_ALIGNED_OLD_TEXT",
            "CORRECT_NEW_TEXT",
            "EXACT_MATCH_ONE",
            "STRUCTURED_EDIT_ACCEPTED",
            "VISIBLE_VALIDATION_PASS",
            "HIDDEN_VALIDATION_PASS",
            "AWAITING_OPERATOR_REVIEW",
        ),
    }


def frozen_envelope(root: Path | None = None) -> dict[str, Any]:
    """Build the exact, non-executing production envelope authority."""

    render_sha = _sha256(STRUCTURED_EDIT_PROTOCOL.render().encode("utf-8"))
    if render_sha != PROTOCOL_RENDER_SHA256:
        raise PilotManifestError("V3_PROTOCOL_RENDER_MISMATCH")
    return {
        "envelope_id": ENVELOPE_ID,
        "status": ENVELOPE_STATUS,
        "worker": {
            "work_role": WORK_ROLE,
            "model": QWEN25_MODEL_TAG,
            "manifest": QWEN25_MODEL_DIGEST,
            "quantization": QWEN25_MODEL_QUANTIZATION,
            "runtime_profile": QWEN25_RUNTIME_PROFILE.profile_id,
            "context": 4096,
            "placement": QWEN25_RUNTIME_PROFILE.policy_result,
            "minimum_gpu_percent": 100,
            "maximum_cpu_percent": 0,
        },
        "protocol": {
            "id": STRUCTURED_EDIT_PROTOCOL_ID,
            "render_sha256": render_sha,
            "write_primitive": "PROPOSE_TEXT_REPLACEMENT",
            "model_owned_values": ["path", "old_text", "new_text"],
            "model_generates_unified_diff": False,
        },
        "normalizer": {"id": ADAPTER_ID, "version": ADAPTER_VERSION},
        "source_grounding_policy": SOURCE_GROUNDING_POLICY_ID,
        "work_boundary_policy": INTERACTIVE_WORK_POLICY_ID,
        "write_scope": dict(WRITE_SCOPE),
        "repair_limits": {
            "ungrounded_write_consumes_match_repair": False,
            "grounded_match_failures_before_escalation": 2,
            "forward_match_repair_opportunities": 1,
            "consecutive_ungrounded_writes_before_escalation": 2,
        },
        "validation": {
            **bind_validation_ids(WRITE_VALIDATION_IDS),
            "both_required": True,
            "technical_correctness_required": "VALIDATED",
            "candidate_integrity_required": "MATCH",
            "source_snapshot_required": "MATCH",
        },
        "operator_boundary": {
            "success_state": "AWAITING_OPERATOR_REVIEW",
            "promotion_authority": PROMOTION_AUTHORITY,
            "automatic_commit": False,
            "automatic_source_mutation": False,
            "automatic_merge": False,
            "automatic_push": False,
            "automatic_deploy": False,
            "automatic_handoff": False,
        },
        "excluded_capabilities": EXCLUDED_CAPABILITIES,
        "acceptance": acceptance_evidence(root),
        "real_repository_pilot": PILOT_NOT_RUN,
        "general_production_use": GENERAL_PRODUCTION_NOT_GRANTED,
    }


def validate_pilot_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a future pilot packet without observing or mutating its repository."""

    required = {
        "pilot_id", "pilot_policy_id", "repository", "authority",
        "requirements_status", "objective", "read_scopes", "patch_paths",
        "validation", "worker_envelope_id", "runtime_profile", "protocol",
        "grounding_policy", "normalizer", "turn_limit", "promotion_authority",
    }
    if set(manifest) != required:
        raise PilotManifestError("PILOT_MANIFEST_FIELDS_MISMATCH")
    if not isinstance(manifest.get("pilot_id"), str) or not manifest["pilot_id"].strip():
        raise PilotManifestError("PILOT_ID_REQUIRED")
    if manifest.get("pilot_policy_id") != PILOT_POLICY_ID:
        raise PilotManifestError("PILOT_POLICY_MISMATCH")

    repository = manifest.get("repository")
    repository_fields = {
        "identity", "head", "source_snapshot_x", "index_identity",
        "tracked_worktree_identity", "untracked_identity", "clean", "frozen",
    }
    if not isinstance(repository, Mapping) or set(repository) != repository_fields:
        raise PilotManifestError("PILOT_REPOSITORY_BINDING_MISMATCH")
    if _SHA256.fullmatch(str(repository.get("identity"))) is None:
        raise PilotManifestError("PILOT_REPOSITORY_IDENTITY_INVALID")
    if _GIT_HEAD.fullmatch(str(repository.get("head"))) is None:
        raise PilotManifestError("PILOT_REPOSITORY_HEAD_INVALID")
    for field in (
        "source_snapshot_x", "index_identity", "tracked_worktree_identity",
        "untracked_identity",
    ):
        if _SHA256.fullmatch(str(repository.get(field))) is None:
            raise PilotManifestError("PILOT_REPOSITORY_STATE_INVALID")
    if repository.get("clean") is not True or repository.get("frozen") is not True:
        raise PilotManifestError("PILOT_SOURCE_NOT_CLEAN_AND_FROZEN")

    authority = manifest.get("authority")
    if not isinstance(authority, Mapping) or set(authority) != {
        "owning_domain", "authorization_reference",
    } or not all(isinstance(value, str) and value.strip() for value in authority.values()):
        raise PilotManifestError("PILOT_AUTHORITY_BINDING_MISMATCH")
    if manifest.get("requirements_status") != "COMPLETE":
        raise PilotManifestError("PILOT_REQUIREMENTS_UNRESOLVED")
    objective = manifest.get("objective")
    if not isinstance(objective, str) or not objective.strip() or len(objective.encode()) > 16_384:
        raise PilotManifestError("PILOT_OBJECTIVE_INVALID")

    read_scopes = manifest.get("read_scopes")
    patch_paths = manifest.get("patch_paths")
    if not isinstance(read_scopes, (list, tuple)) or not read_scopes:
        raise PilotManifestError("PILOT_READ_AUTHORITY_INVALID")
    if not all(_safe_relative(item, allow_dot=True) for item in read_scopes):
        raise PilotManifestError("PILOT_READ_AUTHORITY_INVALID")
    if not isinstance(patch_paths, (list, tuple)) or len(patch_paths) != 1:
        raise PilotManifestError("PILOT_REQUIRES_EXACTLY_ONE_WRITABLE_FILE")
    if not _safe_relative(patch_paths[0], allow_dot=False):
        raise PilotManifestError("PILOT_PATCH_AUTHORITY_INVALID")

    validation = manifest.get("validation")
    if not isinstance(validation, dict) or not binding_matches(validation):
        raise PilotManifestError("PILOT_VALIDATION_BINDING_MISMATCH")
    descriptors = validation.get("descriptors", [])
    if (
        len(validation.get("authorized_validation_ids", [])) != 2
        or [item.get("role") for item in descriptors] != ["VISIBLE", "HIDDEN_ORACLE"]
        or not all(item.get("containment_required") is True for item in descriptors)
        or not all(item.get("repository_writes_allowed") is False for item in descriptors)
    ):
        raise PilotManifestError("PILOT_VALIDATION_BINDING_MISMATCH")
    expected = frozen_envelope()
    exact_bindings = {
        "worker_envelope_id": ENVELOPE_ID,
        "runtime_profile": QWEN25_RUNTIME_PROFILE.profile_id,
        "protocol": {
            "id": expected["protocol"]["id"],
            "render_sha256": expected["protocol"]["render_sha256"],
        },
        "grounding_policy": SOURCE_GROUNDING_POLICY_ID,
        "normalizer": expected["normalizer"],
        "turn_limit": TURN_LIMIT,
        "promotion_authority": PROMOTION_AUTHORITY,
    }
    for key, value in exact_bindings.items():
        if manifest.get(key) != value:
            raise PilotManifestError("PILOT_FROZEN_BINDING_MISMATCH")

    return {
        "pilot_policy_id": PILOT_POLICY_ID,
        "pilot_design_status": PILOT_DESIGN_STATUS,
        "pilot_target_status": PILOT_TARGET_PENDING,
        "real_repository_pilot": PILOT_NOT_RUN,
        "pilot_id": manifest["pilot_id"],
        "manifest_status": "COMPLETE",
        "repository_binding": "PASS",
        "authority_binding": "PASS",
        "frozen_envelope_binding": "PASS",
        "source_protection_binding": "PASS",
        "validation_binding": "PASS",
        "promotion_authority": PROMOTION_AUTHORITY,
        "automatic_model_invocation": False,
        "automatic_promotion": False,
    }


def task11j_pilot_instance(root: Path | None = None) -> dict[str, Any]:
    """Load and verify the exact first local real-repository pilot packet."""

    repository = root or Path(__file__).resolve().parents[2]
    path = repository / TASK11J_PILOT_INSTANCE_PATH
    try:
        instance = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PilotManifestError("TASK11J_PILOT_INSTANCE_UNAVAILABLE") from error
    if set(instance) != {
        "schema_version", "pilot_instance_id", "checkpoint", "source_binding",
        "model_binding", "pilot_manifest",
    }:
        raise PilotManifestError("TASK11J_PILOT_INSTANCE_FIELDS_MISMATCH")
    if (
        instance.get("schema_version") != 1
        or instance.get("pilot_instance_id") != TASK11J_PILOT_INSTANCE_ID
        or instance.get("checkpoint") != "TASK11J-FIRST-REAL-LOCAL-REPOSITORY-V3-PILOT"
    ):
        raise PilotManifestError("TASK11J_PILOT_INSTANCE_IDENTITY_MISMATCH")
    source = instance.get("source_binding")
    expected_source = {
        "canonical_path": TASK11J_TARGET_PATH,
        "origin": TASK11J_TARGET_ORIGIN,
        "branch": TASK11J_TARGET_BRANCH,
        "remote_ref": f"refs/heads/{TASK11J_TARGET_BRANCH}",
        "readme_path": "src/README.md",
        "readme_sha256": TASK11J_README_SHA256,
        "submodule_identity": hashlib.sha256(b"").hexdigest(),
    }
    if source != expected_source:
        raise PilotManifestError("TASK11J_SOURCE_BINDING_MISMATCH")
    envelope = frozen_envelope(repository)
    expected_model = {
        "work_role": WORK_ROLE,
        "model": envelope["worker"]["model"],
        "manifest": envelope["worker"]["manifest"],
        "runtime_profile": envelope["worker"]["runtime_profile"],
        "context": envelope["worker"]["context"],
        "placement": envelope["worker"]["placement"],
    }
    if instance.get("model_binding") != expected_model:
        raise PilotManifestError("TASK11J_MODEL_BINDING_MISMATCH")
    pilot = instance.get("pilot_manifest")
    validated = validate_pilot_manifest(pilot)
    if (
        pilot.get("pilot_id") != TASK11J_PILOT_INSTANCE_ID
        or pilot.get("repository", {}).get("head") != TASK11J_TARGET_HEAD
        or pilot.get("repository", {}).get("source_snapshot_x") != TASK11J_TARGET_SNAPSHOT
        or pilot.get("read_scopes") != ["src/README.md"]
        or pilot.get("patch_paths") != ["src/README.md"]
    ):
        raise PilotManifestError("TASK11J_PILOT_BINDING_MISMATCH")
    return {**instance, "validation_result": validated}


def bind_pilot_entry(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Bind a complete packet to the existing boundary without starting work."""

    pilot = validate_pilot_manifest(manifest)
    boundary = bind_interactive_entry(
        requirements_status="COMPLETE",
        repository_count=1,
        objective_present=True,
        read_authority_present=True,
        patch_authority_declared=True,
        validation_configured=True,
        source_clean_and_frozen=True,
        runtime_accepted=True,
        bounded_adapter_only=True,
    )
    return {
        **pilot,
        "entry_status": boundary["entry_status"],
        "work_boundary_policy": boundary["policy_id"],
        "source_grounding_policy": SOURCE_GROUNDING_POLICY_ID,
        "write_scope": dict(WRITE_SCOPE),
        "stop_conditions": PILOT_STOP_CONDITIONS,
    }


def _safe_relative(value: object, *, allow_dot: bool) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or (path.parts and path.parts[0] == ".git"):
        return False
    if path.as_posix() == ".":
        return allow_dot
    return bool(path.parts)
