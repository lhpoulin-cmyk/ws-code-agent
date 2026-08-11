from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.request_protocol import VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL  # noqa: E402


class ModelSelectionTests(unittest.TestCase):
    def test_devstral_challenger_has_settled_failed_admission_without_retry(self):
        matrix = (ROOT / "models/candidate-matrix.yaml").read_text(encoding="utf-8")
        candidate = matrix.split("  - id: devstral-small-2-q4\n", 1)[1].split("\n  - id:", 1)[0]
        required = (
            "    status: EVALUATION_COMPLETE",
            "      status: RUNTIME_ACCEPTED",
            "      production_admission: FAIL",
            "      write: FAIL",
            "      clarification: PASS",
            "      observed_model_outcome: MODEL_REPEAT_LIMIT",
            "      repeat_limit_terminalization_defect: REPAIRED_GOVERNED",
            "      admission_retry: NOT_AUTHORIZED",
        )
        self.assertTrue(all(value in candidate for value in required))
        self.assertEqual(
            "3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e",
            hashlib.sha256(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.render().encode()).hexdigest(),
        )

    def test_gpt_oss_control_is_ineligible_for_exact_4096_seam(self):
        matrix = (ROOT / "models/candidate-matrix.yaml").read_text(encoding="utf-8")
        selection = matrix.split("selected_challenger:\n", 1)[1].split("\nkatra:\n", 1)[0]
        self.assertIn("  id: UNRESOLVED", selection)
        self.assertIn("  status: NEXT_SELECTION_REQUIRED", selection)
        self.assertIn("  evaluated_candidate: gpt-oss-20b-mxfp4", selection)
        self.assertIn("  context_classification: GPT_OSS_CONTEXT_MINIMUM_EXCEEDS_4096", selection)
        self.assertIn("  comparison_context: 4096", selection)
        self.assertIn("  enforced_minimum_context: 8192", selection)
        candidate = matrix.split("  - id: gpt-oss-20b-mxfp4\n", 1)[1].split("\n  - id:", 1)[0]
        required = (
            "    status: INELIGIBLE_FROZEN_COMPARISON_SEAM",
            "    role: CONTROL",
            "ollama-manifest-digest:17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7",
            "sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb",
            "      model_layer_bytes: 13793422144",
            "    quantization: MXFP4",
            "    comparison_context: 4096",
            "    enforced_minimum_context: 8192",
            "    context_classification: GPT_OSS_CONTEXT_MINIMUM_EXCEEDS_4096",
            "      temperature: 1",
            "      status: COMPATIBLE",
            "      interface: PLAIN_MACHINE_RESPONSE_COMPATIBLE",
            "    local_install_state: NOT_INSTALLED",
            "    expected_katra_fit: GPU_PRIMARY_PARTIAL_OFFLOAD_EXPECTED",
        )
        self.assertTrue(all(value in candidate for value in required))
        self.assertNotIn("SELECTED_FOR_EVALUATION", candidate)
        self.assertNotIn("RUNTIME_ACCEPTED", candidate)
        self.assertNotIn("PRODUCTION_ADMITTED", candidate)
        evidence = (ROOT / "docs/experiments/task10o-gpt-oss-control-selection.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("GPT_OSS_CONTEXT_MINIMUM_EXCEEDS_4096", evidence)
        self.assertIn("NEXT_MODEL_CANDIDATE = UNRESOLVED", evidence)
        self.assertIn("NEXT: SELECT NEXT ELIGIBLE CHALLENGER", evidence)


if __name__ == "__main__":
    unittest.main()
