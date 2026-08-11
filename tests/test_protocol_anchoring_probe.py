from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.alpha_experiment import AlphaExperimentController, ExperimentError  # noqa: E402
from ws_code_agent.disposition_harness import parse_request  # noqa: E402
from ws_code_agent.katra_ollama_backend import (  # noqa: E402
    KatraOllamaDispositionBackend,
    RuntimeTurnEvidence,
)
from ws_code_agent.protocol_anchoring_probe import (  # noqa: E402
    PROBE_A,
    PROBE_B,
    PROBE_CASE_ID,
    PROBE_PATHS,
    PROBE_PROTOCOL_ID,
    ProtocolAnchoringProbeController,
    protocol_for,
)
from ws_code_agent.request_protocol import (  # noqa: E402
    SINGLE_REPOSITORY_PROTOCOL,
    SINGLE_REPOSITORY_PROTOCOL_ID,
    protocol_by_id,
)


PRODUCTION_RENDER_SHA256 = "c9e7082955f796cad94c49f037acda3033728a80aec2f25d176f7378ec2d9367"


def request(kind: str, arguments: dict) -> str:
    return json.dumps({"request_type": kind, "arguments": arguments}, separators=(",", ":"))


class QueueBackend:
    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls = 0

    def invocation_for(self, messages, invocation_id, *, protocol):
        return KatraOllamaDispositionBackend.invocation_for(
            messages, invocation_id, protocol=protocol
        )

    def generate(self, messages, *, protocol, invocation, evidence_sink):
        self.calls += 1
        raw = self.replies.pop(0)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        evidence_sink.capture_response(raw, RuntimeTurnEvidence(
            digest,
            f"job-{self.calls}",
            "digest",
            "Q4_K_M",
            "gpu-primary-partial",
            "GPU_PRIMARY_PARTIAL_OFFLOAD",
            20,
            80,
            "20%/80% CPU/GPU",
            "",
            "",
        ))
        return raw


class ProtocolAnchoringProbeTests(unittest.TestCase):
    def test_presentations_are_schema_identical_and_only_literal_differs(self):
        alpha, beta = protocol_for(PROBE_A), protocol_for(PROBE_B)
        self.assertEqual(alpha.protocol_id, beta.protocol_id)
        self.assertEqual(
            [(item.request_type, item.argument_fields, item.semantics) for item in alpha.requests],
            [(item.request_type, item.argument_fields, item.semantics) for item in beta.requests],
        )
        self.assertEqual(
            alpha.render().replace(PROBE_PATHS[PROBE_A], "<neutral-path>"),
            beta.render().replace(PROBE_PATHS[PROBE_B], "<neutral-path>"),
        )
        self.assertNotIn("src/example.py", alpha.render())
        self.assertNotIn("src/example.py", beta.render())
        for protocol in (alpha, beta):
            for line in protocol.render().splitlines():
                if line.startswith('{"request_type"'):
                    parse_request(line)

    def test_counterbalanced_initial_prompts_differ_only_by_neutral_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Path(temporary)
            alpha = ProtocolAnchoringProbeController.start(
                store,
                session_id="probe-test-counterbalance-a",
                presentation=PROBE_A,
                harness_sha="test-harness",
            )
            beta = ProtocolAnchoringProbeController.start(
                store,
                session_id="probe-test-counterbalance-b",
                presentation=PROBE_B,
                harness_sha="test-harness",
            )
            alpha_case = alpha._turns._case(PROBE_CASE_ID)
            beta_case = beta._turns._case(PROBE_CASE_ID)
            self.assertEqual(alpha_case["conversation"], beta_case["conversation"])
            self.assertEqual(
                alpha.manifest()["repository"],
                beta.manifest()["repository"],
            )
            alpha_prompt = KatraOllamaDispositionBackend._render_prompt(
                tuple(alpha_case["conversation"]), protocol_for(PROBE_A)
            )
            beta_prompt = KatraOllamaDispositionBackend._render_prompt(
                tuple(beta_case["conversation"]), protocol_for(PROBE_B)
            )
            self.assertEqual(
                alpha_prompt.replace(PROBE_PATHS[PROBE_A], "<neutral-path>"),
                beta_prompt.replace(PROBE_PATHS[PROBE_B], "<neutral-path>"),
            )
            self.assertNotEqual(
                hashlib.sha256(alpha_prompt.encode()).hexdigest(),
                hashlib.sha256(beta_prompt.encode()).hexdigest(),
            )

    def test_production_protocol_is_unchanged_and_probe_is_not_registered(self):
        self.assertEqual(
            PRODUCTION_RENDER_SHA256,
            hashlib.sha256(SINGLE_REPOSITORY_PROTOCOL.render().encode()).hexdigest(),
        )
        self.assertEqual(
            SINGLE_REPOSITORY_PROTOCOL,
            protocol_by_id(SINGLE_REPOSITORY_PROTOCOL_ID),
        )
        with self.assertRaisesRegex(ValueError, "unknown request protocol"):
            protocol_by_id(PROBE_PROTOCOL_ID)

    def test_probe_has_fixed_read_only_authority_and_no_promotion_surface(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = ProtocolAnchoringProbeController.start(
                Path(temporary),
                session_id="probe-test-authority",
                presentation=PROBE_A,
                harness_sha="test-harness",
                turn_limit=2,
            )
            manifest = controller.manifest()
            self.assertEqual({"read_scopes": ["."], "patch_paths": []}, manifest["authority"])
            self.assertFalse(manifest["probe"]["production_qualification_authority"])
            self.assertFalse(manifest["probe"]["promotion_authority"])
            self.assertFalse(hasattr(controller, "review"))
            self.assertFalse(hasattr(controller, "disposition"))
            result = controller.step(QueueBackend([request("PROPOSE_PATCH", {
                "patch": "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n",
                "proposed_paths": ["x"],
            })]))
            self.assertEqual("DENIED_AUTHORITY", result["authority_outcome"])
            self.assertFalse(result["evaluator_evidence"]["candidate_effect"])
            self.assertFalse(result["evaluator_evidence"]["promotion_possible"])

    def test_restart_preserves_presentation_prompt_and_missing_path_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Path(temporary)
            controller = ProtocolAnchoringProbeController.start(
                store,
                session_id="probe-test-restart",
                presentation=PROBE_B,
                harness_sha="test-harness",
                turn_limit=2,
            )
            backend = QueueBackend([
                request("READ", {"path": PROBE_PATHS[PROBE_B]}),
                request("REQUEST_CLARIFICATION", {"question": "Which representation is intended?"}),
            ])
            first = controller.step(backend)
            self.assertEqual("PATH_NOT_FOUND", first["authority_outcome"])
            resumed = ProtocolAnchoringProbeController(controller.root)
            resumed.step(backend)
            status = resumed.status()
            self.assertEqual("AWAITING_CLARIFICATION", status["session_status"])
            self.assertEqual(2, status["current_turn"])
            self.assertEqual(2, len(set(status["invocation_integrity"]["invocation_ids"])))
            self.assertEqual("PASS", status["invocation_integrity"]["turn_hash_chain"])
            self.assertEqual(PROBE_PATHS[PROBE_B], status["example_path"])

    def test_default_controller_and_production_lane_cannot_resolve_probe_protocol(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Path(temporary)
            probe = ProtocolAnchoringProbeController.start(
                store,
                session_id="probe-test-unregistered",
                presentation=PROBE_A,
                harness_sha="test-harness",
                turn_limit=1,
            )
            default = AlphaExperimentController(probe.root)
            with self.assertRaisesRegex(ExperimentError, "protocol is not registered"):
                default.step(PROBE_CASE_ID, QueueBackend([request("NO_CHANGE", {})]), lambda case, raw: {})


if __name__ == "__main__":
    unittest.main()
