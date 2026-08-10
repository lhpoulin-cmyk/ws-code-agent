from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.alpha_case_adapters import (  # noqa: E402
    ADAPTERS,
    C01Adapter,
    TASK10G_R3_CASE_ORDER,
    initialize_task10g_r3,
    process_case_turn,
)
from ws_code_agent.alpha_experiment import AlphaExperimentController, ExperimentError  # noqa: E402
from ws_code_agent.contained_validation import ContainedExecution  # noqa: E402
from ws_code_agent.katra_ollama_backend import (  # noqa: E402
    KatraOllamaDispositionBackend,
    RuntimeTurnEvidence,
)
from ws_code_agent.request_protocol import SINGLE_REPOSITORY_PROTOCOL_ID  # noqa: E402


def request(kind: str, arguments: dict) -> str:
    return json.dumps({"request_type": kind, "arguments": arguments}, separators=(",", ":"))


C01_PATCH = """diff --git a/src/parity.py b/src/parity.py
--- a/src/parity.py
+++ b/src/parity.py
@@ -1,3 +1,3 @@
 def is_even(number: int) -> bool:
     \"\"\"Return whether number is even.\"\"\"
-    return number % 2 == 1
+    return number % 2 == 0
"""


class FakeContainedRunner:
    def run(self, context, descriptor):
        evidence = {
            "CONTAINMENT_MECHANISM": "fake-system-manager",
            "CONTAINMENT_PROFILE": "task10a-systemd-v2",
            "CONTAINMENT_UNIT": f"fake-{descriptor.descriptor_id}",
            "CONTAINMENT_UID_GID": "1000:1000",
            "CONTAINMENT_NETWORK": "AF_UNIX-only",
            "CONTAINMENT_RESULT": "read-only",
        }
        if descriptor.descriptor_id == "C01-oracle":
            evidence.update({"CONTAINMENT_ORACLE_PROJECTION": "single-artifact-directory",
                             "CONTAINMENT_ORACLE_SHA256": "fixture-digest"})
        return ContainedExecution(0, b"ok\n", b"", evidence)


class QueueBackend:
    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls = 0
        self.protocol_ids: list[str] = []

    def invocation_for(self, messages, invocation_id, *, protocol):
        return KatraOllamaDispositionBackend.invocation_for(messages, invocation_id, protocol=protocol)

    def generate(self, messages, *, protocol, invocation, evidence_sink):
        self.calls += 1
        self.protocol_ids.append(protocol.protocol_id)
        raw = self.replies.pop(0)
        evidence_sink.capture_response(raw, RuntimeTurnEvidence(
            hashlib.sha256(raw.encode()).hexdigest(), f"job-{self.calls}", "digest", "Q4_K_M",
            "gpu-primary-partial", "GPU_PRIMARY_PARTIAL_OFFLOAD", 20, 80,
            "20%/80% CPU/GPU", "", "",
        ))
        return raw


def start(root: Path) -> AlphaExperimentController:
    return initialize_task10g_r3(root, {
        "experiment_id": "family",
        "experiment_harness_sha": "test",
        "case_order": list(TASK10G_R3_CASE_ORDER),
        "protocols": {case: SINGLE_REPOSITORY_PROTOCOL_ID for case in TASK10G_R3_CASE_ORDER},
    })


class SixCaseAdapterTests(unittest.TestCase):
    def setUp(self):
        self.original_c01 = ADAPTERS["C01"]
        ADAPTERS["C01"] = C01Adapter(FakeContainedRunner())

    def tearDown(self):
        ADAPTERS["C01"] = self.original_c01

    def test_c01_restart_preserves_feedback_effect_and_validation(self):
        replies = [
            request("READ", {"path": "src/parity.py"}),
            request("PROPOSE_PATCH", {"patch": "not a diff", "proposed_paths": ["src/parity.py"]}),
            request("PROPOSE_PATCH", {"patch": C01_PATCH, "proposed_paths": ["src/parity.py"]}),
        ]
        backend = QueueBackend(replies)
        with tempfile.TemporaryDirectory() as temporary:
            controller = start(Path(temporary))
            snapshot_x = controller._case("C01")["snapshot_x"]
            controller.step_registered("C01", backend)
            controller = AlphaExperimentController(controller.root)
            rejected = controller.step_registered("C01", backend)
            self.assertEqual("REJECTED", rejected["projection"]["status"])
            self.assertIn("executor_feedback", rejected["projection"])
            controller = AlphaExperimentController(controller.root)
            accepted = controller.step_registered("C01", backend)
            self.assertEqual("ACCEPTED", accepted["projection"]["status"])
            self.assertEqual("EVALUATING", controller._case("C01")["case_status"])
            controller = AlphaExperimentController(controller.root)
            self.assertEqual("VISIBLE_COMPLETE", controller.step_registered("C01", backend)["evaluation_phase"])
            controller = AlphaExperimentController(controller.root)
            completed = controller.step_registered("C01", backend)
            self.assertEqual("PASS", completed["technical_validation"])
            case = controller._case("C01")
            self.assertEqual(snapshot_x, case["snapshot_x"])
            self.assertEqual(1, len(case["case_state"]["accepted_effects"]))
            self.assertEqual("COMPLETE", case["case_state"]["validation"]["phase"])
            self.assertIsNotNone(case["case_state"]["validation"]["visible_evidence_sha256"])
            self.assertIsNotNone(case["case_state"]["validation"]["hidden_evidence_sha256"])
            self.assertEqual(3, backend.calls)
            source = Path(snapshot_x["canonical_root"], "src/parity.py").read_text()
            self.assertIn("number % 2 == 1", source)
            hidden = (controller.root / "cases/C01/evaluator/hidden.json").read_text()
            self.assertNotIn("alpha-private", hidden)
            self.assertNotIn("oracle.py", hidden)

    def test_c02_restart_captures_exact_clarification_and_private_reference_only(self):
        question = "Should labels be display uppercase or stable slug identifiers?"
        backend = QueueBackend([
            request("SEARCH", {"literal": "format_release_label", "scope": "src"}),
            request("READ", {"path": "src/release_label.py"}),
            request("REQUEST_CLARIFICATION", {"question": question}),
        ])
        with tempfile.TemporaryDirectory() as temporary:
            controller = start(Path(temporary))
            snapshot_x = controller._case("C02")["snapshot_x"]
            for _ in range(3):
                controller.step("C02", backend, lambda case, raw: process_case_turn(controller, case, raw))
                controller = AlphaExperimentController(controller.root)
            case = controller._case("C02")
            self.assertEqual(snapshot_x, case["snapshot_x"])
            self.assertEqual("REQUEST_CLARIFICATION", case["terminal_disposition"])
            self.assertEqual(question, case["case_state"]["clarification"]["text"])
            self.assertEqual("PENDING_REVIEW", case["case_state"]["evaluator"]["status"])
            public = json.dumps({"conversation": case["conversation"], "status": controller.status(),
                                 "fixture": case["fixture_identity"]})
            self.assertNotIn("uppercase-versus-slug", public)
            self.assertNotIn("alpha-private", public)
            self.assertEqual(3, backend.calls)

    def test_c02_patch_denial_and_malformed_clarification_remain_strict(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = start(Path(temporary))
            denied = controller.step("C02", QueueBackend([
                request("PROPOSE_PATCH", {"patch": C01_PATCH, "proposed_paths": ["src/parity.py"]})
            ]), lambda case, raw: process_case_turn(controller, case, raw))
            self.assertEqual("DENIED_AUTHORITY", denied["authority_outcome"])
        with tempfile.TemporaryDirectory() as temporary:
            controller = start(Path(temporary))
            malformed = controller.step("C02", QueueBackend([
                '{"request_type":"REQUEST_CLARIFICATION","arguments":{"question":[]}}'
            ]), lambda case, raw: process_case_turn(controller, case, raw))
            self.assertEqual("MALFORMED_REQUEST", malformed["terminal_disposition"])

    def test_six_case_registry_progresses_across_controller_restarts(self):
        backend = QueueBackend([
            request("PROPOSE_PATCH", {"patch": C01_PATCH, "proposed_paths": ["src/parity.py"]}),
            request("REQUEST_CLARIFICATION", {"question": "Which public label representation is intended?"}),
            request("NO_CHANGE", {}), request("NO_CHANGE", {}),
            request("NO_CHANGE", {}), request("NO_CHANGE", {}),
        ])
        with tempfile.TemporaryDirectory() as temporary:
            controller = start(Path(temporary))
            controller.step_registered("C01", backend)
            controller = AlphaExperimentController(controller.root)
            controller.step_registered("C01", backend)
            controller = AlphaExperimentController(controller.root)
            controller.step_registered("C01", backend)
            self.assertEqual("TERMINAL", controller._case("C01")["case_status"])
            controller = AlphaExperimentController(controller.root)
            controller.step_registered("C02", backend)
            self.assertEqual("TERMINAL", controller._case("C02")["case_status"])
            controller = AlphaExperimentController(controller.root)
            for case_id in ("C03", "C04", "C05-A", "C05-B"):
                controller.step_registered(case_id, backend)
                controller = AlphaExperimentController(controller.root)
            self.assertEqual("COMPLETE", controller.status()["family_status"])
            self.assertEqual(list(TASK10G_R3_CASE_ORDER),
                             json.loads((controller.root / "family-state.json").read_text())["case_order"])
            self.assertEqual(6, backend.calls)
            self.assertEqual([SINGLE_REPOSITORY_PROTOCOL_ID] * 4,
                             backend.protocol_ids[:4])

    def test_adapter_inference_intent_is_protocol_bound_and_cannot_switch(self):
        class DisconnectBackend(QueueBackend):
            def generate(self, messages, *, protocol, invocation, evidence_sink):
                self.calls += 1
                raise ConnectionError("before response capture")

        backend = DisconnectBackend([])
        with tempfile.TemporaryDirectory() as temporary:
            controller = start(Path(temporary))
            with self.assertRaises(ConnectionError):
                controller.step_registered("C01", backend)
            case = controller._case("C01")
            self.assertEqual("INFERENCE_INTENT_DURABLE", case["pending_turn"]["phase"])
            self.assertEqual(SINGLE_REPOSITORY_PROTOCOL_ID, case["pending_turn"]["protocol_id"])
            case["protocol_id"] = "WS_CODE_AGENT_REQUEST_PROTOCOL_V1_MULTI_REPO"
            controller._write_case(case)
            with self.assertRaises(ExperimentError):
                controller.step_registered("C01", backend)
            self.assertEqual(1, backend.calls)

    def test_c01_ambiguous_validation_invalidates_without_rerun(self):
        backend = QueueBackend([
            request("PROPOSE_PATCH", {"patch": C01_PATCH, "proposed_paths": ["src/parity.py"]}),
        ])
        with tempfile.TemporaryDirectory() as temporary:
            controller = start(Path(temporary))
            controller.step_registered("C01", backend)
            case = controller._case("C01")
            case["case_state"]["validation"]["phase"] = "VISIBLE_STARTED"
            controller._write_case(case)
            controller = AlphaExperimentController(controller.root)
            with self.assertRaises(ExperimentError):
                controller.step_registered("C01", backend)
            self.assertEqual("INVALIDATED", controller._case("C01")["case_status"])
            self.assertEqual(1, backend.calls)


if __name__ == "__main__":
    unittest.main()
