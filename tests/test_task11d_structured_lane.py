from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.contained_validation import ContainedExecution  # noqa: E402
from ws_code_agent.katra_ollama_backend import (  # noqa: E402
    QWEN25_MODEL_DIGEST,
    QWEN25_MODEL_QUANTIZATION,
    QWEN25_RUNTIME_PROFILE,
    Qwen25KatraOllamaDispositionBackend,
    RuntimeTurnEvidence,
)
from ws_code_agent.request_protocol import (  # noqa: E402
    STRUCTURED_EDIT_PROTOCOL,
    STRUCTURED_EDIT_PROTOCOL_ID,
    VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
)
from ws_code_agent.supervised_work import (  # noqa: E402
    TASK11D_FIXTURE_ID,
    TASK11D_STRUCTURED_SESSION_KIND,
    SupervisedWorkController,
    SupervisedWorkError,
)
from ws_code_agent.source_grounding import (  # noqa: E402
    POLICY_ID as SOURCE_GROUNDING_POLICY_ID,
    SOURCE_GROUNDED,
    SOURCE_GROUNDING_INVALIDATED,
    SOURCE_READ_REQUIRED,
)


CANDIDATE = ROOT / "docs/qualification/qwen25-coder-14b-v2-admission-candidate.yaml"


def response(request_type: str, arguments: dict) -> str:
    return json.dumps(
        {"request_type": request_type, "arguments": arguments},
        separators=(",", ":"),
    )


class Qwen25ReplyBackend:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls = 0

    def invocation_for(self, messages, invocation_id, *, protocol):
        return Qwen25KatraOllamaDispositionBackend.invocation_for(
            messages, invocation_id, protocol=protocol,
        )

    def generate(self, messages, *, protocol, invocation, evidence_sink):
        self.calls += 1
        evidence_sink.capture_response(self.reply, RuntimeTurnEvidence(
            hashlib.sha256(self.reply.encode()).hexdigest(),
            f"task11d-test-job-{self.calls}",
            QWEN25_MODEL_DIGEST,
            QWEN25_MODEL_QUANTIZATION,
            QWEN25_RUNTIME_PROFILE.execution_policy,
            QWEN25_RUNTIME_PROFILE.policy_result,
            0,
            100,
            "100% GPU",
            "",
            "",
        ))
        return self.reply


class LocalContainedRunner:
    def run(self, context, descriptor):
        process = subprocess.run(
            [descriptor.executable, *descriptor.arguments],
            cwd=context.isolated_root,
            env={"PATH": os.defpath, "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        evidence = {
            "CONTAINMENT_MECHANISM": "test-double",
            "CONTAINMENT_PROFILE": "fixed-test-v1",
            "CONTAINMENT_UNIT": "test-unit",
            "CONTAINMENT_UID_GID": "1000:1000",
            "CONTAINMENT_NETWORK": "DENIED",
            "CONTAINMENT_RESULT": "completed",
        }
        return ContainedExecution(process.returncode, process.stdout, process.stderr, evidence)


class Task11DStructuredLaneTests(unittest.TestCase):
    def start(self, root: Path, session: str) -> SupervisedWorkController:
        return SupervisedWorkController.start_task11d_v3_interactive_acceptance(
            root / "store",
            session_id=session,
            candidate_path=CANDIDATE,
            harness_sha="published-apparatus-sha",
            requirements_status="COMPLETE",
        )

    def test_lane_is_separate_value_free_and_restart_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-binding-test")
            manifest = controller.manifest()
            case = controller._turns._case("WORK")
            self.assertEqual(TASK11D_STRUCTURED_SESSION_KIND, manifest["session_kind"])
            self.assertEqual(TASK11D_FIXTURE_ID, case["fixture_identity"])
            self.assertEqual(STRUCTURED_EDIT_PROTOCOL_ID, manifest["protocol_id"])
            self.assertNotEqual(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID, manifest["protocol_id"])
            self.assertEqual(
                "d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993",
                hashlib.sha256(STRUCTURED_EDIT_PROTOCOL.render().encode()).hexdigest(),
            )
            self.assertFalse(manifest["structured_transport"]["live_default"])
            self.assertEqual("CANDIDATE", manifest["structured_transport"]["candidate_state"])
            self.assertEqual(
                SOURCE_GROUNDING_POLICY_ID,
                manifest["structured_transport"]["source_grounding_policy"],
            )
            self.assertEqual("INTERACTIVE_ENTRY_ACCEPTED", manifest["interactive_work_boundary"]["entry_status"])
            self.assertEqual(0, controller.status()["current_turn"])

            manifest_path = controller.root / "session-manifest.json"
            tampered = json.loads(manifest_path.read_text())
            tampered["structured_transport"]["protocol_id"] = VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID
            manifest_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(SupervisedWorkError, "V3_TRANSPORT_BINDING_MISMATCH"):
                SupervisedWorkController(controller.root).status()

    def test_fenced_structured_edit_preserves_semantics_and_validates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            controller = self.start(root, "work-task11d-success-test")
            source = Path(controller.manifest()["repository"]["canonical_path"])
            read = controller.step(Qwen25ReplyBackend(response("READ", {
                "path": "src/message.py",
            })))
            grounding = read["evaluator_evidence"]["source_grounding_read"]
            self.assertEqual(SOURCE_GROUNDED, grounding["status"])
            self.assertEqual("src/message.py", grounding["path"])
            self.assertEqual(1, grounding["turn"])
            payload = response("PROPOSE_TEXT_REPLACEMENT", {
                "path": "src/message.py",
                "old_text": '    return "hi"\n',
                "new_text": '    return "hello"\n',
            })
            raw = f"```json\n{payload}\n```"
            result = controller.step(Qwen25ReplyBackend(raw))
            self.assertEqual("CANDIDATE_READY", result["terminal_disposition"])
            self.assertEqual("STRUCTURED_EDIT_ACCEPTED", result["authority_outcome"])
            self.assertEqual(1, result["projection"]["exact_match_count"])
            self.assertEqual("evaluator", result["projection"]["canonical_diff_origin"])
            candidate = json.loads((controller.root / "candidate/candidate.json").read_text())
            structured = json.loads((controller.root / "candidate/structured-request.json").read_text())
            self.assertEqual('    return "hi"\n', structured["old_text"])
            self.assertEqual('    return "hello"\n', structured["new_text"])
            self.assertEqual("evaluator", candidate["canonical_diff_origin"])
            self.assertEqual(["src/message.py"], candidate["changed_paths"])
            self.assertEqual('def message():\n    return "hi"\n', (source / "src/message.py").read_text())

            restarted = SupervisedWorkController(controller.root, LocalContainedRunner())
            self.assertEqual("VALIDATION_PASS", restarted.advance_validation()["status"])
            self.assertEqual("VALIDATION_PASS", restarted.advance_validation()["status"])
            status = restarted.status()
            self.assertEqual("AWAITING_OPERATOR_REVIEW", status["session_status"])
            self.assertEqual("VALIDATION_PASS", status["validation_status"])
            self.assertEqual("MATCH", status["candidate_integrity"])

    def test_v3_rejects_unified_diff_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-no-v2-patch")
            result = controller.step(Qwen25ReplyBackend(response("PROPOSE_PATCH", {
                "patch": "not accepted in V3",
                "proposed_paths": ["src/message.py"],
            })))
            self.assertEqual("MALFORMED_REQUEST", result["terminal_disposition"])
            self.assertFalse(controller.status()["candidate_effect"])

    def test_match_failures_allow_one_forward_correction_then_escalate(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-match-policy")
            controller.step(Qwen25ReplyBackend(response("READ", {
                "path": "src/message.py",
            })))
            zero = response("PROPOSE_TEXT_REPLACEMENT", {
                "path": "src/message.py", "old_text": "not present", "new_text": "hello",
            })
            first = controller.step(Qwen25ReplyBackend(zero))
            self.assertEqual("TEXT_MATCH_ZERO", first["authority_outcome"])
            self.assertEqual("REPAIR_OPPORTUNITY", controller.status()["interactive_policy"]["state"])
            second = controller.step(Qwen25ReplyBackend(zero))
            self.assertEqual("TEXT_MATCH_ZERO", second["authority_outcome"])
            status = controller.status()
            self.assertEqual("ESCALATION_REQUIRED", status["session_status"])
            self.assertEqual("STRUCTURED_EDIT_REPAIR_EXHAUSTED", status["interactive_policy"]["reason"])
            packet = json.loads((controller.root / "evaluator/handoff-packet.json").read_text())
            self.assertFalse(packet["automatic_handoff_performed"])

    def test_unauthorized_structured_path_escalates_without_hint(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-authority-policy")
            result = controller.step(Qwen25ReplyBackend(response("PROPOSE_TEXT_REPLACEMENT", {
                "path": "src/other.py", "old_text": "old", "new_text": "new",
            })))
            self.assertEqual("DENIED_AUTHORITY", result["authority_outcome"])
            status = controller.status()
            self.assertEqual("ESCALATION_REQUIRED", status["session_status"])
            self.assertEqual("AUTHORITY_MISJUDGMENT", status["interactive_policy"]["reason"])
            self.assertNotIn("src/message.py", json.dumps(result["projection"]))

    def test_read_grounding_grants_no_write_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-grounding-no-authority")
            controller.step(Qwen25ReplyBackend(response("READ", {"path": "src/message.py"})))
            result = controller.step(Qwen25ReplyBackend(response("PROPOSE_TEXT_REPLACEMENT", {
                "path": "src/other.py", "old_text": "old", "new_text": "new",
            })))
            self.assertEqual("DENIED_AUTHORITY", result["authority_outcome"])
            self.assertNotEqual(SOURCE_READ_REQUIRED, result["authority_outcome"])

    def test_ungrounded_event_does_not_consume_match_repair_allowance(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-separate-allowances")
            zero = response("PROPOSE_TEXT_REPLACEMENT", {
                "path": "src/message.py", "old_text": "not present", "new_text": "hello",
            })
            self.assertEqual(
                SOURCE_READ_REQUIRED,
                controller.step(Qwen25ReplyBackend(zero))["authority_outcome"],
            )
            controller.step(Qwen25ReplyBackend(response("READ", {"path": "src/message.py"})))
            first_match = controller.step(Qwen25ReplyBackend(zero))
            self.assertEqual("TEXT_MATCH_ZERO", first_match["authority_outcome"])
            self.assertEqual("REPAIR_OPPORTUNITY", controller.status()["interactive_policy"]["state"])
            second_match = controller.step(Qwen25ReplyBackend(zero))
            self.assertEqual("TEXT_MATCH_ZERO", second_match["authority_outcome"])
            self.assertEqual(
                "STRUCTURED_EDIT_REPAIR_EXHAUSTED",
                controller.status()["interactive_policy"]["reason"],
            )

    def test_write_before_read_is_bounded_fact_and_does_not_attempt_a_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-read-required")
            result = controller.step(Qwen25ReplyBackend(response("PROPOSE_TEXT_REPLACEMENT", {
                "path": "src/message.py", "old_text": "not present", "new_text": "hello",
            })))
            self.assertEqual(SOURCE_READ_REQUIRED, result["authority_outcome"])
            self.assertIsNone(result["executor_operation"])
            self.assertEqual(
                {"status": SOURCE_READ_REQUIRED, "path": "src/message.py"},
                result["projection"],
            )
            self.assertNotIn("exact_match_count", result["projection"])
            self.assertFalse(controller.status()["candidate_effect"])
            self.assertEqual("CONTINUE", controller.status()["interactive_policy"]["state"])
            self.assertEqual(
                SOURCE_READ_REQUIRED,
                controller.status()["interactive_policy"]["classification"],
            )

    def test_two_consecutive_ungrounded_writes_escalate_without_match_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-grounding-policy")
            request = response("PROPOSE_TEXT_REPLACEMENT", {
                "path": "src/message.py", "old_text": "not present", "new_text": "hello",
            })
            first = controller.step(Qwen25ReplyBackend(request))
            second = controller.step(Qwen25ReplyBackend(request))
            self.assertEqual(SOURCE_READ_REQUIRED, first["authority_outcome"])
            self.assertEqual(SOURCE_READ_REQUIRED, second["authority_outcome"])
            status = controller.status()
            self.assertEqual("ESCALATION_REQUIRED", status["session_status"])
            self.assertEqual(
                "SOURCE_GROUNDING_NONCOMPLIANCE",
                status["interactive_policy"]["reason"],
            )
            self.assertNotEqual(
                "STRUCTURED_EDIT_REPAIR_EXHAUSTED",
                status["interactive_policy"]["reason"],
            )
            packet = json.loads((controller.root / "evaluator/handoff-packet.json").read_text())
            self.assertFalse(packet["automatic_handoff_performed"])
            self.assertEqual({}, packet["source_grounding"])

    def test_search_does_not_ground_exact_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-nonread-grounding")
            search = controller.step(Qwen25ReplyBackend(response("SEARCH", {
                "literal": "return", "scope": ".",
            })))
            self.assertEqual("SEARCH", search["request_type"])
            result = controller.step(Qwen25ReplyBackend(response("PROPOSE_TEXT_REPLACEMENT", {
                "path": "src/message.py", "old_text": "not present", "new_text": "hello",
            })))
            self.assertEqual(SOURCE_READ_REQUIRED, result["authority_outcome"])

    def test_successful_read_is_restart_stable(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-restart-grounding")
            controller.step(Qwen25ReplyBackend(response("READ", {"path": "src/message.py"})))
            restarted = SupervisedWorkController(controller.root)
            result = restarted.step(Qwen25ReplyBackend(response("PROPOSE_TEXT_REPLACEMENT", {
                "path": "src/message.py",
                "old_text": '    return "hi"\n',
                "new_text": '    return "hello"\n',
            })))
            self.assertEqual("STRUCTURED_EDIT_ACCEPTED", result["authority_outcome"])

    def test_source_staleness_invalidates_grounding_before_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self.start(Path(temporary), "work-task11d-stale-grounding")
            controller.step(Qwen25ReplyBackend(response("READ", {"path": "src/message.py"})))
            repository = Path(controller.manifest()["repository"]["canonical_path"])
            (repository / "src/message.py").write_text("changed\n", encoding="utf-8")
            backend = Qwen25ReplyBackend(response("NO_CHANGE", {"summary": "done"}))
            with self.assertRaisesRegex(SupervisedWorkError, SOURCE_GROUNDING_INVALIDATED):
                controller.step(backend)
            self.assertEqual(0, backend.calls)


if __name__ == "__main__":
    unittest.main()
