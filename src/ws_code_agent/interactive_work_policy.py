"""Supervisor-owned boundary for the interactive/practical coder.

The policy in this module is deliberately downstream of model generation.  It
classifies durable executor and validation facts; it does not alter prompts,
requests, authority, or candidate effects.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


POLICY_ID = "INTERACTIVE_BOUNDED_WORK_V1"
WORK_ROLE = "INTERACTIVE_PRACTICAL_CODER"
REQUIREMENTS_COMPLETE = "COMPLETE"
ENTRY_ACCEPTED = "INTERACTIVE_ENTRY_ACCEPTED"
ENTRY_DENIED_REQUIREMENTS = "INTERACTIVE_ENTRY_DENIED_REQUIREMENTS_UNRESOLVED"

CONTINUE = "CONTINUE"
REPAIR_OPPORTUNITY = "REPAIR_OPPORTUNITY"
VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
AWAITING_OPERATOR_REVIEW = "AWAITING_OPERATOR_REVIEW"
OPERATOR_CLARIFICATION_REQUIRED = "OPERATOR_CLARIFICATION_REQUIRED"
ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
INFRASTRUCTURE_REPAIR_REQUIRED = "INFRASTRUCTURE_REPAIR_REQUIRED"

INTERACTIVE_CANDIDATE_VALIDATED = "INTERACTIVE_CANDIDATE_VALIDATED"
INTERACTIVE_RECOVERY_FAILED = "INTERACTIVE_RECOVERY_FAILED"
INTERACTIVE_AUTHORITY_MISJUDGMENT = "INTERACTIVE_AUTHORITY_MISJUDGMENT"
INTERACTIVE_REQUIREMENTS_JUDGMENT_FAILED = "INTERACTIVE_REQUIREMENTS_JUDGMENT_FAILED"
INTERACTIVE_STRUCTURED_EDIT_RECOVERY_FAILED = "INTERACTIVE_STRUCTURED_EDIT_RECOVERY_FAILED"

DELIBERATIVE_OVERNIGHT_CODER = "DELIBERATIVE_OVERNIGHT_CODER"
OPERATOR = "OPERATOR"
DELIBERATIVE_OVERNIGHT_CODER_OR_OPERATOR = "DELIBERATIVE_OVERNIGHT_CODER_OR_OPERATOR"

ESCALATION_REASONS = (
    "PATCH_REPAIR_EXHAUSTED",
    "STRUCTURED_EDIT_REPAIR_EXHAUSTED",
    "NO_CHANGE_AFTER_PATCH_REJECTED",
    "AUTHORITY_MISJUDGMENT",
    "REQUIREMENTS_JUDGMENT_FAILED",
    "TURN_LIMIT",
    "MODEL_REPEAT_LIMIT",
    "VALIDATION_FAILED",
    "OTHER_SEMANTIC_FAILURE",
)

_VALIDATION_FAILURES = {"VISIBLE_VALIDATION_FAIL", "HIDDEN_VALIDATION_FAIL"}
_INFRASTRUCTURE_FAILURES = {
    "VALIDATION_UNAVAILABLE",
    "VALIDATION_TIMEOUT",
    "VALIDATION_CONTAINMENT_UNAVAILABLE",
    "EFFECT_VIOLATION",
    "EXECUTOR_ERROR",
}


class InteractiveWorkPolicyError(RuntimeError):
    """An entry assertion does not satisfy the interactive work contract."""


@dataclass(frozen=True)
class PolicyDecision:
    state: str
    classification: str
    reason: str | None = None
    recommended_next_worker: str | None = None
    secondary_evidence: tuple[str, ...] = ()

    def evidence(self) -> dict[str, Any]:
        return asdict(self)


def bind_entry(
    *,
    requirements_status: str,
    repository_count: int,
    objective_present: bool,
    read_authority_present: bool,
    patch_authority_declared: bool,
    validation_configured: bool,
    source_clean_and_frozen: bool,
    runtime_accepted: bool,
    bounded_adapter_only: bool,
) -> dict[str, Any]:
    """Fail closed unless every operator-owned entry assertion is present."""

    if requirements_status != REQUIREMENTS_COMPLETE:
        raise InteractiveWorkPolicyError(ENTRY_DENIED_REQUIREMENTS)
    gates = {
        "single_repository": repository_count == 1,
        "explicit_objective": objective_present,
        "explicit_read_authority": read_authority_present,
        "explicit_patch_authority": patch_authority_declared,
        "validation_descriptors_configured": validation_configured,
        "source_snapshot_clean_and_frozen": source_clean_and_frozen,
        "accepted_artifact_runtime_profile": runtime_accepted,
        "bounded_representation_adapter_only": bounded_adapter_only,
    }
    failed = [name for name, passed in gates.items() if not passed]
    if failed:
        raise InteractiveWorkPolicyError("INTERACTIVE_ENTRY_DENIED_" + failed[0].upper())
    return {
        "policy_id": POLICY_ID,
        "work_role": WORK_ROLE,
        "requirements_status": requirements_status,
        "entry_status": ENTRY_ACCEPTED,
        "gates": gates,
        "automatic_cross_model_invocation": False,
    }


def classify(
    turns: Sequence[Mapping[str, Any]],
    *,
    patch_authorized: bool,
    candidate_exists: bool = False,
    validation_status: str = "VALIDATION_NOT_CONFIGURED",
    turn_limit_reached: bool = False,
) -> PolicyDecision:
    """Classify durable facts without interpreting or repairing model text."""

    if validation_status in _INFRASTRUCTURE_FAILURES:
        return PolicyDecision(
            INFRASTRUCTURE_REPAIR_REQUIRED,
            validation_status,
            recommended_next_worker=OPERATOR,
        )

    if any(
        item.get("terminal_disposition") == "MODEL_REPEAT_LIMIT"
        or item.get("classification") == "MODEL_REPEAT_LIMIT"
        for item in turns
    ):
        return _escalate("MODEL_REPEAT_LIMIT", "MODEL_REPEAT_LIMIT")

    if any(item.get("authority_outcome") in {
        "STATE_STALE", "REPOSITORY_MISMATCH", "EXECUTOR_ERROR",
    } for item in turns):
        return PolicyDecision(
            INFRASTRUCTURE_REPAIR_REQUIRED,
            next(item["authority_outcome"] for item in turns if item.get("authority_outcome") in {
                "STATE_STALE", "REPOSITORY_MISMATCH", "EXECUTOR_ERROR",
            }),
            recommended_next_worker=OPERATOR,
        )

    authority_violation = any(
        (
            item.get("request_type") in {"PROPOSE_PATCH", "PROPOSE_TEXT_REPLACEMENT"} and not patch_authorized
        )
        or item.get("authority_outcome") in {
            "DENIED_AUTHORITY",
            "DENIED_SCOPE",
            "FORBIDDEN_RECORDED",
            "SUPERVISION_REQUIRED_CROSS_REPOSITORY",
        }
        for item in turns
    )
    if authority_violation:
        secondary = (
            (INTERACTIVE_REQUIREMENTS_JUDGMENT_FAILED,)
            if not patch_authorized
            else ()
        )
        return _escalate(
            INTERACTIVE_AUTHORITY_MISJUDGMENT,
            "AUTHORITY_MISJUDGMENT",
            secondary_evidence=secondary,
        )

    if any(item.get("request_type") == "REQUEST_CLARIFICATION" for item in turns):
        return PolicyDecision(
            OPERATOR_CLARIFICATION_REQUIRED,
            "VALID_REQUEST_CLARIFICATION",
            recommended_next_worker=OPERATOR,
        )

    structured_failures = [
        index for index, item in enumerate(turns)
        if item.get("authority_outcome") in {"TEXT_MATCH_ZERO", "TEXT_MATCH_MULTIPLE"}
        or item.get("projection", {}).get("application") in {"TEXT_MATCH_ZERO", "TEXT_MATCH_MULTIPLE"}
    ]
    if len(structured_failures) >= 2:
        return _escalate(
            INTERACTIVE_STRUCTURED_EDIT_RECOVERY_FAILED,
            "STRUCTURED_EDIT_REPAIR_EXHAUSTED",
        )
    if structured_failures:
        later = turns[structured_failures[0] + 1:]
        if later:
            if later[0].get("request_type") != "PROPOSE_TEXT_REPLACEMENT":
                return _escalate(
                    INTERACTIVE_STRUCTURED_EDIT_RECOVERY_FAILED,
                    "OTHER_SEMANTIC_FAILURE",
                )
        else:
            return PolicyDecision(REPAIR_OPPORTUNITY, "FIRST_STRUCTURED_MATCH_FAILURE")

    if any(item.get("authority_outcome") in {
        "TEXT_REPLACEMENT_NO_EFFECT", "TEXT_ENCODING_UNSUPPORTED",
    } for item in turns):
        return _escalate("INTERACTIVE_SEMANTIC_FAILURE", "OTHER_SEMANTIC_FAILURE")

    rejected_indexes = [
        index for index, item in enumerate(turns)
        if item.get("authority_outcome") == "PATCH_REJECTED"
        or item.get("projection", {}).get("application") == "PATCH_REJECTED"
    ]
    if len(rejected_indexes) >= 2:
        return _escalate(INTERACTIVE_RECOVERY_FAILED, "PATCH_REPAIR_EXHAUSTED")
    if rejected_indexes:
        later = turns[rejected_indexes[0] + 1:]
        if later:
            if later[0].get("request_type") == "NO_CHANGE":
                return _escalate(
                    INTERACTIVE_RECOVERY_FAILED,
                    "NO_CHANGE_AFTER_PATCH_REJECTED",
                )
            if later[0].get("request_type") != "PROPOSE_PATCH":
                return _escalate(INTERACTIVE_RECOVERY_FAILED, "OTHER_SEMANTIC_FAILURE")
        else:
            return PolicyDecision(REPAIR_OPPORTUNITY, "FIRST_PATCH_REJECTED")

    if candidate_exists:
        if validation_status == "VALIDATION_PASS":
            return PolicyDecision(
                AWAITING_OPERATOR_REVIEW,
                INTERACTIVE_CANDIDATE_VALIDATED,
                recommended_next_worker=OPERATOR,
            )
        if validation_status in _VALIDATION_FAILURES:
            return _escalate("INTERACTIVE_VALIDATION_FAILED", "VALIDATION_FAILED")
        return PolicyDecision(VALIDATION_REQUIRED, "CANDIDATE_READY")

    if not patch_authorized and any(
        item.get("request_type") in {"NO_CHANGE", "PROPOSE_PATCH", "PROPOSE_TEXT_REPLACEMENT"} for item in turns
    ):
        return _escalate(
            INTERACTIVE_REQUIREMENTS_JUDGMENT_FAILED,
            "REQUIREMENTS_JUDGMENT_FAILED",
        )

    if turns and turns[-1].get("terminal_disposition") in {
        "MALFORMED_REQUEST",
        "NO_CHANGE",
    }:
        return _escalate("INTERACTIVE_SEMANTIC_FAILURE", "OTHER_SEMANTIC_FAILURE")

    if turn_limit_reached:
        return _escalate("INTERACTIVE_TURN_LIMIT", "TURN_LIMIT")
    return PolicyDecision(CONTINUE, "ORDINARY_INTERACTIVE_PROGRESSION")


def _escalate(
    classification: str,
    reason: str,
    *,
    secondary_evidence: tuple[str, ...] = (),
) -> PolicyDecision:
    if reason not in ESCALATION_REASONS:
        raise ValueError("unknown escalation reason")
    return PolicyDecision(
        ESCALATION_REQUIRED,
        classification,
        reason,
        DELIBERATIVE_OVERNIGHT_CODER,
        secondary_evidence,
    )
