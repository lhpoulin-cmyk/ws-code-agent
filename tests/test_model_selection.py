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

    def test_qwen25_coder_14b_runtime_remains_accepted_and_admission_is_failed(self):
        matrix = (ROOT / "models/candidate-matrix.yaml").read_text(encoding="utf-8")
        candidate = matrix.split("  - id: qwen25-coder-14b-q4\n", 1)[1].split("\n  - id:", 1)[0]
        required_candidate = (
            "    practical_coding_baseline: true",
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
            "    production_admission: FAIL",
            "    qualification: NOT_EVALUATED",
            "      status: FAIL",
            "      write: FAIL",
            "      write_terminal: MALFORMED_REQUEST",
            "      write_semantic_behavior: PLAUSIBLE_AUTHORIZED_PROPOSE_PATCH",
            "      write_protocol_behavior: MARKDOWN_FENCED_OUTPUT",
            "      clarification: FAIL",
            "      clarification_terminal: MALFORMED_REQUEST",
            "      clarification_semantic_behavior: NO_CHANGE_INSTEAD_OF_REQUEST_CLARIFICATION",
            "      clarification_protocol_behavior: MARKDOWN_FENCED_OUTPUT",
            "      model_inferences: 2",
            "      practical_coding_baseline: YES",
            "      runtime_accepted: YES",
            "      full_gpu_on_katra: YES",
            "      strict_v2_production_admission: FAIL",
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
        admission_evidence = (
            ROOT / "docs/experiments/task10r-qwen25-coder-14b-v2-admission.md"
        ).read_text(encoding="utf-8")
        self.assertIn("QWEN25_CODER_14B_V2_PRODUCTION_ADMISSION_FAIL", admission_evidence)
        self.assertIn("WRITE_FAIL", admission_evidence)
        self.assertIn("CLARIFICATION_FAIL", admission_evidence)
        self.assertIn("NEXT: SELECT NEXT ELIGIBLE CHALLENGER", admission_evidence)

    def test_qwen25_coder_32b_runtime_is_accepted_as_exact_scale_control(self):
        matrix = (ROOT / "models/candidate-matrix.yaml").read_text(encoding="utf-8")
        selection = matrix.split("selected_challenger:\n", 1)[1].split("\nkatra:\n", 1)[0]
        required_selection = (
            "  id: qwen25-coder-32b-q4",
            "  role: INTRA_FAMILY_SCALE_CONTROL",
            "  status: RUNTIME_ACCEPTED",
            "  ollama_tag: qwen2.5-coder:32b-instruct-q4_K_M",
            "  manifest_digest: b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41",
            "  model_layer_digest: ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9",
            "  model_layer_bytes: 19851336384",
            "  comparison_context: 4096",
            "  context_classification: QWEN25_CODER_32B_CONTEXT_4096_COMPATIBLE",
            "  artifact_generation_defaults: NONE_SPECIFIED",
            "  acquisition_state: ACQUIRED_EXACT_ARTIFACT",
            "  expected_katra_fit: GPU_PRIMARY_PARTIAL_OFFLOAD_EXPECTED",
            "  empirical_katra_fit: GPU_PRIMARY_PARTIAL_OFFLOAD",
            "    status: RUNTIME_ACCEPTED",
            "    profile_id: qwen25-coder-32b-katra-4096",
            "    implementation_checkpoint: 282cffabfa165b9d9906a35a9372cb077bdf6153",
            "    policy_acceptance_checkpoint: e64e39c029616d69ec4523500facd20e7a75c9f2",
            "    execution: GPU_PRIMARY_PARTIAL_OFFLOAD",
            "    processor_envelope: {minimum_gpu_percent: 71, maximum_cpu_percent: 29}",
            "    observed_vram_mib: 14634",
            "    effective_context: 4096",
            "    status: APPARATUS_READY",
            "    session_kind: QWEN25_32B_V2_SUPERVISED_PRODUCTION_ADMISSION",
            "    operator_command: start-qwen25-32b-v2",
            "    backend: Qwen25_32BKatraOllamaDispositionBackend",
            "    model_visible_first_turn_equivalence: PASS",
            "  production_admission: NOT_EVALUATED",
        )
        self.assertTrue(all(value in selection for value in required_selection))
        candidate = matrix.split("  - id: qwen25-coder-32b-q4\n", 1)[1].split("\n  - id:", 1)[0]
        required_candidate = (
            "    status: RUNTIME_ACCEPTED",
            "    role: INTRA_FAMILY_SCALE_CONTROL",
            "ollama-manifest-digest:b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41",
            "sha256:f0676bd3c336a0f995e270c5e2c80ce09aa5cfcab0c59ff574088eca52da32ee",
            "sha256:ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9",
            "      model_layer_bytes: 19851336384",
            "sha256:1e65450c30670713aa47fe23e8b9662bdf4065e81cc8e3cbfaa98924fcc0d320",
            "      parameters_layer: ABSENT",
            "    parameter_class: 32.8B artifact / 32.5B upstream",
            "    architecture: dense / qwen2",
            "    quantization: Q4_K_M",
            "    resolved_context_metadata: 32768",
            "    context_classification: QWEN25_CODER_32B_CONTEXT_4096_COMPATIBLE",
            "      artifact_overrides: NONE_SPECIFIED",
            "      exact_14b_system_layer_match: true",
            "      exact_14b_template_layer_match: true",
            "      interface: PLAIN_MACHINE_RESPONSE_COMPATIBLE",
            "      model_specific_adaptation: NOT_REQUIRED",
            "    acquisition_state: ACQUIRED_EXACT_ARTIFACT",
            "    expected_katra_fit: GPU_PRIMARY_PARTIAL_OFFLOAD_EXPECTED",
            "    empirical_katra_fit: GPU_PRIMARY_PARTIAL_OFFLOAD",
            "      status: RUNTIME_ACCEPTED",
            "      profile_id: qwen25-coder-32b-katra-4096",
            "      implementation_checkpoint: 282cffabfa165b9d9906a35a9372cb077bdf6153",
            "      policy_acceptance_checkpoint: e64e39c029616d69ec4523500facd20e7a75c9f2",
            "      execution: GPU_PRIMARY_PARTIAL_OFFLOAD",
            "      processor_envelope: {minimum_gpu_percent: 71, maximum_cpu_percent: 29}",
            "      observed_vram_mib: 14634",
            "      effective_context: 4096",
            "      neutral_probes: 3",
            "      terminality: NORMAL_STOP_ALL_PROBES",
            "      model_repeat_limit: NOT_OBSERVED",
            "      status: APPARATUS_READY",
            "      session_kind: QWEN25_32B_V2_SUPERVISED_PRODUCTION_ADMISSION",
            "      operator_command: start-qwen25-32b-v2",
            "      backend: Qwen25_32BKatraOllamaDispositionBackend",
            "      digest_selector: EXACT_FULL_MANIFEST",
            "      model_visible_first_turn_equivalence: PASS",
            "    production_admission: NOT_EVALUATED",
        )
        self.assertTrue(all(value in candidate for value in required_candidate))
        self.assertNotIn("PRODUCTION_ADMITTED", candidate)
        evidence = (
            ROOT / "docs/experiments/task10s-qwen25-coder-32b-scale-control-selection.md"
        ).read_text(encoding="utf-8")
        self.assertIn("QWEN25_CODER_32B_CONTEXT_4096_COMPATIBLE", evidence)
        self.assertIn("NEXT_MODEL_CANDIDATE = qwen25-coder-32b-q4", evidence)
        self.assertIn("ROLE = INTRA_FAMILY_SCALE_CONTROL", evidence)
        self.assertIn("NEXT: RUN QWEN2.5-CODER 32B ARTIFACT/RUNTIME ACCEPTANCE", evidence)
        runtime_evidence = (
            ROOT / "docs/experiments/task10t-qwen25-coder-32b-runtime-acceptance.md"
        ).read_text(encoding="utf-8")
        self.assertIn("QWEN25_CODER_32B_RUNTIME_ACCEPTED", runtime_evidence)
        self.assertIn("GPU_PRIMARY_PARTIAL_OFFLOAD", runtime_evidence)
        self.assertIn(
            "NEXT: BIND QWEN2.5-CODER 32B SCALE CONTROL TO FROZEN V2 ADMISSION SEAM",
            runtime_evidence,
        )
        binding_evidence = (
            ROOT / "docs/experiments/task10u-qwen25-coder-32b-v2-binding.md"
        ).read_text(encoding="utf-8")
        self.assertIn("TASK10U_32B_ADMISSION_APPARATUS_READY", binding_evidence)
        self.assertIn("MODEL_VISIBLE_FIRST_TURN_EQUIVALENCE = PASS", binding_evidence)
        self.assertEqual(
            "3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e",
            hashlib.sha256(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.render().encode()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
