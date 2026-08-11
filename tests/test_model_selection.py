from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.request_protocol import VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL  # noqa: E402


class ModelSelectionTests(unittest.TestCase):
    def test_devstral_challenger_is_runtime_accepted_without_admission(self):
        matrix = (ROOT / "models/candidate-matrix.yaml").read_text(encoding="utf-8")
        selection = matrix.split("selected_challenger:\n", 1)[1].split("\nkatra:\n", 1)[0]
        required = (
            "  id: devstral-small-2-q4",
            "  status: SELECTED_FOR_EVALUATION",
            "  ollama_tag: devstral-small-2:24b-instruct-2512-q4_K_M",
            "  manifest_digest: 24277f07f62db8f9cb68e9dfc679ea1818a7fbac47a50eff0a701d3f645b63c8",
            "  quantization: Q4_K_M",
            "  comparison_context: 4096",
            "    temperature: 0.15",
            "  local_install_state: NOT_INSTALLED_AT_SELECTION",
            "  expected_katra_fit: PARTIAL_OFFLOAD_EXPECTED",
            "  runtime_acceptance: RUNTIME_ACCEPTED",
            "  runtime_profile_id: devstral-small-2-24b-katra-partial",
            "  accepted_gpu_minimum_percent: 88",
            "  accepted_cpu_maximum_percent: 12",
            "  production_admission: PENDING",
            "  alpha_qualification: NOT_EVALUATED",
        )
        self.assertTrue(all(value in selection for value in required))
        self.assertNotIn("QUALIFIED", selection.replace("NOT_QUALIFIED", ""))
        self.assertNotIn("ADMITTED", selection.replace("NOT_ADMITTED", ""))
        candidate = (ROOT / "docs/qualification/devstral-small-2-v2-admission-candidate.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("status: RUNTIME_ACCEPTED", candidate)
        self.assertIn("production_admission: PENDING", candidate)
        self.assertEqual(
            "3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e",
            hashlib.sha256(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.render().encode()).hexdigest(),
        )
        evidence = (ROOT / "docs/experiments/task10m-devstral-challenger-selection.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("1. runtime/artifact acceptance on Katra", evidence)
        self.assertIn("2. V2 synthetic write admission", evidence)
        self.assertIn("3. V2 synthetic clarification admission", evidence)


if __name__ == "__main__":
    unittest.main()
