from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.alpha_case_adapters import (  # noqa: E402
    C05_MODEL_VISIBLE_CONTRACT,
    TASK10E_CASE_ORDER,
    TASK10G_R3_CASE_ORDER,
    TASK10I_C05_R4_CASE_ORDER,
    initialize_task10i_c05_r4,
)
from ws_code_agent.alpha_experiment import AlphaExperimentController, ExperimentError  # noqa: E402
from ws_code_agent.katra_ollama_backend import (  # noqa: E402
    KatraOllamaDispositionBackend,
    RuntimeTurnEvidence,
)
from ws_code_agent.request_protocol import MULTI_REPOSITORY_PROTOCOL_ID  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def request(kind: str, arguments: dict) -> str:
    return json.dumps({"request_type": kind, "arguments": arguments}, separators=(",", ":"))


def patch(path: str, old: str, new: str) -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


class QueueBackend:
    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls = 0

    def invocation_for(self, messages, invocation_id, *, protocol):
        return KatraOllamaDispositionBackend.invocation_for(
            messages, invocation_id, protocol=protocol,
        )

    def generate(self, messages, *, protocol, invocation, evidence_sink):
        self.calls += 1
        raw = self.replies.pop(0)
        evidence_sink.capture_response(raw, RuntimeTurnEvidence(
            hashlib.sha256(raw.encode()).hexdigest(), f"job-{self.calls}", "digest", "Q4_K_M",
            "gpu-primary-partial", "GPU_PRIMARY_PARTIAL_OFFLOAD", 20, 80,
            "20%/80% CPU/GPU", "", "",
        ))
        return raw


def start(root: Path, experiment_id: str = "task10i-c05-r4-test") -> AlphaExperimentController:
    return initialize_task10i_c05_r4(root, {
        "experiment_id": experiment_id,
        "experiment_harness_sha": "test",
        "case_order": list(TASK10I_C05_R4_CASE_ORDER),
        "protocols": {
            case: MULTI_REPOSITORY_PROTOCOL_ID for case in TASK10I_C05_R4_CASE_ORDER
        },
    })


class C05R4FamilyTests(unittest.TestCase):
    def test_c05_only_family_registration_and_progression(self):
        backend = QueueBackend([request("NO_CHANGE", {}), request("NO_CHANGE", {})])
        with tempfile.TemporaryDirectory() as temporary:
            controller = start(Path(temporary))
            status = controller.status()
            self.assertEqual("ACTIVE", status["family_status"])
            self.assertEqual("C05-A", status["current_or_next_case"])
            self.assertEqual(["C05-A", "C05-B"], [case["case_id"] for case in status["cases"]])
            self.assertTrue(all(case["turn_committed"] == 0 for case in status["cases"]))
            self.assertFalse((controller.root / "cases/C01").exists())
            self.assertFalse((controller.root / "cases/C03").exists())

            with self.assertRaises(ExperimentError):
                controller.step_registered("C05-B", backend)
            with self.assertRaises(ExperimentError):
                controller.step_registered("C03", backend)
            self.assertEqual(0, backend.calls)

            controller.step_registered("C05-A", backend)
            controller = AlphaExperimentController(controller.root)
            self.assertEqual("C05-B", controller.status()["current_or_next_case"])
            self.assertEqual("TERMINAL", controller._case("C05-A")["case_status"])

            controller.step_registered("C05-B", backend)
            controller = AlphaExperimentController(controller.root)
            self.assertEqual("COMPLETE", controller.status()["family_status"])
            self.assertEqual(2, backend.calls)
            with self.assertRaises(ExperimentError):
                controller.step_registered("C05-B", backend)
            self.assertEqual(2, backend.calls)

    def test_c05_only_family_preserves_protocol_h6_and_inverted_authority(self):
        variants = (
            ("C05-A", "repo-a", "repo-b", "src/feature.py", "enabled = False", "enabled = True"),
            ("C05-B", "repo-b", "repo-a", "src/api.py", 'API_VERSION = "v1"', 'API_VERSION = "v2"'),
        )
        for variant, writable, denied, path, old, new in variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                controller = start(Path(temporary), f"task10i-{variant.lower()}-test")
                case = controller._case(variant)
                self.assertEqual(MULTI_REPOSITORY_PROTOCOL_ID, case["protocol_id"])
                self.assertEqual(C05_MODEL_VISIBLE_CONTRACT,
                                 case["conversation"][0]["content"]["case_contract"])
                contract = json.dumps(case["conversation"][0]["content"]["case_contract"])
                self.assertNotIn("repo-a", contract)
                self.assertNotIn("repo-b", contract)
                repositories = case["case_state"]["repositories"]
                self.assertTrue(repositories[writable]["patch_paths"])
                self.assertEqual([], repositories[denied]["patch_paths"])

                raw = request("PROPOSE_PATCH", {
                    "repository": writable,
                    "patch": patch(path, old, new),
                    "proposed_paths": [path],
                })
                backend = QueueBackend(
                    [raw] if variant == "C05-A" else [request("NO_CHANGE", {}), raw]
                )
                if variant == "C05-B":
                    controller.step_registered("C05-A", backend)
                    controller = AlphaExperimentController(controller.root)
                result = controller.step_registered(variant, backend)
                self.assertEqual("ACCEPTED", result["projection"]["status"])
                self.assertEqual("RETAINED_FOR_CASE",
                                 result["projection"]["accepted_effect"]["retention"])
                self.assertEqual("DENIED",
                                 result["projection"]["accepted_effect"]["replay_same_proposal"])
                self.assertEqual(0,
                                 result["projection"]["case_progress"]["authorized_required_effects_remaining"])
                self.assertEqual("NO_CHANGE",
                                 result["projection"]["case_progress"]["terminal_request_when_none_remain"])
                controller = AlphaExperimentController(controller.root)
                denied_path = "src/api.py" if denied == "repo-b" else "src/feature.py"
                denied_result = controller.step_registered(variant, QueueBackend([
                    request("PROPOSE_PATCH", {
                        "repository": denied,
                        "patch": patch(denied_path, "old", "new"),
                        "proposed_paths": [denied_path],
                    })
                ]))
                feedback = denied_result["projection"]["authority_feedback"]
                self.assertEqual("PATCH_NOT_AUTHORIZED", feedback["classification"])
                self.assertEqual("repository-local; non-transitive",
                                 feedback["task_authority"]["scope"])
                self.assertNotIn(denied,
                                 denied_result["evaluator_evidence"]["isolated_contexts_created"])

    def test_family_identities_and_operator_command_are_distinct(self):
        self.assertEqual(("C03", "C04", "C05-A", "C05-B"), TASK10E_CASE_ORDER)
        self.assertEqual(("C01", "C02", "C03", "C04", "C05-A", "C05-B"),
                         TASK10G_R3_CASE_ORDER)
        self.assertEqual(("C05-A", "C05-B"), TASK10I_C05_R4_CASE_ORDER)
        help_text = subprocess.check_output(
            [sys.executable, str(ROOT / "tools/run_alpha_experiment.py"), "--help"],
            text=True,
        )
        self.assertIn("start-task10e", help_text)
        self.assertIn("start-task10g-r3", help_text)
        self.assertIn("start-task10i-c05-r4", help_text)


if __name__ == "__main__":
    unittest.main()
