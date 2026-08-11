from __future__ import annotations

import hashlib
import inspect
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
from ws_code_agent import supervised_work as supervised_work_module  # noqa: E402
from ws_code_agent.supervised_work import (  # noqa: E402
    DEVSTRAL_CANDIDATE_ID,
    DEVSTRAL_V2_SESSION_KIND,
    QWEN25_CANDIDATE_ID,
    QWEN25_V2_SESSION_KIND,
    SYNTHETIC_V2_CLARIFICATION,
    SYNTHETIC_V2_SESSION_KIND,
    SYNTHETIC_V2_WRITE,
    SupervisedWorkController,
    SupervisedWorkError,
)
from ws_code_agent.request_protocol import (  # noqa: E402
    SINGLE_REPOSITORY_PROTOCOL_ID,
    VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL,
    VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
)


QUALIFICATION = ROOT / "docs/qualification/qwen3-coder-30b-alpha-v1.yaml"
DEVSTRAL_CANDIDATE = ROOT / "docs/qualification/devstral-small-2-v2-admission-candidate.yaml"
QWEN25_CANDIDATE = ROOT / "docs/qualification/qwen25-coder-14b-v2-admission-candidate.yaml"


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


def candidate_qualification(root: Path) -> Path:
    path = root / "candidate-qualification.yaml"
    text = QUALIFICATION.read_text(encoding="utf-8")
    text = text.replace(
        "  qualification_status: SUPERVISED_SYNTHETIC_ACCEPTED",
        "  qualification_status: CANDIDATE",
    ).replace(
        "  synthetic_acceptance: PASS",
        "  synthetic_acceptance: PENDING",
    ).replace(
        "  synthetic_acceptance: FAIL",
        "  synthetic_acceptance: PENDING",
    ).replace(
        "  production_qualified: true",
        "  production_qualified: false",
    )
    path.write_text(text, encoding="utf-8")
    return path


def accepted_v2_qualification(root: Path) -> Path:
    path = root / "accepted-v2-qualification.yaml"
    text = QUALIFICATION.read_text(encoding="utf-8")
    text = text.replace(
        "  qualification_status: CANDIDATE",
        "  qualification_status: SUPERVISED_SYNTHETIC_ACCEPTED",
    ).replace(
        "  synthetic_acceptance: PENDING",
        "  synthetic_acceptance: PASS",
    ).replace(
        "  synthetic_acceptance: FAIL",
        "  synthetic_acceptance: PASS",
    ).replace(
        "  production_qualified: false",
        "  production_qualified: true",
    ).replace(
        "    status: NOT_ADMITTED",
        "    status: ADMITTED",
        1,
    )
    path.write_text(text, encoding="utf-8")
    return path


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
        qualification_path=accepted_v2_qualification(store.parent),
        harness_sha="test-harness",
        turn_limit=3,
    )


class SupervisedWorkTests(unittest.TestCase):
    def test_qwen25_selector_preserves_frozen_v2_and_fixture_bytes(self):
        self.assertEqual(
            "3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e",
            hashlib.sha256(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.render().encode()).hexdigest(),
        )
        fixtures = (
            (
                supervised_work_module._WRITE_OBJECTIVE,
                supervised_work_module._WRITE_README,
                "",
                "task10k-c-write/synthetic-v1",
                (".",),
                ("src/message.py",),
                "db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6",
            ),
            (
                supervised_work_module._CLARIFICATION_OBJECTIVE,
                supervised_work_module._CLARIFICATION_README,
                supervised_work_module._CLARIFICATION_SOURCE,
                "task10k-c-clarification/synthetic-v1",
                (".",),
                (),
                "b0f5cdd341a2eb491ddcd9f02253563cbc0a44d79eccf86b3a3519cfdb13b3ba",
            ),
        )
        for objective, readme, source, identity, reads, patches, expected in fixtures:
            payload = json.dumps(
                [objective, readme, source, identity, reads, patches],
                separators=(",", ":"),
            ).encode()
            self.assertEqual(expected, hashlib.sha256(payload).hexdigest())

    def test_manifest_binds_clean_source_explicit_scope_and_qualification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo, head = repository(root)
            controller = start(root / "store", repo, head)
            manifest = controller.manifest()
            self.assertEqual(["src"], manifest["authority"]["read_scopes"])
            self.assertEqual(["src/message.py"], manifest["authority"]["patch_paths"])
            self.assertEqual("SUPERVISED_SINGLE_REPO", manifest["qualification"]["operating_class"])
            self.assertEqual(
                VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
                manifest["protocol_id"],
            )
            self.assertTrue(manifest["protocol_qualification"]["production_qualified"])
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

    def test_qwen_qualification_closes_production_and_synthetic_admission(self):
        text = QUALIFICATION.read_text(encoding="utf-8")
        self.assertIn("  status: NOT_ADMITTED", text)
        self.assertIn("  synthetic_acceptance: FAIL", text)
        self.assertIn("  production_qualified: false", text)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo, head = repository(root)
            with self.assertRaisesRegex(
                SupervisedWorkError,
                "PROTOCOL_QUALIFICATION_MISMATCH",
            ):
                SupervisedWorkController.start(
                    root / "closed-store",
                    session_id="work-qwen-closed-production",
                    repository=repo,
                    expected_head=head,
                    objective="Change the message as requested.",
                    read_scopes=("src",),
                    patch_paths=("src/message.py",),
                    qualification_path=QUALIFICATION,
                    harness_sha="test-harness",
                )
            with self.assertRaisesRegex(
                SupervisedWorkError,
                "V2_CANDIDATE_SESSION_NOT_AUTHORIZED",
            ):
                SupervisedWorkController.start_synthetic_v2(
                    root / "closed-synthetic-store",
                    session_id="work-qwen-closed-synthetic",
                    fixture_kind=SYNTHETIC_V2_WRITE,
                    qualification_path=QUALIFICATION,
                    harness_sha="test-harness",
                )

    def test_value_free_v2_is_candidate_only_and_uses_fixed_synthetic_fixtures(self):
        self.assertNotIn(
            "protocol_id",
            inspect.signature(SupervisedWorkController.start).parameters,
        )
        self.assertNotIn(
            "repository",
            inspect.signature(SupervisedWorkController.start_synthetic_v2).parameters,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write = SupervisedWorkController.start_synthetic_v2(
                root / "store",
                session_id="work-v2-write-test",
                fixture_kind=SYNTHETIC_V2_WRITE,
                qualification_path=candidate_qualification(root),
                harness_sha="test-harness",
            )
            manifest = write.manifest()
            self.assertEqual(SYNTHETIC_V2_SESSION_KIND, manifest["session_kind"])
            self.assertEqual(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID, manifest["protocol_id"])
            self.assertEqual(
                {
                    "id": VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
                    "qualification_status": "CANDIDATE",
                    "production_qualified": False,
                    "synthetic_acceptance": "PENDING",
                    "operating_class": "SUPERVISED_SINGLE_REPO",
                    "alpha_evaluation_protocol": SINGLE_REPOSITORY_PROTOCOL_ID,
                },
                manifest["protocol_qualification"],
            )
            self.assertEqual(["."], manifest["authority"]["read_scopes"])
            self.assertEqual(["src/message.py"], manifest["authority"]["patch_paths"])
            self.assertNotIn("repositories", manifest)
            self.assertTrue(
                Path(manifest["repository"]["canonical_path"]).is_relative_to(
                    root / "store" / "_synthetic-v2-fixtures"
                )
            )

            clarification = SupervisedWorkController.start_synthetic_v2(
                root / "store",
                session_id="work-v2-clarification-test",
                fixture_kind=SYNTHETIC_V2_CLARIFICATION,
                qualification_path=candidate_qualification(root),
                harness_sha="test-harness",
            )
            self.assertEqual([], clarification.manifest()["authority"]["patch_paths"])
            self.assertEqual(
                VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
                clarification.status()["protocol_id"],
            )

            repo, head = repository(root / "accepted-production")
            accepted = SupervisedWorkController.start(
                root / "accepted-store",
                session_id="work-v2-accepted-production",
                repository=repo,
                expected_head=head,
                objective="Change the message as requested.",
                read_scopes=("src",),
                patch_paths=("src/message.py",),
                qualification_path=accepted_v2_qualification(root),
                harness_sha="test-harness",
            )
            self.assertEqual(
                VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
                accepted.manifest()["protocol_id"],
            )
            with self.assertRaisesRegex(
                SupervisedWorkError,
                "V2_CANDIDATE_SESSION_NOT_AUTHORIZED",
            ):
                SupervisedWorkController.start_synthetic_v2(
                    root / "accepted-candidate-store",
                    session_id="work-v2-accepted-candidate",
                    fixture_kind=SYNTHETIC_V2_WRITE,
                    qualification_path=accepted_v2_qualification(root),
                    harness_sha="test-harness",
                )

    def test_devstral_admission_uses_exact_candidate_and_frozen_v2_fixtures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write = SupervisedWorkController.start_devstral_v2_admission(
                root / "store",
                session_id="work-devstral-write-test",
                fixture_kind=SYNTHETIC_V2_WRITE,
                candidate_path=DEVSTRAL_CANDIDATE,
                harness_sha="frozen-harness",
            )
            manifest = write.manifest()
            self.assertEqual(DEVSTRAL_V2_SESSION_KIND, manifest["session_kind"])
            self.assertEqual(DEVSTRAL_CANDIDATE_ID, manifest["qualification"]["candidate_id"])
            self.assertEqual(
                "24277f07f62db8f9cb68e9dfc679ea1818a7fbac47a50eff0a701d3f645b63c8",
                manifest["model_artifact"]["digest"],
            )
            self.assertEqual(
                "devstral-small-2-24b-katra-partial",
                manifest["model_artifact"]["runtime_profile_id"],
            )
            self.assertEqual(88, manifest["model_artifact"]["minimum_gpu_percent"])
            self.assertEqual(12, manifest["model_artifact"]["maximum_cpu_percent"])
            self.assertEqual(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID, manifest["protocol_id"])
            self.assertEqual(["."], manifest["authority"]["read_scopes"])
            self.assertEqual(["src/message.py"], manifest["authority"]["patch_paths"])
            self.assertEqual(
                "task10k-c-write/synthetic-v1",
                write._turns._case("WORK")["fixture_identity"],
            )

            clarification = SupervisedWorkController.start_devstral_v2_admission(
                root / "store",
                session_id="work-devstral-clarification-test",
                fixture_kind=SYNTHETIC_V2_CLARIFICATION,
                candidate_path=DEVSTRAL_CANDIDATE,
                harness_sha="frozen-harness",
            )
            self.assertEqual([], clarification.manifest()["authority"]["patch_paths"])
            self.assertEqual(
                "task10k-c-clarification/synthetic-v1",
                clarification._turns._case("WORK")["fixture_identity"],
            )

            altered = root / "altered-candidate.yaml"
            altered.write_text(
                DEVSTRAL_CANDIDATE.read_text(encoding="utf-8").replace(
                    "minimum_gpu_percent: 88", "minimum_gpu_percent: 80"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SupervisedWorkError, "CHALLENGER_BINDING_MISMATCH"):
                SupervisedWorkController.start_devstral_v2_admission(
                    root / "altered-store",
                    session_id="work-devstral-altered-test",
                    fixture_kind=SYNTHETIC_V2_WRITE,
                    candidate_path=altered,
                    harness_sha="frozen-harness",
                )

    def test_qwen25_admission_uses_exact_candidate_and_rejects_stale_bindings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write = SupervisedWorkController.start_qwen25_v2_admission(
                root / "store",
                session_id="work-qwen25-write-test",
                fixture_kind=SYNTHETIC_V2_WRITE,
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="frozen-harness",
            )
            manifest = write.manifest()
            self.assertEqual(QWEN25_V2_SESSION_KIND, manifest["session_kind"])
            self.assertEqual(QWEN25_CANDIDATE_ID, manifest["qualification"]["candidate_id"])
            self.assertEqual(
                "qwen2.5-coder:14b-instruct-q4_K_M", manifest["model_artifact"]["tag"]
            )
            self.assertEqual(
                "9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849",
                manifest["model_artifact"]["digest"],
            )
            self.assertEqual("qwen25-coder-14b-katra-4096", manifest["model_artifact"]["runtime_profile_id"])
            self.assertEqual((100, 0), (
                manifest["model_artifact"]["minimum_gpu_percent"],
                manifest["model_artifact"]["maximum_cpu_percent"],
            ))
            self.assertEqual(4096, manifest["model_artifact"]["context"])
            self.assertEqual(["."], manifest["authority"]["read_scopes"])
            self.assertEqual(["src/message.py"], manifest["authority"]["patch_paths"])
            self.assertEqual(8, manifest["turn_limit"])
            self.assertEqual("task10k-c-write/synthetic-v1", write._turns._case("WORK")["fixture_identity"])

            clarification = SupervisedWorkController.start_qwen25_v2_admission(
                root / "store",
                session_id="work-qwen25-clarification-test",
                fixture_kind=SYNTHETIC_V2_CLARIFICATION,
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="frozen-harness",
            )
            self.assertEqual([], clarification.manifest()["authority"]["patch_paths"])
            self.assertEqual(8, clarification.manifest()["turn_limit"])
            self.assertEqual(
                "task10k-c-clarification/synthetic-v1",
                clarification._turns._case("WORK")["fixture_identity"],
            )

            replacements = {
                "wrong-digest": (
                    "9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849",
                    "0" * 64,
                ),
                "wrong-tag": (
                    "qwen2.5-coder:14b-instruct-q4_K_M",
                    "qwen2.5-coder:14b-instruct-q4_0",
                ),
                "wrong-profile": (
                    "qwen25-coder-14b-katra-4096",
                    "devstral-small-2-24b-katra-partial",
                ),
            }
            source = QWEN25_CANDIDATE.read_text(encoding="utf-8")
            for name, (old, new) in replacements.items():
                altered = root / f"{name}.yaml"
                altered.write_text(source.replace(old, new), encoding="utf-8")
                with self.subTest(name=name), self.assertRaisesRegex(
                    SupervisedWorkError, "CHALLENGER_BINDING_MISMATCH"
                ):
                    SupervisedWorkController.start_qwen25_v2_admission(
                        root / f"{name}-store",
                        session_id=f"work-qwen25-{name}",
                        fixture_kind=SYNTHETIC_V2_WRITE,
                        candidate_path=altered,
                        harness_sha="frozen-harness",
                    )

    def test_value_free_v2_synthetic_write_and_clarification_use_normal_durable_lane(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write = SupervisedWorkController.start_synthetic_v2(
                root / "store",
                session_id="work-v2-write-flow",
                fixture_kind=SYNTHETIC_V2_WRITE,
                qualification_path=candidate_qualification(root),
                harness_sha="test-harness",
            )
            observed = write.step(QueueBackend([
                request("READ", {"path": "src/message.py"}),
            ]))
            self.assertEqual("PATH_NOT_FOUND", observed["authority_outcome"])
            candidate_content = 'def message():\n    return "hello"\n'
            accepted = SupervisedWorkController(write.root).step(QueueBackend([
                request("PROPOSE_PATCH", {
                    "patch": new_file_patch("src/message.py", candidate_content),
                    "proposed_paths": ["src/message.py"],
                }),
            ]))
            self.assertEqual("CANDIDATE_READY", accepted["terminal_disposition"])
            review = write.review()
            self.assertEqual(["src/message.py"], review["changed_paths"])
            self.assertEqual(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID, review["protocol_id"])
            self.assertEqual("MATCH", review["source_state"])
            self.assertFalse(
                Path(write.manifest()["repository"]["canonical_path"], "src/message.py").exists()
            )
            intent = json.loads(
                (write.root / "cases/WORK/turns/0001/inference-intent.json").read_text()
            )
            self.assertEqual(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID, intent["protocol_id"])

            clarification = SupervisedWorkController.start_synthetic_v2(
                root / "store",
                session_id="work-v2-clarification-flow",
                fixture_kind=SYNTHETIC_V2_CLARIFICATION,
                qualification_path=candidate_qualification(root),
                harness_sha="test-harness",
            )
            question = "Should the representation be display-oriented or identifier-oriented?"
            clarification.step(QueueBackend([
                request("REQUEST_CLARIFICATION", {"question": question}),
            ]))
            status = SupervisedWorkController(clarification.root).status()
            self.assertEqual("AWAITING_CLARIFICATION", status["session_status"])
            self.assertEqual(question, status["clarification"]["question"])
            self.assertFalse(status["candidate_effect"])

    def test_value_free_v2_cannot_broaden_to_second_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            controller = SupervisedWorkController.start_synthetic_v2(
                Path(temporary) / "store",
                session_id="work-v2-cross-repo",
                fixture_kind=SYNTHETIC_V2_WRITE,
                qualification_path=candidate_qualification(Path(temporary)),
                harness_sha="test-harness",
            )
            denied = controller.step(QueueBackend([
                request("READ", {"path": "../peer/target"}),
            ]))
            self.assertEqual("SUPERVISION_REQUIRED_CROSS_REPOSITORY", denied["authority_outcome"])
            self.assertFalse(controller.status()["candidate_effect"])

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
