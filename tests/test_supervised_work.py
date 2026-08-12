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
from ws_code_agent.katra_ollama_backend import (  # noqa: E402
    KatraOllamaDispositionBackend,
    Qwen25KatraOllamaDispositionBackend,
    RuntimeTurnEvidence,
)
from ws_code_agent import supervised_work as supervised_work_module  # noqa: E402
from ws_code_agent.supervised_work import (  # noqa: E402
    DEVSTRAL_CANDIDATE_ID,
    DEVSTRAL_V2_SESSION_KIND,
    QWEN25_CANDIDATE_ID,
    QWEN25_14B_INTERACTIVE_NORMALIZED_SESSION_KIND,
    QWEN25_V2_SESSION_KIND,
    QWEN25_32B_CANDIDATE_ID,
    QWEN25_32B_V2_SESSION_KIND,
    SYNTHETIC_V2_CLARIFICATION,
    SYNTHETIC_V2_SESSION_KIND,
    SYNTHETIC_V2_WRITE,
    TASK11A_FIXTURE_ID,
    TASK11A_INTERACTIVE_ACCEPTANCE_SESSION_KIND,
    SupervisedWorkController,
    SupervisedWorkError,
)
from ws_code_agent.response_normalization import ADAPTER_ID, ADAPTER_VERSION, STRICT_RAW  # noqa: E402
from ws_code_agent.request_protocol import (  # noqa: E402
    SINGLE_REPOSITORY_PROTOCOL_ID,
    VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL,
    VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
)


QUALIFICATION = ROOT / "docs/qualification/qwen3-coder-30b-alpha-v1.yaml"
DEVSTRAL_CANDIDATE = ROOT / "docs/qualification/devstral-small-2-v2-admission-candidate.yaml"
QWEN25_CANDIDATE = ROOT / "docs/qualification/qwen25-coder-14b-v2-admission-candidate.yaml"
QWEN25_32B_CANDIDATE = ROOT / "docs/qualification/qwen25-coder-32b-v2-admission-candidate.yaml"


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


class Qwen25QueueBackend(QueueBackend):
    def invocation_for(self, messages, invocation_id, *, protocol):
        return Qwen25KatraOllamaDispositionBackend.invocation_for(
            messages, invocation_id, protocol=protocol
        )


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

    def test_task11a_fixture_and_complete_entry_are_new_exact_and_prebound(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(
                SupervisedWorkError, "INTERACTIVE_ENTRY_DENIED_REQUIREMENTS_UNRESOLVED"
            ):
                SupervisedWorkController.start_task11a_interactive_acceptance(
                    root / "store",
                    session_id="work-task11a-unresolved-test",
                    candidate_path=QWEN25_CANDIDATE,
                    harness_sha="task11a-harness",
                    requirements_status="UNRESOLVED",
                )
            self.assertFalse((root / "store/_task11a-fixtures/work-task11a-unresolved-test").exists())

            controller = SupervisedWorkController.start_task11a_interactive_acceptance(
                root / "store",
                session_id="work-task11a-positive-test",
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="task11a-harness",
                requirements_status="COMPLETE",
            )
            manifest = controller.manifest()
            case = controller._turns._case("WORK")
            repository = Path(manifest["repository"]["canonical_path"])
            self.assertEqual(TASK11A_INTERACTIVE_ACCEPTANCE_SESSION_KIND, manifest["session_kind"])
            self.assertEqual(TASK11A_FIXTURE_ID, case["fixture_identity"])
            self.assertEqual('def message():\n    return "hi"\n', (repository / "src/message.py").read_text())
            self.assertEqual(
                'Change message() in src/message.py so that calling message()\n'
                'returns exactly the string "hello".\n\nMake no other functional change.\n',
                manifest["objective"],
            )
            self.assertEqual(["."], manifest["authority"]["read_scopes"])
            self.assertEqual(["src/message.py"], manifest["authority"]["patch_paths"])
            self.assertEqual("COMPLETE", manifest["interactive_work_boundary"]["requirements_status"])
            self.assertEqual("INTERACTIVE_ENTRY_ACCEPTED", manifest["interactive_work_boundary"]["entry_status"])
            self.assertEqual(
                ["task10k-c-write-visible-v1", "task10k-c-write-hidden-v1"],
                manifest["validation"]["authorized_validation_ids"],
            )
            self.assertEqual(
                "98f2f772b26b287735956a41fe7972e3d33cdfa364e15025951068e23afd49d7",
                manifest["fixture"]["content_sha256"],
            )
            self.assertEqual(
                "0e3358da82716ecf114edb4359fc1aafbf506d89f2d0911c5d8fe4ba49ec805e",
                manifest["fixture"]["contract_sha256"],
            )
            self.assertEqual("MATCH", controller.status()["source_state"])
            self.assertEqual(0, controller.status()["current_turn"])

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

    def test_qwen25_interactive_normalized_lane_is_durable_and_strict_raw_is_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            strict = SupervisedWorkController.start_qwen25_v2_admission(
                root / "store",
                session_id="work-qwen25-strict-separation",
                fixture_kind=SYNTHETIC_V2_WRITE,
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="frozen-harness",
            )
            normalized = SupervisedWorkController.start_qwen25_interactive_normalized(
                root / "store",
                session_id="work-qwen25-normalized-separation",
                fixture_kind=SYNTHETIC_V2_WRITE,
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="frozen-harness",
                requirements_status="COMPLETE",
            )
            self.assertEqual(
                {"mode": STRICT_RAW, "adapter_id": "NONE", "adapter_version": None},
                strict.manifest()["response_adapter"],
            )
            expected = {
                "mode": "INTERACTIVE_NORMALIZED",
                "adapter_id": ADAPTER_ID,
                "adapter_version": ADAPTER_VERSION,
            }
            self.assertEqual(QWEN25_14B_INTERACTIVE_NORMALIZED_SESSION_KIND, normalized.manifest()["session_kind"])
            self.assertEqual(expected, normalized.manifest()["response_adapter"])
            self.assertEqual(expected, normalized.status()["response_adapter"])
            self.assertEqual(expected, normalized._turns._case("WORK")["response_adapter"])
            self.assertEqual(
                ["task10k-c-write-visible-v1", "task10k-c-write-hidden-v1"],
                normalized.manifest()["validation"]["authorized_validation_ids"],
            )

            strict_content = strict._turns._case("WORK")["conversation"][0]["content"]
            normalized_content = normalized._turns._case("WORK")["conversation"][0]["content"]
            comparable = json.loads(json.dumps(normalized_content))
            comparable["repository"] = strict_content["repository"]
            self.assertEqual(strict_content, comparable)

            state_path = normalized.root / "session-state.json"
            state = json.loads(state_path.read_text())
            state["response_adapter"] = {
                "mode": STRICT_RAW, "adapter_id": "NONE", "adapter_version": None,
            }
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(SupervisedWorkError, "RESPONSE_ADAPTER_BINDING_MISMATCH"):
                SupervisedWorkController(normalized.root).status()

    def test_normalized_lane_preserves_raw_and_parses_only_exact_fence_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            controller = SupervisedWorkController.start_qwen25_interactive_normalized(
                root / "store",
                session_id="work-qwen25-normalized-evidence",
                fixture_kind=SYNTHETIC_V2_WRITE,
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="frozen-harness",
                requirements_status="COMPLETE",
            )
            payload = request("NO_CHANGE", {})
            raw = f"```json\n{payload}\n```"
            result = controller.step(Qwen25QueueBackend([raw]))
            turn = controller.root / "cases/WORK/turns/0001"
            self.assertEqual(raw.encode(), (turn / "raw-response.txt").read_bytes())
            self.assertEqual(payload.encode(), (turn / "normalized-parser-input.txt").read_bytes())
            evidence = json.loads((turn / "normalization-evidence.json").read_text())
            self.assertTrue(evidence["transformation_applied"])
            self.assertEqual("SINGLE_MARKDOWN_JSON_FENCE_REMOVED", evidence["transformation_classification"])
            self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), result["raw_sha256"])
            self.assertEqual(hashlib.sha256(payload.encode()).hexdigest(), result["parser_input_sha256"])
            self.assertEqual("NO_CHANGE", result["request_type"])
            self.assertEqual("NO_CHANGE", result["terminal_disposition"])

    def test_normalized_lane_does_not_change_patch_authority_or_strict_raw_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw_request = request("PROPOSE_PATCH", {
                "patch": new_file_patch("src/other.py", 'VALUE = "hello"\n'),
                "proposed_paths": ["src/other.py"],
            })
            fenced = f"```json\n{raw_request}\n```"
            normalized = SupervisedWorkController.start_qwen25_interactive_normalized(
                root / "store",
                session_id="work-qwen25-normalized-authority",
                fixture_kind=SYNTHETIC_V2_WRITE,
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="frozen-harness",
                requirements_status="COMPLETE",
            )
            denied = normalized.step(Qwen25QueueBackend([fenced]))
            self.assertEqual("DENIED_SCOPE", denied["authority_outcome"])
            self.assertFalse(normalized.status()["candidate_effect"])

            strict = SupervisedWorkController.start_qwen25_v2_admission(
                root / "store",
                session_id="work-qwen25-strict-fence",
                fixture_kind=SYNTHETIC_V2_CLARIFICATION,
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="frozen-harness",
            )
            malformed = strict.step(Qwen25QueueBackend([
                f"```json\n{request('REQUEST_CLARIFICATION', {'question': 'Which representation is required?'})}\n```"
            ]))
            self.assertEqual("MALFORMED_REQUEST", malformed["terminal_disposition"])
            self.assertFalse((strict.root / "cases/WORK/turns/0001/normalized-parser-input.txt").exists())

    def test_interactive_boundary_requires_complete_validated_entry_and_persists_handoff(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(
                SupervisedWorkError, "INTERACTIVE_ENTRY_DENIED_REQUIREMENTS_UNRESOLVED"
            ):
                SupervisedWorkController.start_qwen25_interactive_normalized(
                    root / "store",
                    session_id="work-qwen25-unresolved-entry",
                    fixture_kind=SYNTHETIC_V2_WRITE,
                    candidate_path=QWEN25_CANDIDATE,
                    harness_sha="frozen-harness",
                    requirements_status="UNRESOLVED",
                )
            self.assertFalse((root / "store/_synthetic-v2-fixtures/work-qwen25-unresolved-entry").exists())

            with self.assertRaisesRegex(
                SupervisedWorkError, "INTERACTIVE_ENTRY_DENIED_VALIDATION_DESCRIPTORS_CONFIGURED"
            ):
                SupervisedWorkController.start_qwen25_interactive_normalized(
                    root / "store",
                    session_id="work-qwen25-no-validator-entry",
                    fixture_kind=SYNTHETIC_V2_CLARIFICATION,
                    candidate_path=QWEN25_CANDIDATE,
                    harness_sha="frozen-harness",
                    requirements_status="COMPLETE",
                )

            corrupt = request("PROPOSE_PATCH", {
                "patch": "diff --git a/src/message.py b/src/message.py\ncorrupt\n",
                "proposed_paths": ["src/message.py"],
            })
            controller = SupervisedWorkController.start_qwen25_interactive_normalized(
                root / "store",
                session_id="work-qwen25-policy-handoff",
                fixture_kind=SYNTHETIC_V2_WRITE,
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="frozen-harness",
                requirements_status="COMPLETE",
            )
            boundary = controller.manifest()["interactive_work_boundary"]
            self.assertEqual("INTERACTIVE_BOUNDED_WORK_V1", boundary["policy_id"])
            self.assertEqual("COMPLETE", boundary["requirements_status"])
            self.assertFalse(boundary["automatic_cross_model_invocation"])

            controller.step(Qwen25QueueBackend([corrupt]))
            self.assertEqual("REPAIR_OPPORTUNITY", controller.status()["interactive_policy"]["state"])
            controller.step(Qwen25QueueBackend([request("NO_CHANGE", {})]))
            status = controller.status()
            self.assertEqual("ESCALATION_REQUIRED", status["session_status"])
            self.assertEqual("INTERACTIVE_RECOVERY_FAILED", status["interactive_policy"]["classification"])
            packet = json.loads(
                (controller.root / "evaluator/handoff-packet.json").read_text(encoding="utf-8")
            )
            self.assertEqual("DELIBERATIVE_OVERNIGHT_CODER", packet["recommended_next_worker"])
            self.assertEqual("NO_CHANGE_AFTER_PATCH_REJECTED", packet["reason"])
            self.assertEqual(2, len(packet["turn_sequence"]))
            self.assertFalse(packet["automatic_handoff_performed"])
            self.assertNotIn("implementation", json.dumps(packet["validation_outcomes"]))

            candidate_controller = SupervisedWorkController.start_qwen25_interactive_normalized(
                root / "store",
                session_id="work-qwen25-policy-validation-required",
                fixture_kind=SYNTHETIC_V2_WRITE,
                candidate_path=QWEN25_CANDIDATE,
                harness_sha="frozen-harness",
                requirements_status="COMPLETE",
            )
            valid_patch = request("PROPOSE_PATCH", {
                "patch": new_file_patch("src/message.py", 'def message():\n    return "hello"\n'),
                "proposed_paths": ["src/message.py"],
            })
            candidate_controller.step(Qwen25QueueBackend([valid_patch]))
            self.assertEqual("VALIDATION_REQUIRED", candidate_controller.status()["session_status"])
            with self.assertRaisesRegex(SupervisedWorkError, "OPERATOR_REVIEW_NOT_READY"):
                candidate_controller.disposition("APPROVE")

    def test_qwen25_32b_admission_binding_is_exact_separate_and_stale_safe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write = SupervisedWorkController.start_qwen25_32b_v2_admission(
                root / "store",
                session_id="work-qwen25-32b-write-test",
                fixture_kind=SYNTHETIC_V2_WRITE,
                candidate_path=QWEN25_32B_CANDIDATE,
                harness_sha="frozen-harness",
            )
            manifest = write.manifest()
            self.assertEqual(QWEN25_32B_V2_SESSION_KIND, manifest["session_kind"])
            self.assertNotEqual(QWEN25_V2_SESSION_KIND, manifest["session_kind"])
            self.assertEqual(QWEN25_32B_CANDIDATE_ID, manifest["qualification"]["candidate_id"])
            self.assertNotEqual(QWEN25_CANDIDATE_ID, manifest["qualification"]["candidate_id"])
            self.assertEqual("qwen2.5-coder:32b-instruct-q4_K_M", manifest["model_artifact"]["tag"])
            self.assertEqual(
                "b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41",
                manifest["model_artifact"]["digest"],
            )
            self.assertEqual(
                "ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9",
                manifest["model_artifact"]["model_blob"],
            )
            self.assertEqual("qwen25-coder-32b-katra-4096", manifest["model_artifact"]["runtime_profile_id"])
            self.assertEqual("GPU_PRIMARY_PARTIAL_OFFLOAD", manifest["model_artifact"]["runtime_profile"])
            self.assertEqual((71, 29), (
                manifest["model_artifact"]["minimum_gpu_percent"],
                manifest["model_artifact"]["maximum_cpu_percent"],
            ))
            self.assertEqual(4096, manifest["model_artifact"]["context"])
            self.assertEqual(["."], manifest["authority"]["read_scopes"])
            self.assertEqual(["src/message.py"], manifest["authority"]["patch_paths"])
            self.assertEqual(8, manifest["turn_limit"])
            self.assertEqual("task10k-c-write/synthetic-v1", write._turns._case("WORK")["fixture_identity"])
            self.assertEqual(0, write._turns._case("WORK")["turn_committed"])

            source = QWEN25_32B_CANDIDATE.read_text(encoding="utf-8")
            replacements = {
                "wrong-candidate": ("candidate_id: qwen25-coder-32b-q4", "candidate_id: qwen25-coder-14b-q4"),
                "wrong-status": ("status: RUNTIME_ACCEPTED", "status: SELECTED_FOR_EVALUATION"),
                "wrong-digest": ("b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41", "0" * 64),
                "wrong-blob": ("ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9", "0" * 64),
                "wrong-tag": ("qwen2.5-coder:32b-instruct-q4_K_M", "qwen2.5-coder:14b-instruct-q4_K_M"),
                "wrong-quantization": ("  quantization: Q4_K_M", "  quantization: Q4_0"),
                "wrong-profile": ("qwen25-coder-32b-katra-4096", "qwen25-coder-14b-katra-4096"),
                "wrong-context": ("  context: 4096", "  context: 8192"),
                "wrong-generation": ("  generation_overrides: NONE", "  generation_overrides: temperature=0"),
                "wrong-execution": ("  execution: GPU_PRIMARY_PARTIAL_OFFLOAD", "  execution: GPU_ONLY"),
                "wrong-gpu": ("  minimum_gpu_percent: 71", "  minimum_gpu_percent: 70"),
                "wrong-cpu": ("  maximum_cpu_percent: 29", "  maximum_cpu_percent: 30"),
                "wrong-runtime": ("  ollama_version: 0.32.0+helix.repeatlimit.1", "  ollama_version: 0.32.0"),
                "wrong-binary": ("  binary_sha256: b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143", "  binary_sha256: " + "0" * 64),
                "wrong-build": ("  build_id: ffd1f9f6c8ffd69fdca1316e7c032447479fe139", "  build_id: " + "0" * 40),
                "wrong-deviation": ("  runtime_deviation: OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1", "  runtime_deviation: NONE"),
                "wrong-protocol": ("  protocol_id: WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE", "  protocol_id: WS_CODE_AGENT_REQUEST_PROTOCOL_V1_SINGLE"),
                "wrong-admission": ("  production_admission: NOT_EVALUATED", "  production_admission: PASS"),
            }
            for name, (old, new) in replacements.items():
                altered = root / f"{name}.yaml"
                altered.write_text(source.replace(old, new), encoding="utf-8")
                with self.subTest(name=name), self.assertRaisesRegex(
                    SupervisedWorkError, "CHALLENGER_BINDING_MISMATCH"
                ):
                    supervised_work_module._qwen25_32b_candidate_binding(altered)

            cli = (ROOT / "tools/run_supervised_work.py").read_text(encoding="utf-8")
            self.assertIn('sub.add_parser("start-qwen25-v2")', cli)
            self.assertIn('sub.add_parser("start-qwen25-interactive-normalized")', cli)
            self.assertIn('sub.add_parser("start-qwen25-32b-v2")', cli)
            self.assertIn("elif digest == QWEN25_MODEL_DIGEST:", cli)
            self.assertIn("elif digest == QWEN25_32B_MODEL_DIGEST:", cli)
            self.assertIn("backend = Qwen25KatraOllamaDispositionBackend()", cli)
            self.assertIn("backend = Qwen25_32BKatraOllamaDispositionBackend()", cli)

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
