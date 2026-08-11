from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.alpha_experiment import AlphaExperimentController  # noqa: E402
from ws_code_agent.katra_ollama_backend import KatraOllamaDispositionBackend, RuntimeTurnEvidence  # noqa: E402
from ws_code_agent.supervised_work import SupervisedWorkController, SupervisedWorkError  # noqa: E402


QUALIFICATION = ROOT / "docs/qualification/qwen3-coder-30b-alpha-v1.yaml"


def request(kind: str, arguments: dict) -> str:
    return json.dumps({"request_type": kind, "arguments": arguments}, separators=(",", ":"))


def patch(path: str, old: str, new: str) -> str:
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{old}\n+{new}\n"


def new_file_patch(path: str, content: str) -> str:
    lines = content.splitlines()
    added = "\n".join(f"+{line}" for line in lines)
    return (
        f"diff --git a/{path} b/{path}\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{len(lines)} @@\n{added}\n"
    )


class QueueBackend:
    def __init__(self, replies: list[str], disconnect_after_capture: bool = False):
        self.replies = list(replies)
        self.calls = 0
        self.disconnect_after_capture = disconnect_after_capture

    def invocation_for(self, messages, invocation_id, *, protocol):
        return KatraOllamaDispositionBackend.invocation_for(messages, invocation_id, protocol=protocol)

    def generate(self, messages, *, protocol, invocation, evidence_sink):
        self.calls += 1
        raw = self.replies[0]
        evidence_sink.capture_response(raw, RuntimeTurnEvidence(
            hashlib.sha256(raw.encode()).hexdigest(), f"job-{self.calls}",
            "digest", "Q4_K_M", "gpu-primary-partial", "GPU_PRIMARY_PARTIAL_OFFLOAD",
            20, 80, "20%/80% CPU/GPU", "", "",
        ))
        if self.disconnect_after_capture:
            self.disconnect_after_capture = False
            raise ConnectionError("simulated client loss")
        self.replies.pop(0)
        return raw


def repository(root: Path) -> tuple[Path, str]:
    repo = root / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src/message.py").write_text('MESSAGE = "old"\n')
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run([
        "git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-qm", "fixture",
    ], check=True)
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    return repo, head


def start(store: Path, repo: Path, head: str, *, patch_paths=("src/message.py",), session="work-test-session"):
    return SupervisedWorkController.start(
        store,
        session_id=session,
        repository=repo,
        expected_head=head,
        objective="Change the message as requested.",
        read_scopes=("src",),
        patch_paths=tuple(patch_paths),
        qualification_path=QUALIFICATION,
        harness_sha="test-harness",
        turn_limit=3,
    )


class SupervisedWorkTests(unittest.TestCase):
    def test_manifest_binds_clean_source_explicit_scope_and_qualification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, head = repository(root)
            controller = start(root / "store", repo, head)
            manifest = controller.manifest()
            self.assertEqual(["src"], manifest["authority"]["read_scopes"])
            self.assertEqual(["src/message.py"], manifest["authority"]["patch_paths"])
            self.assertEqual("SUPERVISED_SINGLE_REPO", manifest["qualification"]["operating_class"])
            self.assertEqual("WS_CODE_AGENT_REQUEST_PROTOCOL_V1_SINGLE", manifest["protocol_id"])
            self.assertNotIn("repositories", manifest)
            altered = root / "qualification.yaml"
            altered.write_text(QUALIFICATION.read_text().replace(
                "SUPERVISED_SINGLE_REPO: QUALIFIED", "SUPERVISED_SINGLE_REPO: NOT_QUALIFIED"
            ))
            with self.assertRaisesRegex(SupervisedWorkError, "MODEL_QUALIFICATION_MISMATCH"):
                SupervisedWorkController.start(
                    root / "altered-store", session_id="work-altered-session", repository=repo,
                    expected_head=head, objective="Task", read_scopes=("src",),
                    patch_paths=("src/message.py",), qualification_path=altered,
                    harness_sha="test-harness",
                )
            (repo / "draft.txt").write_text("dirty")
            with self.assertRaisesRegex(SupervisedWorkError, "SOURCE_MUST_BE_CLEAN"):
                start(root / "other", repo, head, session="work-other-session")

    def test_candidate_review_and_operator_disposition_never_promote_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, head = repository(root)
            before = (repo / "src/message.py").read_bytes()
            controller = start(root / "store", repo, head)
            raw = request("PROPOSE_PATCH", {"patch": patch("src/message.py", 'MESSAGE = "old"', 'MESSAGE = "hello"'), "proposed_paths": ["src/message.py"]})
            result = controller.step(QueueBackend([raw]))
            self.assertEqual("CANDIDATE_READY", result["terminal_disposition"])
            review = SupervisedWorkController(controller.root).review()
            self.assertEqual(["src/message.py"], review["changed_paths"])
            self.assertEqual("SUCCESS", review["executor_application"])
            self.assertEqual("VALIDATION_NOT_CONFIGURED", review["validation_result"])
            self.assertEqual(before, (repo / "src/message.py").read_bytes())
            disposition = SupervisedWorkController(controller.root).disposition("APPROVE")
            self.assertFalse(disposition["promotion_performed"])
            self.assertEqual(before, (repo / "src/message.py").read_bytes())
            self.assertEqual("PASS", controller.status()["invocation_integrity"]["turn_hash_chain"])

    def test_clarification_is_exact_durable_and_pauses_without_effect(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, head = repository(root)
            controller = start(root / "store", repo, head, patch_paths=())
            question = "Should the message be a display string or a stable identifier?"
            controller.step(QueueBackend([request("REQUEST_CLARIFICATION", {"question": question})]))
            resumed = SupervisedWorkController(controller.root)
            status = resumed.status()
            self.assertEqual("AWAITING_CLARIFICATION", status["session_status"])
            self.assertEqual(question, status["clarification"]["question"])
            self.assertFalse(status["candidate_effect"])
            with self.assertRaisesRegex(SupervisedWorkError, "SESSION_MAY_NOT_ADVANCE"):
                resumed.step(QueueBackend([request("NO_CHANGE", {})]))

    def test_scope_second_repository_and_stale_source_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, head = repository(root)
            with self.assertRaisesRegex(SupervisedWorkError, "SUPERVISION_REQUIRED_CROSS_REPOSITORY"):
                start(root / "bad", repo, head, patch_paths=("../peer/file.py",), session="work-cross-repo")
            controller = start(root / "store", repo, head)
            raw = request("PROPOSE_PATCH", {"patch": patch("src/other.py", "old", "new"), "proposed_paths": ["src/other.py"]})
            denied = controller.step(QueueBackend([raw]))
            self.assertEqual("DENIED_SCOPE", denied["authority_outcome"])
            malformed = request("READ", {"repository": "peer", "path": "src/message.py"})
            controller.step(QueueBackend([malformed]))
            self.assertEqual("MALFORMED_REQUEST", controller.status()["terminal_disposition"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, head = repository(root)
            controller = start(root / "store", repo, head)
            raw = request("PROPOSE_PATCH", {"patch": patch("src/message.py", 'MESSAGE = "old"', 'MESSAGE = "hello"'), "proposed_paths": ["src/message.py"]})
            controller.step(QueueBackend([raw]))
            (repo / "src/message.py").write_text('MESSAGE = "operator"\n')
            review = controller.review()
            self.assertEqual("STALE", review["source_state"])
            with self.assertRaisesRegex(SupervisedWorkError, "SOURCE_STATE_STALE"):
                controller.disposition("APPROVE")

    def test_interrupted_raw_capture_recovers_without_duplicate_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, head = repository(root)
            controller = start(root / "store", repo, head)
            backend = QueueBackend([request("READ", {"path": "src/message.py"})], disconnect_after_capture=True)
            with self.assertRaises(ConnectionError):
                controller.step(backend)
            self.assertEqual("RAW_RESPONSE_DURABLE", controller.status()["pending_turn"]["phase"])
            resumed = SupervisedWorkController(controller.root)
            resumed.step(backend)
            self.assertEqual(1, backend.calls)
            status = resumed.status()
            self.assertEqual(1, status["current_turn"])
            self.assertFalse(status["invocation_integrity"]["duplicate_invocation_ids"])

    def test_patch_rejection_and_runtime_failure_are_truthful_and_durable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, head = repository(root)
            controller = start(root / "store", repo, head)
            rejected = controller.step(QueueBackend([
                request("PROPOSE_PATCH", {"patch": "not a diff", "proposed_paths": ["src/message.py"]})
            ]))
            self.assertEqual("REJECTED", rejected["projection"]["status"])
            self.assertEqual("PATCH_REJECTED", rejected["projection"]["application"])
            self.assertFalse(controller.status()["candidate_effect"])

        class FailedBackend(QueueBackend):
            def generate(self, messages, *, protocol, invocation, evidence_sink):
                self.calls += 1
                raise RuntimeError("simulated runtime failure")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, head = repository(root)
            controller = start(root / "store", repo, head)
            backend = FailedBackend([])
            with self.assertRaisesRegex(RuntimeError, "simulated runtime failure"):
                controller.step(backend)
            state = json.loads((controller.root / "session-state.json").read_text())
            self.assertEqual("ACTIVE", state["status"])
            self.assertEqual("RuntimeError", state["last_step_error"]["type"])
            self.assertEqual("INFERENCE_INTENT_DURABLE", controller.status()["pending_turn"]["phase"])
            self.assertEqual(0, controller.status()["current_turn"])

    def test_missing_authorized_read_can_progress_to_isolated_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, _ = repository(root)
            (repo / "src/message.py").unlink()
            subprocess.run(["git", "-C", str(repo), "add", "-u"], check=True)
            subprocess.run([
                "git", "-C", str(repo), "-c", "user.name=Test",
                "-c", "user.email=test@example.invalid", "commit", "-qm", "missing target",
            ], check=True)
            head = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
            ).strip()
            controller = start(root / "store", repo, head)

            observed = controller.step(QueueBackend([request("READ", {"path": "src/message.py"})]))
            self.assertEqual("PATH_NOT_FOUND", observed["authority_outcome"])
            self.assertEqual(
                {"status": "ERROR", "error": "PATH_NOT_FOUND"}, observed["projection"]
            )

            candidate_content = 'def message():\n    return "hello"\n'
            resumed = SupervisedWorkController(controller.root)
            accepted = resumed.step(QueueBackend([request("PROPOSE_PATCH", {
                "patch": new_file_patch("src/message.py", candidate_content),
                "proposed_paths": ["src/message.py"],
            })]))
            self.assertEqual("CANDIDATE_READY", accepted["terminal_disposition"])
            review = resumed.review()
            self.assertEqual(["src/message.py"], review["changed_paths"])
            self.assertEqual("SUCCESS", review["executor_application"])
            self.assertEqual("MATCH", review["source_state"])
            self.assertFalse((repo / "src/message.py").exists())
            self.assertTrue((resumed.root / "review-packet.json").is_file())


if __name__ == "__main__":
    unittest.main()
