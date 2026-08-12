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
from ws_code_agent.katra_ollama_backend import KatraOllamaDispositionBackend, RuntimeTurnEvidence  # noqa: E402
from ws_code_agent.supervised_validation import (  # noqa: E402
    HIDDEN_SOURCE,
    HIDDEN_VALIDATION_ID,
    VISIBLE_SOURCE,
    VISIBLE_VALIDATION_ID,
    WRITE_VALIDATION_IDS,
    TASK11J_VALIDATION_IDS,
    TASK11M_VALIDATION_IDS,
    bind_validation_ids,
    bound_descriptor_ids_by_role,
    validation_registry,
)
from ws_code_agent.supervised_work import (  # noqa: E402
    SYNTHETIC_V2_WRITE,
    SupervisedWorkController,
    SupervisedWorkError,
)
from ws_code_agent.validation import ValidationRole  # noqa: E402


CANDIDATE_MANIFEST = ROOT / "docs/qualification/qwen25-coder-32b-v2-admission-candidate.yaml"


def response(source: str) -> str:
    lines = source.splitlines()
    additions = "\n".join(f"+{line}" for line in lines)
    patch = (
        "diff --git a/src/message.py b/src/message.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/src/message.py\n"
        f"@@ -0,0 +1,{len(lines)} @@\n{additions}\n"
    )
    return json.dumps({
        "request_type": "PROPOSE_PATCH",
        "arguments": {"patch": patch, "proposed_paths": ["src/message.py"]},
    }, separators=(",", ":"))


class OneReplyBackend:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.calls = 0

    def invocation_for(self, messages, invocation_id, *, protocol):
        return KatraOllamaDispositionBackend.invocation_for(
            messages, invocation_id, protocol=protocol
        )

    def generate(self, messages, *, protocol, invocation, evidence_sink):
        self.calls += 1
        evidence_sink.capture_response(self.raw, RuntimeTurnEvidence(
            hashlib.sha256(self.raw.encode()).hexdigest(),
            f"validation-test-job-{self.calls}",
            "digest",
            "Q4_K_M",
            "gpu-primary-partial",
            "GPU_PRIMARY_PARTIAL_OFFLOAD",
            29,
            71,
            "29%/71% CPU/GPU",
            "",
            "",
        ))
        return self.raw


class LocalContainedRunner:
    def __init__(self, behavior: dict[str, str] | None = None) -> None:
        self.behavior = behavior or {}

    def run(self, context, descriptor):
        behavior = self.behavior.get(descriptor.descriptor_id, "run")
        if behavior == "timeout":
            return ContainedExecution(124, b"", b"", self._evidence())
        if behavior == "fail":
            return ContainedExecution(7, b"", b"bounded failure", self._evidence())
        if behavior == "effect":
            (Path(context.isolated_root) / "validator-effect.txt").write_text("x", encoding="utf-8")
            return ContainedExecution(0, b"", b"", self._evidence())
        process = subprocess.run(
            [descriptor.executable, *descriptor.arguments],
            cwd=context.isolated_root,
            env={"PATH": os.defpath, "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return ContainedExecution(process.returncode, process.stdout, process.stderr, self._evidence())

    @staticmethod
    def _evidence():
        return {
            "CONTAINMENT_MECHANISM": "test-double",
            "CONTAINMENT_PROFILE": "fixed-test-v1",
            "CONTAINMENT_UNIT": "test-unit",
            "CONTAINMENT_UID_GID": "1000:1000",
            "CONTAINMENT_NETWORK": "DENIED",
            "CONTAINMENT_RESULT": "completed",
        }


class RecordingPassRunner:
    def __init__(self) -> None:
        self.descriptor_ids: list[str] = []

    def run(self, context, descriptor):
        self.descriptor_ids.append(descriptor.descriptor_id)
        return ContainedExecution(0, b"bounded pass", b"", LocalContainedRunner._evidence())


class SupervisedValidationTests(unittest.TestCase):
    def _controller(self, root: Path, source: str = 'def message(): return "hello"\n'):
        controller = SupervisedWorkController.start_qwen25_32b_v2_admission(
            root / "store",
            session_id="work-validation-test-session",
            fixture_kind=SYNTHETIC_V2_WRITE,
            candidate_path=CANDIDATE_MANIFEST,
            harness_sha="validation-test-harness",
            turn_limit=8,
        )
        backend = OneReplyBackend(response(source))
        controller.step(backend)
        self.assertEqual(1, backend.calls)
        return controller

    def test_contract_calibration_accepts_distinct_good_forms_and_rejects_bad_forms(self):
        good = (
            'def message():\n    return "hello"\n',
            'def message(): return "hello"\n',
            'def message() -> str:\n    """Return the greeting."""\n    return "hello"\n',
        )
        bad = (
            None,
            'def message(:\n',
            'def other(): return "hello"\n',
            'def message(value): return "hello"\n',
            'def message(): return "Hello"\n',
            'def message(): return None\n',
        )
        for source in good:
            self._run_assets(source, expected=0)
        for source in bad:
            self._run_assets(source, expected=1)

    def test_task11a_existing_file_calibration_reuses_only_the_exact_behavioral_contract(self):
        # Task 11A changes an existing file, but its final behavioral contract is
        # exactly the already-independent Task 10W descriptor contract.
        for source in (
            'def message():\n    return "hello"\n',
            'def message(): return "hello"\n',
            'def message() -> str:\n    """Greeting."""\n    return "hello"\n',
        ):
            self._run_assets(source, expected=0)
        for source in (
            'def message():\n    return "hi"\n',
            'def message(value=None): return "hello"\n',
            'message = "hello"\n',
            'def message(): return b"hello"\n',
        ):
            self._run_assets(source, expected=1)
        contract = bind_validation_ids(WRITE_VALIDATION_IDS)
        self.assertNotEqual(
            contract["descriptors"][0]["source_sha256"],
            contract["descriptors"][1]["source_sha256"],
        )

    def _run_assets(self, source: str | None, *, expected: int):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            if source is not None:
                (root / "src").mkdir()
                (root / "src/message.py").write_text(source, encoding="utf-8")
            for asset in (VISIBLE_SOURCE, HIDDEN_SOURCE):
                process = subprocess.run(
                    [sys.executable, "-B", str(asset)],
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(expected, process.returncode, (asset, source, process.stderr))

    def test_registry_is_exact_and_rejects_unauthorized_identity(self):
        registry = validation_registry()
        self.assertEqual(
            set(WRITE_VALIDATION_IDS + TASK11J_VALIDATION_IDS + TASK11M_VALIDATION_IDS),
            set(registry),
        )
        contract = bind_validation_ids(WRITE_VALIDATION_IDS)
        self.assertEqual(list(WRITE_VALIDATION_IDS), contract["authorized_validation_ids"])
        self.assertTrue(all(item["containment_required"] for item in contract["descriptors"]))
        self.assertTrue(all(not item["repository_writes_allowed"] for item in contract["descriptors"]))
        with self.assertRaisesRegex(ValueError, "unknown or unauthorized"):
            bind_validation_ids(("model-selected-command",))

    def test_future_session_binds_restart_stable_validation_and_passes_both(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            controller = self._controller(root)
            manifest = controller.manifest()
            self.assertEqual(list(WRITE_VALIDATION_IDS), manifest["validation"]["authorized_validation_ids"])
            conversation = json.dumps(controller._turns._case("WORK")["conversation"])
            self.assertNotIn(VISIBLE_VALIDATION_ID, conversation)
            self.assertNotIn(HIDDEN_VALIDATION_ID, conversation)
            restarted = SupervisedWorkController(controller.root, LocalContainedRunner())
            visible = restarted.advance_validation()
            self.assertEqual("VALIDATION_PASS", visible["status"])
            hidden = restarted.advance_validation()
            self.assertEqual("VALIDATION_PASS", hidden["status"])
            review = restarted.review()
            self.assertEqual("VALIDATION_PASS", review["validation_result"])
            self.assertEqual("VALIDATED", review["technical_correctness"])
            self.assertEqual(VISIBLE_VALIDATION_ID, review["visible_validation"]["descriptor_id"])
            self.assertEqual(HIDDEN_VALIDATION_ID, review["hidden_validation"]["descriptor_id"])
            self.assertEqual("MATCH", review["source_state"])
            self.assertEqual("MATCH", review["candidate_integrity"])

    def test_bound_roles_resolve_task11j_pair_without_historical_fallback(self):
        contract = bind_validation_ids(TASK11J_VALIDATION_IDS)
        resolved = bound_descriptor_ids_by_role(contract)
        self.assertEqual(TASK11J_VALIDATION_IDS[0], resolved[ValidationRole.VISIBLE])
        self.assertEqual(TASK11J_VALIDATION_IDS[1], resolved[ValidationRole.HIDDEN_ORACLE])
        for mutation in ("version", "descriptor_identity", "containment_required"):
            changed = json.loads(json.dumps(contract))
            changed["descriptors"][0][mutation] = "wrong" if mutation != "containment_required" else False
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                bound_descriptor_ids_by_role(changed)

    def test_advance_validation_uses_exact_session_bound_task11j_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            manifest_path = controller.root / "session-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["validation"] = bind_validation_ids(TASK11J_VALIDATION_IDS)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            runner = RecordingPassRunner()
            restarted = SupervisedWorkController(controller.root, runner)
            restarted.advance_validation()
            restarted.advance_validation()
            self.assertEqual(list(TASK11J_VALIDATION_IDS), runner.descriptor_ids)

    def test_explicit_preexecution_recovery_is_identity_bound_and_audited(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            candidate = controller._turns._case("WORK")["case_state"]["candidate"]
            candidate_identity = candidate["candidate_snapshot_identity"]
            contract = controller.manifest()["validation"]
            visible_identity = contract["descriptors"][0]["descriptor_identity"]
            state_path = controller.root / "validation-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["candidate_snapshot_identity"] = candidate_identity
            state["phase"] = "VISIBLE_VALIDATION_STARTED"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            restarted = SupervisedWorkController(controller.root, LocalContainedRunner())
            with self.assertRaisesRegex(SupervisedWorkError, "BINDING_MISMATCH"):
                restarted.recover_preexecution_validation(candidate_identity, "0" * 64)
            record = restarted.recover_preexecution_validation(
                candidate_identity,
                visible_identity,
            )
            self.assertEqual("VALIDATION_PREEXECUTION_RECOVERY", record["record_type"])
            self.assertEqual(VISIBLE_VALIDATION_ID, record["descriptor_id"])
            self.assertEqual("NOT_STARTED", record["recovered_phase"])
            self.assertFalse(record["evaluator_evidence_present"])
            self.assertEqual("VALIDATION_PASS", restarted.advance_validation()["status"])
            self.assertEqual("VALIDATION_PASS", restarted.advance_validation()["status"])
            with self.assertRaisesRegex(SupervisedWorkError, "NOT_APPLICABLE"):
                restarted.recover_preexecution_validation(candidate_identity, visible_identity)

    def test_preexecution_recovery_refuses_existing_evaluator_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            candidate = controller._turns._case("WORK")["case_state"]["candidate"]
            candidate_identity = candidate["candidate_snapshot_identity"]
            contract = controller.manifest()["validation"]
            visible_identity = contract["descriptors"][0]["descriptor_identity"]
            state_path = controller.root / "validation-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state.update({
                "candidate_snapshot_identity": candidate_identity,
                "phase": "VISIBLE_VALIDATION_STARTED",
            })
            state_path.write_text(json.dumps(state), encoding="utf-8")
            evidence = controller.root / "evaluator/validation/visible.json"
            evidence.parent.mkdir(parents=True)
            evidence.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(SupervisedWorkError, "OUTCOME_AMBIGUOUS"):
                SupervisedWorkController(
                    controller.root, LocalContainedRunner()
                ).recover_preexecution_validation(candidate_identity, visible_identity)

    def test_visible_and_hidden_failure_remain_distinct(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary), 'def message(): return "Hello"\n')
            restarted = SupervisedWorkController(controller.root, LocalContainedRunner())
            visible = restarted.advance_validation()
            self.assertEqual("VALIDATION_FAIL", visible["status"])
            self.assertEqual("VISIBLE_VALIDATION_FAIL", restarted.review()["validation_result"])
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            restarted = SupervisedWorkController(
                controller.root,
                LocalContainedRunner({HIDDEN_VALIDATION_ID: "fail"}),
            )
            restarted.advance_validation()
            hidden = restarted.advance_validation()
            self.assertEqual("VALIDATION_FAIL", hidden["status"])
            self.assertEqual("HIDDEN_VALIDATION_FAIL", restarted.review()["validation_result"])

    def test_timeout_effect_and_candidate_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            restarted = SupervisedWorkController(
                controller.root,
                LocalContainedRunner({VISIBLE_VALIDATION_ID: "timeout"}),
            )
            run = restarted.advance_validation()
            self.assertEqual("VALIDATION_TIMEOUT", run["status"])
            self.assertEqual("NOT_EVALUATED", restarted.review()["technical_correctness"])
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            restarted = SupervisedWorkController(
                controller.root,
                LocalContainedRunner({VISIBLE_VALIDATION_ID: "effect"}),
            )
            run = restarted.advance_validation()
            self.assertEqual("EFFECT_VIOLATION", run["status"])
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            (controller.root / "candidate/repository/src/message.py").write_text(
                'def message(): return "tampered"\n', encoding="utf-8"
            )
            with self.assertRaisesRegex(SupervisedWorkError, "CANDIDATE_STATE_INVALID"):
                SupervisedWorkController(controller.root, LocalContainedRunner()).advance_validation()

    def test_descriptor_substitution_and_ambiguous_restart_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            manifest_path = controller.root / "session-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["validation"]["descriptors"][0]["descriptor_identity"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(SupervisedWorkError, "BINDING_MISMATCH"):
                SupervisedWorkController(controller.root, LocalContainedRunner()).advance_validation()
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            state_path = controller.root / "validation-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["phase"] = "VISIBLE_VALIDATION_STARTED"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(SupervisedWorkError, "VALIDATION_OUTCOME_AMBIGUOUS"):
                SupervisedWorkController(controller.root, LocalContainedRunner()).advance_validation()

    def test_retrospective_binding_is_forward_only_and_candidate_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = self._controller(Path(temporary))
            candidate = controller._turns._case("WORK")["case_state"]["candidate"]
            identity = candidate["candidate_snapshot_identity"]
            manifest_path = controller.root / "session-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.pop("validation")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (controller.root / "validation-state.json").unlink()
            restarted = SupervisedWorkController(controller.root, LocalContainedRunner())
            with self.assertRaisesRegex(SupervisedWorkError, "CANDIDATE_STATE_INVALID"):
                restarted.bind_retrospective_validation("0" * 64)
            binding = restarted.bind_retrospective_validation(identity)
            self.assertEqual("RETROSPECTIVE_TECHNICAL_VALIDATION_BINDING", binding["record_type"])
            restarted.advance_validation()
            restarted.advance_validation()
            review = restarted.review()
            self.assertEqual("VALIDATED", review["technical_correctness"])
            self.assertEqual(1, controller._turns._case("WORK")["turn_committed"])


if __name__ == "__main__":
    unittest.main()
