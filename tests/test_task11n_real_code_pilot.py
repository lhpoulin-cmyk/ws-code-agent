from __future__ import annotations

import hashlib
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.production_envelope import (  # noqa: E402
    ENVELOPE_ID,
    PROTOCOL_RENDER_SHA256,
    TASK11J_TARGET_HEAD,
    TASK11J_TARGET_ORIGIN,
    TASK11J_TARGET_PATH,
    TASK11N_PILOT_INSTANCE_ID,
    TASK11N_TARGET_FILE,
    TASK11N_TARGET_FILE_SHA256,
    task11n_pilot_instance,
)
from ws_code_agent.supervised_validation import (  # noqa: E402
    TASK11N_HIDDEN_SOURCE,
    TASK11N_VALIDATION_IDS,
    TASK11N_VISIBLE_SOURCE,
    bind_validation_ids,
    bound_descriptor_ids_by_role,
)
from tools.calibrate_task11n_validation import source_cases  # noqa: E402


class Task11NRealCodePilotTests(unittest.TestCase):
    def test_instance_binds_distinct_clean_executable_code_target(self):
        instance = task11n_pilot_instance(ROOT)
        self.assertEqual(TASK11N_PILOT_INSTANCE_ID, instance["pilot_instance_id"])
        source = instance["source_binding"]
        self.assertEqual(TASK11J_TARGET_PATH, source["canonical_path"])
        self.assertEqual(TASK11J_TARGET_ORIGIN, source["origin"])
        self.assertEqual(TASK11N_TARGET_FILE, source["target_path"])
        self.assertTrue(TASK11N_TARGET_FILE.endswith(".py"))
        pilot = instance["pilot_manifest"]
        self.assertEqual(TASK11J_TARGET_HEAD, pilot["repository"]["head"])
        self.assertEqual([TASK11N_TARGET_FILE], pilot["read_scopes"])
        self.assertEqual([TASK11N_TARGET_FILE], pilot["patch_paths"])
        self.assertEqual(ENVELOPE_ID, pilot["worker_envelope_id"])
        self.assertEqual(PROTOCOL_RENDER_SHA256, pilot["protocol"]["render_sha256"])
        self.assertEqual("COMPLETE", instance["validation_result"]["manifest_status"])

    def test_observed_defect_and_requirement_are_repository_local(self):
        repository = Path(TASK11J_TARGET_PATH)
        target = repository / TASK11N_TARGET_FILE
        self.assertEqual(TASK11N_TARGET_FILE_SHA256, hashlib.sha256(target.read_bytes()).hexdigest())
        from_form = runpy.run_path(str(target))["from_form"]
        standard = "Preserve ambiguity and draft without guessing"
        custom = "Ask the operator which timeline applies."
        self.assertEqual(
            standard,
            from_form({
                "clarification_policy": standard,
                "clarification_policy_custom": custom,
            }).clarification_policy,
        )
        design = (repository / "docs/writing-setup-explicit-intent-design.md").read_text()
        app = (repository / "src/docwriter_web/app.py").read_text()
        self.assertIn("Writing setup is operator intent", design)
        self.assertIn("Custom policy", app)
        self.assertIn("only when a standard choice does not fit", app)

    def test_generation_method_records_exact_unchanged_request_fields(self):
        instance = task11n_pilot_instance(ROOT)
        self.assertEqual(
            {
                "request_fields": ["model", "prompt", "stream"],
                "stream": False,
                "seed_override": "ABSENT",
                "temperature_override": "ABSENT",
                "top_p_override": "ABSENT",
                "top_k_override": "ABSENT",
                "other_generation_overrides": [],
                "interpretation": "OBSERVED_REPRODUCIBILITY",
            },
            instance["generation_method"],
        )

    def test_validators_are_separately_implemented_and_exactly_bound(self):
        contract = bind_validation_ids(TASK11N_VALIDATION_IDS)
        visible, hidden = contract["descriptors"]
        self.assertEqual(("VISIBLE", "HIDDEN_ORACLE"), (visible["role"], hidden["role"]))
        self.assertNotEqual(visible["source_sha256"], hidden["source_sha256"])
        roles = bound_descriptor_ids_by_role(contract)
        self.assertEqual(set(TASK11N_VALIDATION_IDS), set(roles.values()))
        for descriptor in contract["descriptors"]:
            self.assertTrue(descriptor["containment_required"])
            self.assertFalse(descriptor["repository_writes_allowed"])

    def test_direct_validator_calibration_matrix(self):
        source = Path(TASK11J_TARGET_PATH, TASK11N_TARGET_FILE).read_bytes()
        for name, (candidate, second_change, expected) in source_cases().items():
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory() as temporary:
                    repository = Path(temporary)
                    target = repository / TASK11N_TARGET_FILE
                    target.parent.mkdir(parents=True)
                    target.write_bytes(source)
                    (repository / "README.md").write_text("# Control\n")
                    subprocess.run(["git", "-C", temporary, "init", "-q"], check=True)
                    subprocess.run(["git", "-C", temporary, "add", "."], check=True)
                    subprocess.run([
                        "git", "-C", temporary, "-c", "user.name=Test", "-c",
                        "user.email=test@example.invalid", "commit", "-qm", "source",
                    ], check=True)
                    target.write_bytes(candidate)
                    if second_change:
                        (repository / "README.md").write_text("# Changed\n")
                    expected_code = 0 if expected.value == "VALIDATION_PASS" else 1
                    for asset in (TASK11N_VISIBLE_SOURCE, TASK11N_HIDDEN_SOURCE):
                        process = subprocess.run(
                            [sys.executable, "-B", str(asset)], cwd=repository,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                        )
                        self.assertEqual(expected_code, process.returncode, process.stderr)

    def test_selector_is_explicit_without_model_visible_scope_coaching(self):
        cli = (ROOT / "tools/run_supervised_work.py").read_text(encoding="utf-8")
        controller = (ROOT / "src/ws_code_agent/supervised_work.py").read_text(encoding="utf-8")
        objective = task11n_pilot_instance(ROOT)["pilot_manifest"]["objective"].lower()
        self.assertIn('sub.add_parser("start-task11n-real-code-pilot")', cli)
        self.assertIn("start_task11n_real_code_pilot", controller)
        self.assertNotIn("smallest", objective)
        self.assertNotIn("whole file", objective)
        self.assertNotIn("task 11", objective)


if __name__ == "__main__":
    unittest.main()
