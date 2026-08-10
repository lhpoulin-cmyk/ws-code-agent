from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.alpha_experiment import AlphaExperimentController, ExperimentError
from ws_code_agent.katra_ollama_backend import KatraOllamaDispositionBackend, RuntimeTurnEvidence
from ws_code_agent.request_protocol import SINGLE_REPOSITORY_PROTOCOL, SINGLE_REPOSITORY_PROTOCOL_ID


@dataclass
class FakeBackend:
    replies: list[str]
    calls: int = 0
    stop_after_capture: bool = False

    def invocation_for(self, messages, invocation_id, *, protocol):
        return KatraOllamaDispositionBackend.invocation_for(messages, invocation_id, protocol=protocol)

    def generate(self, messages, *, protocol, invocation, evidence_sink):
        self.calls += 1
        raw = self.replies.pop(0)
        evidence_sink.capture_response(raw, RuntimeTurnEvidence(hashlib.sha256(raw.encode()).hexdigest(), f"job-{self.calls}", "digest", "Q4_K_M", "gpu-primary-partial", "GPU_PRIMARY_PARTIAL_OFFLOAD", 20, 80, "20%/80% CPU/GPU", "", ""))
        if self.stop_after_capture:
            raise RuntimeError("simulated session loss")
        return raw


class IdempotentRemoteBackend:
    def __init__(self, raw): self.raw=raw; self.executions=0; self.invocations={}; self.disconnect_once=True
    def invocation_for(self,messages,invocation_id,*,protocol): return KatraOllamaDispositionBackend.invocation_for(messages,invocation_id,protocol=protocol)
    def generate(self,messages,*,protocol,invocation,evidence_sink):
        if invocation.invocation_id not in self.invocations:
            self.executions+=1; self.invocations[invocation.invocation_id]=self.raw
            if self.disconnect_once: self.disconnect_once=False; raise ConnectionError("client disappeared after remote success")
        raw=self.invocations[invocation.invocation_id]
        evidence_sink.capture_response(raw,RuntimeTurnEvidence(hashlib.sha256(raw.encode()).hexdigest(),"job-1","digest","Q4_K_M","gpu-primary-partial","GPU_PRIMARY_PARTIAL_OFFLOAD",20,80,"20%/80% CPU/GPU","","")); return raw


def processor(case, raw):
    request = json.loads(raw)
    return {"request_type": request["request_type"], "parsed_arguments": request["arguments"], "authority_outcome": "AUTHORIZED", "executor_operation": "READ_FILE", "projection": {"status": "OK", "turn": case["turn_committed"] + 1}, "terminal_disposition": request["request_type"] if request["request_type"] == "NO_CHANGE" else None}


class AlphaExperimentTests(unittest.TestCase):
    def start(self, directory: Path, case_id="C03"):
        return AlphaExperimentController.start(directory, {"experiment_id": "family", "experiment_harness_sha": "test", "case_order": [case_id]}, ({"case_id": case_id, "interaction_id": "i", "protocol_id": SINGLE_REPOSITORY_PROTOCOL_ID, "fixture_identity": "fixture", "initial_snapshot_identity": "X", "turn_limit": 3, "conversation": [{"role": "user", "content": {"case": case_id}}], "case_state": {"transition": "NOT_APPLIED", "authority": {"repo-a": "DENIED"}}},))

    def test_raw_response_is_durable_before_recovery_and_never_regenerated(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.start(Path(directory)); backend = FakeBackend(['{"request_type":"READ","arguments":{"path":"x"}}'], stop_after_capture=True)
            with self.assertRaises(RuntimeError): controller.step("C03", backend, processor)
            state = controller.status()["cases"][0]
            self.assertEqual("RAW_RESPONSE_DURABLE", state["pending_turn"]["phase"])
            self.assertTrue((Path(directory) / "family/cases/C03/turns/0001/raw-response.txt").exists())
            result = controller.step("C03", backend, processor)
            self.assertEqual("READ", result["request_type"]); self.assertEqual(1, backend.calls)
            self.assertEqual(1, controller.status()["cases"][0]["turn_committed"])

    def test_committed_turn_reconstructs_conversation_between_invocations(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.start(Path(directory)); backend = FakeBackend(['{"request_type":"READ","arguments":{"path":"x"}}', '{"request_type":"NO_CHANGE","arguments":{}}'])
            controller.step("C03", backend, processor)
            controller = AlphaExperimentController(Path(directory) / "family")
            controller.step("C03", backend, processor)
            state = controller.status()["cases"][0]
            self.assertEqual(2, state["turn_committed"]); self.assertEqual("TERMINAL", state["case_status"])
            case = json.loads((Path(directory) / "family/cases/C03/case.json").read_text())
            self.assertEqual(3, len(case["conversation"]))

    def test_ambiguous_executor_processing_invalidates_and_c05_authority_is_persistent(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.start(Path(directory), "C05-A"); backend = FakeBackend(['{"request_type":"READ","arguments":{}}'])
            case = controller._case("C05-A"); case["pending_turn"] = {"phase":"HARNESS_PROCESSING","turn":1}; controller._write_case(case)
            with self.assertRaises(ExperimentError): controller.step("C05-A", backend, processor)
            stored = controller._case("C05-A")
            self.assertEqual("INVALIDATED", stored["case_status"])
            self.assertEqual("DENIED", stored["case_state"]["authority"]["repo-a"])

    def test_c04_transition_state_and_corrupt_temporary_file_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.start(Path(directory), "C04")
            case = controller._case("C04")
            case["case_state"]["transition"] = "APPLIED"
            case["case_state"]["snapshot_y"] = "Y"
            controller._write_case(case)
            turns = Path(directory) / "family/cases/C04/turns"
            turns.mkdir(parents=True)
            (turns / ".state.json.interrupted").write_text("{truncated")
            resumed = AlphaExperimentController(Path(directory) / "family")
            stored = resumed._case("C04")
            self.assertEqual("APPLIED", stored["case_state"]["transition"])
            self.assertEqual("Y", stored["case_state"]["snapshot_y"])
            self.assertEqual(0, stored["turn_committed"])

    def test_harness_result_durable_finalizes_without_second_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.start(Path(directory)); backend = FakeBackend(['{"request_type":"READ","arguments":{}}'])
            controller.step("C03", backend, processor)
            case = controller._case("C03")
            # A committed record is authoritative; a restart cannot regenerate it.
            resumed = AlphaExperimentController(Path(directory) / "family")
            self.assertEqual(1, resumed.status()["cases"][0]["turn_committed"])
            self.assertEqual(1, backend.calls)

    def test_intent_survives_remote_success_disconnect_and_recovers_once(self):
        with tempfile.TemporaryDirectory() as directory:
            controller=self.start(Path(directory)); backend=IdempotentRemoteBackend('{"request_type":"READ","arguments":{"path":"x"}}')
            with self.assertRaises(ConnectionError): controller.step("C03",backend,processor)
            pending=controller.status()["cases"][0]["pending_turn"]
            self.assertEqual("INFERENCE_INTENT_DURABLE",pending["phase"]); invocation_id=pending["invocation_id"]
            controller=AlphaExperimentController(Path(directory)/"family"); controller.step("C03",backend,processor)
            self.assertEqual(1,backend.executions); self.assertIn(invocation_id,backend.invocations)
            self.assertEqual(1,controller.status()["cases"][0]["turn_committed"])
