from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.interactive_work_policy import POLICY_ID as WORK_POLICY_ID  # noqa: E402
from ws_code_agent.production_envelope import (  # noqa: E402
    ENVELOPE_ID,
    ENVELOPE_STATUS,
    EXCLUDED_CAPABILITIES,
    GENERAL_PRODUCTION_NOT_GRANTED,
    PILOT_NOT_RUN,
    PILOT_POLICY_ID,
    PILOT_STOP_CONDITIONS,
    PILOT_TARGET_PENDING,
    PROTOCOL_RENDER_SHA256,
    PilotManifestError,
    acceptance_evidence,
    bind_pilot_entry,
    frozen_envelope,
    validate_pilot_manifest,
)
from ws_code_agent.request_protocol import (  # noqa: E402
    STRUCTURED_EDIT_PROTOCOL,
    VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL,
)
from ws_code_agent.response_normalization import ADAPTER_ID, ADAPTER_VERSION  # noqa: E402
from ws_code_agent.source_grounding import POLICY_ID as GROUNDING_POLICY_ID  # noqa: E402
from ws_code_agent.supervised_validation import WRITE_VALIDATION_IDS, bind_validation_ids  # noqa: E402


def valid_manifest() -> dict:
    envelope = frozen_envelope(ROOT)
    return {
        "pilot_id": "pilot-boring-existing-file-v1",
        "pilot_policy_id": PILOT_POLICY_ID,
        "repository": {
            "identity": "1" * 64,
            "head": "2" * 40,
            "source_snapshot_x": "3" * 64,
            "index_identity": "4" * 64,
            "tracked_worktree_identity": "5" * 64,
            "untracked_identity": "6" * 64,
            "clean": True,
            "frozen": True,
        },
        "authority": {
            "owning_domain": "example-repository-owner",
            "authorization_reference": "operator-approved-pilot-reference",
        },
        "requirements_status": "COMPLETE",
        "objective": "Change one existing constant to the approved value.",
        "read_scopes": ["."],
        "patch_paths": ["src/existing.py"],
        "validation": bind_validation_ids(WRITE_VALIDATION_IDS),
        "worker_envelope_id": ENVELOPE_ID,
        "runtime_profile": envelope["worker"]["runtime_profile"],
        "protocol": {
            "id": envelope["protocol"]["id"],
            "render_sha256": envelope["protocol"]["render_sha256"],
        },
        "grounding_policy": GROUNDING_POLICY_ID,
        "normalizer": envelope["normalizer"],
        "turn_limit": 8,
        "promotion_authority": "OPERATOR_ONLY",
    }


class ProductionEnvelopeTests(unittest.TestCase):
    def test_envelope_freezes_exact_task11f_worker_and_surfaces(self):
        envelope = frozen_envelope(ROOT)
        self.assertEqual((ENVELOPE_ID, ENVELOPE_STATUS), (
            envelope["envelope_id"], envelope["status"],
        ))
        self.assertEqual("qwen2.5-coder:14b-instruct-q4_K_M", envelope["worker"]["model"])
        self.assertEqual(
            "9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849",
            envelope["worker"]["manifest"],
        )
        self.assertEqual("qwen25-coder-14b-katra-4096", envelope["worker"]["runtime_profile"])
        self.assertEqual(("GPU_ONLY", 100, 0, 4096), (
            envelope["worker"]["placement"],
            envelope["worker"]["minimum_gpu_percent"],
            envelope["worker"]["maximum_cpu_percent"],
            envelope["worker"]["context"],
        ))
        self.assertEqual(PROTOCOL_RENDER_SHA256, envelope["protocol"]["render_sha256"])
        self.assertEqual((ADAPTER_ID, ADAPTER_VERSION), (
            envelope["normalizer"]["id"], envelope["normalizer"]["version"],
        ))
        self.assertEqual(GROUNDING_POLICY_ID, envelope["source_grounding_policy"])
        self.assertEqual(WORK_POLICY_ID, envelope["work_boundary_policy"])
        self.assertEqual(PILOT_NOT_RUN, envelope["real_repository_pilot"])
        self.assertEqual(GENERAL_PRODUCTION_NOT_GRANTED, envelope["general_production_use"])

    def test_task11f_acceptance_file_and_terminal_identities_are_exact(self):
        evidence = acceptance_evidence(ROOT)
        self.assertEqual(
            "INTERACTIVE_PRACTICAL_CODER_V3_SOURCE_GROUNDED_ACCEPTANCE_PASS",
            evidence["disposition"],
        )
        self.assertEqual("762f5e21ddcaab09815679384240a8f75131023d", evidence["commit"])
        self.assertEqual(
            "ac813e35c939b2bfc64aaa4a5fd3237e284ca80fbd2dbaac351fe25ad755d7a5",
            evidence["candidate_identity"],
        )
        self.assertEqual("AWAITING_OPERATOR_REVIEW", evidence["behavior"][-1])

    def test_v1_is_exactly_one_existing_utf8_file_and_excludes_broadening(self):
        envelope = frozen_envelope(ROOT)
        scope = envelope["write_scope"]
        self.assertTrue(scope["existing_file_only"] and scope["regular_file"])
        self.assertEqual(("UTF-8", False, "EXACT_LITERAL", 1, 1), (
            scope["encoding"], scope["nul_allowed"], scope["replacement"],
            scope["required_occurrence_count"], scope["authorized_writable_file_count"],
        ))
        for excluded in (
            "NEW_FILE_CREATION", "MULTIPLE_WRITABLE_FILES", "MULTI_REPOSITORY_WORK",
            "FUZZY_MATCHING", "REGEX_REPLACEMENT", "SEMANTIC_REPAIR",
            "AUTOMATIC_PROMOTION", "AUTOMATIC_OVERNIGHT_CODER_INVOCATION",
        ):
            self.assertIn(excluded, EXCLUDED_CAPABILITIES)

    def test_validation_and_operator_boundary_are_fail_closed(self):
        envelope = frozen_envelope(ROOT)
        validation = envelope["validation"]
        self.assertEqual(list(WRITE_VALIDATION_IDS), validation["authorized_validation_ids"])
        self.assertTrue(validation["both_required"])
        self.assertEqual("VALIDATED", validation["technical_correctness_required"])
        operator = envelope["operator_boundary"]
        self.assertEqual("AWAITING_OPERATOR_REVIEW", operator["success_state"])
        self.assertTrue(all(operator[key] is False for key in (
            "automatic_commit", "automatic_source_mutation", "automatic_merge",
            "automatic_push", "automatic_deploy", "automatic_handoff",
        )))

    def test_complete_pilot_manifest_binds_without_starting_or_promoting(self):
        manifest = valid_manifest()
        validated = validate_pilot_manifest(manifest)
        self.assertEqual("COMPLETE", validated["manifest_status"])
        self.assertEqual(PILOT_TARGET_PENDING, validated["pilot_target_status"])
        self.assertEqual(PILOT_NOT_RUN, validated["real_repository_pilot"])
        self.assertFalse(validated["automatic_model_invocation"])
        self.assertFalse(validated["automatic_promotion"])
        entry = bind_pilot_entry(manifest)
        self.assertEqual("INTERACTIVE_ENTRY_ACCEPTED", entry["entry_status"])
        self.assertEqual(WORK_POLICY_ID, entry["work_boundary_policy"])
        self.assertEqual(GROUNDING_POLICY_ID, entry["source_grounding_policy"])
        self.assertEqual(PILOT_STOP_CONDITIONS, entry["stop_conditions"])

    def test_pilot_manifest_rejects_incomplete_or_substituted_authority(self):
        cases = []
        missing = valid_manifest()
        missing.pop("authority")
        cases.append(missing)
        incomplete = valid_manifest()
        incomplete["requirements_status"] = "UNRESOLVED"
        cases.append(incomplete)
        multiple = valid_manifest()
        multiple["patch_paths"] = ["src/existing.py", "src/other.py"]
        cases.append(multiple)
        traversal = valid_manifest()
        traversal["patch_paths"] = ["../outside.py"]
        cases.append(traversal)
        stale = valid_manifest()
        stale["repository"]["frozen"] = False
        cases.append(stale)
        runtime = valid_manifest()
        runtime["runtime_profile"] = "substituted-profile"
        cases.append(runtime)
        protocol = valid_manifest()
        protocol["protocol"]["render_sha256"] = "0" * 64
        cases.append(protocol)
        validation = valid_manifest()
        validation["validation"] = {"authorized_validation_ids": [], "descriptors": []}
        cases.append(validation)
        for manifest in cases:
            with self.subTest(manifest=manifest):
                with self.assertRaises(PilotManifestError):
                    validate_pilot_manifest(manifest)

    def test_protocols_are_frozen_and_no_model_visible_example_is_added(self):
        self.assertEqual(
            PROTOCOL_RENDER_SHA256,
            hashlib.sha256(STRUCTURED_EDIT_PROTOCOL.render().encode()).hexdigest(),
        )
        self.assertEqual(
            "3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e",
            hashlib.sha256(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.render().encode()).hexdigest(),
        )
        for populated in ("src/message.py", 'return \"hi\"', 'return \"hello\"'):
            self.assertNotIn(populated, STRUCTURED_EDIT_PROTOCOL.render())

    def test_pending_target_is_explicit_and_no_repository_is_fabricated(self):
        self.assertEqual(
            "REAL_REPOSITORY_PILOT_TARGET_PENDING_OPERATOR_SELECTION",
            PILOT_TARGET_PENDING,
        )
        self.assertIn("SOURCE_STATE_DRIFT", PILOT_STOP_CONDITIONS)
        self.assertIn("MODEL_REPEAT_LIMIT", PILOT_STOP_CONDITIONS)

    def test_durable_envelope_and_pilot_policy_match_code_authority(self):
        envelope_doc = yaml.safe_load(
            (ROOT / "docs/work/interactive-v3-production-envelope-v1.yaml").read_text()
        )
        pilot_doc = yaml.safe_load(
            (ROOT / "docs/work/interactive-v3-real-repository-pilot-v1.yaml").read_text()
        )
        envelope = frozen_envelope(ROOT)
        self.assertEqual((ENVELOPE_ID, ENVELOPE_STATUS), (
            envelope_doc["envelope_id"], envelope_doc["status"],
        ))
        self.assertEqual(envelope["worker"], envelope_doc["worker"])
        self.assertEqual(envelope["protocol"], envelope_doc["protocol"])
        self.assertEqual(envelope["write_scope"], envelope_doc["write_scope"])
        self.assertEqual(list(EXCLUDED_CAPABILITIES), envelope_doc["excluded_capabilities"])
        self.assertEqual(
            {
                "task10x", "task11a", "task11b", "task11c",
                "task11d", "task11e", "task11f",
            },
            set(envelope_doc["failure_lineage"]),
        )
        self.assertEqual(
            "SOURCE_GROUNDED_V3_ACCEPTANCE_PASS",
            envelope_doc["failure_lineage"]["task11f"],
        )
        self.assertEqual(PILOT_POLICY_ID, pilot_doc["pilot_policy_id"])
        self.assertEqual(PILOT_TARGET_PENDING, pilot_doc["target_status"])
        self.assertEqual(list(PILOT_STOP_CONDITIONS), pilot_doc["stop_conditions"])
        self.assertEqual(PILOT_NOT_RUN, pilot_doc["real_repository_pilot"])

    def test_candidate_matrix_and_qualification_bind_frozen_not_general_state(self):
        matrix = (ROOT / "models/candidate-matrix.yaml").read_text()
        candidate = matrix.split("  - id: qwen25-coder-14b-q4\n", 1)[1].split("\n  - id:", 1)[0]
        qualification = yaml.safe_load(
            (ROOT / "docs/qualification/qwen25-coder-14b-v2-admission-candidate.yaml").read_text()
        )
        required = (
            "envelope_id: INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1",
            "status: FROZEN",
            "real_repository_pilot: NOT_YET_RUN",
            "pilot_target: REAL_REPOSITORY_PILOT_TARGET_PENDING_OPERATOR_SELECTION",
            "general_production_use: NOT_YET_GRANTED",
            "promotion_authority: OPERATOR_ONLY",
            "model_inferences_14b: 0",
            "model_inferences_32b: 0",
            "historical_rescore: false",
        )
        self.assertTrue(all(value in candidate for value in required))
        frozen = qualification["production_envelope"]
        self.assertEqual(ENVELOPE_ID, frozen["envelope_id"])
        self.assertEqual(ENVELOPE_STATUS, frozen["status"])
        self.assertEqual(PILOT_NOT_RUN, frozen["real_repository_pilot"])
        self.assertEqual(GENERAL_PRODUCTION_NOT_GRANTED, frozen["general_production_use"])


if __name__ == "__main__":
    unittest.main()
