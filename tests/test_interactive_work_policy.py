from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.interactive_work_policy import (  # noqa: E402
    AWAITING_OPERATOR_REVIEW,
    DELIBERATIVE_OVERNIGHT_CODER,
    ENTRY_DENIED_REQUIREMENTS,
    ESCALATION_REQUIRED,
    INFRASTRUCTURE_REPAIR_REQUIRED,
    INTERACTIVE_AUTHORITY_MISJUDGMENT,
    INTERACTIVE_CANDIDATE_VALIDATED,
    INTERACTIVE_RECOVERY_FAILED,
    OPERATOR_CLARIFICATION_REQUIRED,
    REPAIR_OPPORTUNITY,
    VALIDATION_REQUIRED,
    InteractiveWorkPolicyError,
    bind_entry,
    classify,
)


def patch_rejected() -> dict:
    return {
        "request_type": "PROPOSE_PATCH",
        "authority_outcome": "PATCH_REJECTED",
        "projection": {"application": "PATCH_REJECTED"},
    }


class InteractiveWorkPolicyTests(unittest.TestCase):
    def test_entry_requires_operator_asserted_complete_requirements(self):
        with self.assertRaisesRegex(InteractiveWorkPolicyError, ENTRY_DENIED_REQUIREMENTS):
            bind_entry(
                requirements_status="UNRESOLVED",
                repository_count=1,
                objective_present=True,
                read_authority_present=True,
                patch_authority_declared=True,
                validation_configured=True,
                source_clean_and_frozen=True,
                runtime_accepted=True,
                bounded_adapter_only=True,
            )

    def test_complete_bounded_entry_records_every_gate_and_no_auto_handoff(self):
        binding = bind_entry(
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
        self.assertTrue(all(binding["gates"].values()))
        self.assertFalse(binding["automatic_cross_model_invocation"])

    def test_candidate_validation_and_one_forward_repair_are_normal_progression(self):
        accepted = classify(
            [{"request_type": "PROPOSE_PATCH", "authority_outcome": "AUTHORIZED"}],
            patch_authorized=True,
            candidate_exists=True,
            validation_status="VALIDATION_PASS",
        )
        self.assertEqual(AWAITING_OPERATOR_REVIEW, accepted.state)
        self.assertEqual(INTERACTIVE_CANDIDATE_VALIDATED, accepted.classification)

        repair = classify([patch_rejected()], patch_authorized=True)
        self.assertEqual(REPAIR_OPPORTUNITY, repair.state)

        repaired = classify(
            [patch_rejected(), {"request_type": "PROPOSE_PATCH", "authority_outcome": "AUTHORIZED"}],
            patch_authorized=True,
            candidate_exists=True,
            validation_status="VALIDATION_PASS",
        )
        self.assertEqual(AWAITING_OPERATOR_REVIEW, repaired.state)

        pending = classify(
            [{"request_type": "PROPOSE_PATCH", "authority_outcome": "AUTHORIZED"}],
            patch_authorized=True,
            candidate_exists=True,
            validation_status="VALIDATION_PENDING",
        )
        self.assertEqual(VALIDATION_REQUIRED, pending.state)

    def test_valid_clarification_pauses_for_operator(self):
        decision = classify(
            [{"request_type": "REQUEST_CLARIFICATION", "authority_outcome": "NO_EXECUTOR_ACTION"}],
            patch_authorized=True,
        )
        self.assertEqual(OPERATOR_CLARIFICATION_REQUIRED, decision.state)

    def test_patch_failure_limits_and_task10y_write_replay(self):
        exhausted = classify([patch_rejected(), patch_rejected()], patch_authorized=True)
        self.assertEqual(ESCALATION_REQUIRED, exhausted.state)
        self.assertEqual("PATCH_REPAIR_EXHAUSTED", exhausted.reason)

        historical = classify(
            [
                patch_rejected(),
                {"request_type": "NO_CHANGE", "authority_outcome": "NO_EXECUTOR_ACTION", "terminal_disposition": "NO_CHANGE"},
            ],
            patch_authorized=True,
        )
        self.assertEqual(ESCALATION_REQUIRED, historical.state)
        self.assertEqual(INTERACTIVE_RECOVERY_FAILED, historical.classification)
        self.assertEqual("NO_CHANGE_AFTER_PATCH_REJECTED", historical.reason)
        self.assertEqual(DELIBERATIVE_OVERNIGHT_CODER, historical.recommended_next_worker)

    def test_task10y_clarification_replay_uses_authority_as_primary_reason(self):
        decision = classify(
            [
                {"request_type": "SEARCH", "authority_outcome": "AUTHORIZED"},
                {"request_type": "READ", "authority_outcome": "AUTHORIZED"},
                {"request_type": "PROPOSE_PATCH", "authority_outcome": "DENIED_AUTHORITY"},
            ],
            patch_authorized=False,
        )
        self.assertEqual(ESCALATION_REQUIRED, decision.state)
        self.assertEqual(INTERACTIVE_AUTHORITY_MISJUDGMENT, decision.classification)
        self.assertEqual("AUTHORITY_MISJUDGMENT", decision.reason)
        self.assertIn("INTERACTIVE_REQUIREMENTS_JUDGMENT_FAILED", decision.secondary_evidence)

        denied_read = classify(
            [{"request_type": "READ", "authority_outcome": "DENIED_SCOPE"}],
            patch_authorized=True,
        )
        self.assertEqual((ESCALATION_REQUIRED, "AUTHORITY_MISJUDGMENT"), (
            denied_read.state, denied_read.reason,
        ))

    def test_repeat_limit_turn_limit_and_validation_failures_stay_distinct(self):
        repeat = classify(
            [{"classification": "MODEL_REPEAT_LIMIT", "terminal_disposition": "MODEL_REPEAT_LIMIT"}],
            patch_authorized=True,
        )
        self.assertEqual((ESCALATION_REQUIRED, "MODEL_REPEAT_LIMIT"), (repeat.state, repeat.reason))

        turn_limit = classify([], patch_authorized=True, turn_limit_reached=True)
        self.assertEqual((ESCALATION_REQUIRED, "TURN_LIMIT"), (turn_limit.state, turn_limit.reason))

        validation = classify(
            [{"request_type": "PROPOSE_PATCH", "authority_outcome": "AUTHORIZED"}],
            patch_authorized=True,
            candidate_exists=True,
            validation_status="VISIBLE_VALIDATION_FAIL",
        )
        self.assertEqual((ESCALATION_REQUIRED, "VALIDATION_FAILED"), (validation.state, validation.reason))

        infrastructure = classify(
            [], patch_authorized=True, validation_status="VALIDATION_CONTAINMENT_UNAVAILABLE"
        )
        self.assertEqual(INFRASTRUCTURE_REPAIR_REQUIRED, infrastructure.state)


if __name__ == "__main__":
    unittest.main()
