from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.production_envelope import (  # noqa: E402
    ENVELOPE_ID,
    PROTOCOL_RENDER_SHA256,
    TASK11M_PILOT_INSTANCE_ID,
    TASK11M_TARGET_FILE,
    TASK11M_TARGET_FILE_SHA256,
    TASK11M_TARGET_HEAD,
    TASK11M_TARGET_ORIGIN,
    TASK11M_TARGET_PATH,
    task11m_pilot_instance,
)
from ws_code_agent.supervised_validation import (  # noqa: E402
    TASK11M_HIDDEN_SOURCE,
    TASK11M_VALIDATION_IDS,
    TASK11M_VISIBLE_SOURCE,
    bind_validation_ids,
    bound_descriptor_ids_by_role,
)


OLD = b"- Ollama `0.32.0` enabled only after CUDA smoke passed\n"
NEW = b"- Ollama `0.32.0+helix.repeatlimit.1` enabled only after CUDA smoke passed\n"


class Task11MRealMidfilePilotTests(unittest.TestCase):
    def test_instance_binds_distinct_clean_gpu_compute_target(self):
        instance = task11m_pilot_instance(ROOT)
        self.assertEqual(TASK11M_PILOT_INSTANCE_ID, instance["pilot_instance_id"])
        source = instance["source_binding"]
        self.assertEqual(TASK11M_TARGET_PATH, source["canonical_path"])
        self.assertEqual(TASK11M_TARGET_ORIGIN, source["origin"])
        self.assertEqual(TASK11M_TARGET_FILE, source["target_path"])
        pilot = instance["pilot_manifest"]
        self.assertEqual(TASK11M_TARGET_HEAD, pilot["repository"]["head"])
        self.assertEqual([TASK11M_TARGET_FILE], pilot["read_scopes"])
        self.assertEqual([TASK11M_TARGET_FILE], pilot["patch_paths"])
        self.assertEqual(ENVELOPE_ID, pilot["worker_envelope_id"])
        self.assertEqual(PROTOCOL_RENDER_SHA256, pilot["protocol"]["render_sha256"])
        self.assertEqual("COMPLETE", instance["validation_result"]["manifest_status"])
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

    def test_task_is_midfile_and_whole_file_replacement_only_fails(self):
        source = Path(TASK11M_TARGET_PATH, TASK11M_TARGET_FILE).read_bytes()
        self.assertEqual(TASK11M_TARGET_FILE_SHA256, hashlib.sha256(source).hexdigest())
        self.assertEqual(1, source.count(OLD))
        prefix, suffix = source.split(OLD, 1)
        self.assertGreater(len(prefix), 1000)
        self.assertGreater(len(suffix), 1000)
        correct = prefix + NEW + suffix
        self.assertNotEqual(correct, NEW)
        self.assertNotEqual(hashlib.sha256(NEW).hexdigest(), hashlib.sha256(correct).hexdigest())

    def test_requirement_is_proven_by_repository_local_pinned_runtime(self):
        repository = Path(TASK11M_TARGET_PATH)
        runbook = (repository / "docs/runbooks/ollama-repeat-terminalization.md").read_text()
        config = (repository / "config/ollama-v0.32.0-repeat-terminalization.yaml").read_text()
        self.assertIn("0.32.0+helix.repeatlimit.1", runbook)
        self.assertIn("version_string: 0.32.0+helix.repeatlimit.1", config)

    def test_generation_method_records_exact_unchanged_request_fields(self):
        transport = Path(
            TASK11M_TARGET_PATH, "bin/ollama-machine-response"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '{"model": model, "prompt": prompt, "stream": False}',
            transport,
        )
        payload_block = transport.split("payload = json.dumps(", 1)[1].split(
            ").encode(\"utf-8\")", 1
        )[0]
        for option in ("seed", "temperature", "top_p", "top_k"):
            self.assertNotIn(f'"{option}"', payload_block)

    def test_validators_are_separately_implemented_and_exactly_bound(self):
        contract = bind_validation_ids(TASK11M_VALIDATION_IDS)
        visible, hidden = contract["descriptors"]
        self.assertEqual(("VISIBLE", "HIDDEN_ORACLE"), (visible["role"], hidden["role"]))
        self.assertNotEqual(visible["source_sha256"], hidden["source_sha256"])
        roles = bound_descriptor_ids_by_role(contract)
        self.assertEqual(set(TASK11M_VALIDATION_IDS), set(roles.values()))
        for descriptor in contract["descriptors"]:
            self.assertTrue(descriptor["containment_required"])
            self.assertFalse(descriptor["repository_writes_allowed"])

    def test_direct_validator_calibration_matrix(self):
        source = Path(TASK11M_TARGET_PATH, TASK11M_TARGET_FILE).read_bytes()
        prefix, suffix = source.split(OLD, 1)
        expected = prefix + NEW + suffix
        cases = (
            (expected, False, 0),
            (source, False, 1),
            (NEW, False, 1),
            (NEW + suffix, False, 1),
            (prefix + NEW, False, 1),
            (expected + b"\nOther.\n", False, 1),
            (prefix + NEW.replace(b"repeatlimit.1", b"repeatlimit.2") + suffix, False, 1),
            (expected, True, 1),
        )
        for candidate, second_change, expected_code in cases:
            with self.subTest(candidate=hashlib.sha256(candidate).hexdigest(), second=second_change):
                with tempfile.TemporaryDirectory() as temporary:
                    repository = Path(temporary)
                    (repository / "CURRENT_STATE.md").write_bytes(source)
                    (repository / "README.md").write_text("# Control\n")
                    subprocess.run(["git", "-C", temporary, "init", "-q"], check=True)
                    subprocess.run(["git", "-C", temporary, "add", "."], check=True)
                    subprocess.run([
                        "git", "-C", temporary, "-c", "user.name=Test", "-c",
                        "user.email=test@example.invalid", "commit", "-qm", "source",
                    ], check=True)
                    (repository / "CURRENT_STATE.md").write_bytes(candidate)
                    if second_change:
                        (repository / "README.md").write_text("# Changed\n")
                    for asset in (TASK11M_VISIBLE_SOURCE, TASK11M_HIDDEN_SOURCE):
                        process = subprocess.run(
                            [sys.executable, "-B", str(asset)], cwd=repository,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                        )
                        self.assertEqual(expected_code, process.returncode, process.stderr)

    def test_selector_is_explicit_without_model_visible_scope_coaching(self):
        cli = (ROOT / "tools/run_supervised_work.py").read_text(encoding="utf-8")
        controller = (ROOT / "src/ws_code_agent/supervised_work.py").read_text(encoding="utf-8")
        objective = task11m_pilot_instance(ROOT)["pilot_manifest"]["objective"]
        self.assertIn('sub.add_parser("start-task11m-real-midfile-pilot")', cli)
        self.assertIn("start_task11m_real_repository_pilot", controller)
        self.assertNotIn("whole file", objective.lower())
        self.assertNotIn("smallest", objective.lower())
        self.assertNotIn("prefix", objective.lower())
        self.assertNotIn("suffix", objective.lower())


if __name__ == "__main__":
    unittest.main()
