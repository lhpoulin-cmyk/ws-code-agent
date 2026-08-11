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

    def test_qwen25_coder_14b_runtime_is_accepted_for_exact_4096_seam(self):
        matrix = (ROOT / "models/candidate-matrix.yaml").read_text(encoding="utf-8")
        selection = matrix.split("selected_challenger:\n", 1)[1].split("\nkatra:\n", 1)[0]
        required_selection = (
            "  id: qwen25-coder-14b-q4",
            "  status: RUNTIME_ACCEPTED",
            "  ollama_tag: qwen2.5-coder:14b-instruct-q4_K_M",
            "  manifest_digest: 9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849",
            "  comparison_context: 4096",
            "  context_classification: QWEN25_CODER_14B_CONTEXT_4096_COMPATIBLE",
            "  artifact_generation_defaults: NONE_SPECIFIED",
            "  acquisition_state: ACQUIRED_EXACT_ARTIFACT",
            "  expected_katra_fit: FULL_GPU_CANDIDATE",
            "  empirical_katra_fit: FULL_GPU",
            "    status: RUNTIME_ACCEPTED",
            "    profile_id: qwen25-coder-14b-katra-4096",
            "    implementation_checkpoint: fc514cb02c9a2f76c60b461f787fba9ee43e2364",
            "    policy_acceptance_checkpoint: a84c33f68dcb14b292d791c8485e0ec4e532852c",
            "    execution: GPU_ONLY",
            "    effective_context: 4096",
            "  production_admission: NOT_EVALUATED",
        )
        self.assertTrue(all(value in selection for value in required_selection))
        candidate = matrix.split("  - id: qwen25-coder-14b-q4\n", 1)[1].split("\n  - id:", 1)[0]
        required_candidate = (
            "sha256:0578f229f23ad620e123654fd0b4708405e7af3629ec1aecf3f553f54e06bc40",
            "sha256:ac9bc7a69dab38da1c790838955f1293420b55ab555ef6b4615efa1c1507b1ed",
            "      model_layer_bytes: 8988110784",
            "sha256:1e65450c30670713aa47fe23e8b9662bdf4065e81cc8e3cbfaa98924fcc0d320",
            "      parameters_layer: ABSENT",
            "    architecture: dense / qwen2",
            "    quantization: Q4_K_M",
            "    resolved_context_metadata: 32768",
            "    context_classification: QWEN25_CODER_14B_CONTEXT_4096_COMPATIBLE",
            "      interface: PLAIN_MACHINE_RESPONSE_COMPATIBLE",
            "    expected_katra_fit: FULL_GPU_CANDIDATE",
            "    empirical_katra_fit: FULL_GPU",
            "      status: RUNTIME_ACCEPTED",
            "      profile_id: qwen25-coder-14b-katra-4096",
            "      execution: GPU_ONLY",
            "      observed_vram_mib: 9304",
            "      effective_context: 4096",
            "      neutral_probes: 3",
            "      terminality: NORMAL_STOP_ALL_PROBES",
            "      model_repeat_limit: NOT_OBSERVED",
            "    production_admission: NOT_EVALUATED",
        )
        self.assertTrue(all(value in candidate for value in required_candidate))
        self.assertNotIn("PRODUCTION_ADMITTED", candidate)
        qwen3 = matrix.split("  - id: qwen3-coder-30b-q4\n", 1)[1].split("\n  - id:", 1)[0]
        self.assertIn("      supervised_production_admission: NOT_ADMITTED", qwen3)
        evidence = (ROOT / "docs/experiments/task10p-qwen25-coder-14b-selection.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("QWEN25_CODER_14B_CONTEXT_4096_COMPATIBLE", evidence)
        self.assertIn("NEXT_MODEL_CANDIDATE = qwen25-coder-14b-q4", evidence)
        self.assertIn("NEXT: RUN QWEN2.5-CODER 14B ARTIFACT/RUNTIME ACCEPTANCE", evidence)
        runtime_evidence = (
            ROOT / "docs/experiments/task10q-qwen25-coder-14b-runtime-acceptance.md"
        ).read_text(encoding="utf-8")
        self.assertIn("QWEN25_CODER_14B_RUNTIME_ACCEPTED", runtime_evidence)
        self.assertIn("NEXT: RUN QWEN2.5-CODER 14B V2 PRODUCTION ADMISSION", runtime_evidence)


if __name__ == "__main__":
    unittest.main()
