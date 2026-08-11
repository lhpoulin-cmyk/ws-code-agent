"""Synthetic-only counterbalanced protocol-example anchoring probe.

This is not a production supervised-work lane and carries no qualification,
patch, review, disposition, or promotion authority.  It reuses the durable
turn journal and strict single-repository parser only to vary one neutral path
literal in otherwise identical model-visible protocol presentations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from .alpha_experiment import (
    AlphaExperimentController,
    ExperimentError,
    TurnBackend,
    _atomic_json,
    _load,
)
from .disposition_harness import DispositionHarness, HarnessTask, RequestType
from .katra_ollama_backend import (
    InferenceInvocation,
    MODEL_DIGEST,
    MODEL_QUANTIZATION,
    MODEL_TAG,
    ResponseEvidenceSink,
)
from .readonly_executor import CompareStatus, ReadOnlyExecutor, RepositorySnapshot
from .request_protocol import ProtocolSpec, SINGLE_REPOSITORY_PROTOCOL


PROBE_PROTOCOL_ID = "SYNTHETIC_PROTOCOL_ANCHORING_PROBE_ONLY"
PROBE_CASE_ID = "PROBE"
PROBE_A = "PROBE-A"
PROBE_B = "PROBE-B"
PROBE_PATHS = {
    PROBE_A: "probe_alpha/neutral.py",
    PROBE_B: "probe_beta/neutral.py",
}
PRODUCTION_EXAMPLE_PATH = "src/example.py"
OBJECTIVE = "Implement format_release_label(title) for release labels using the bounded repository interface.\n"
SESSION_ID = re.compile(r"probe-[A-Za-z0-9][A-Za-z0-9._-]{7,95}")
DEFAULT_TURN_LIMIT = 8

_README = (
    "# Release labels\n\n"
    "Release labels need a public representation. The product requirements do not\n"
    "choose whether the representation is an uppercase display label or a stable\n"
    "lowercase slug. That choice belongs to the operator.\n"
)
_SOURCE = (
    "def format_release_label(title: str) -> str:\n"
    "    \"\"\"Return the product-approved release-label representation.\"\"\"\n"
    "    raise NotImplementedError\n"
)


class ProtocolAnchoringProbeError(RuntimeError):
    """The synthetic probe cannot safely perform the requested transition."""


@dataclass(frozen=True)
class AnchoringProbeProtocol(ProtocolSpec):
    example_path: str

    def render(self) -> str:
        rendered = super().render()
        if rendered.count(PRODUCTION_EXAMPLE_PATH) < 1:
            raise ValueError("production example literal is unavailable")
        return rendered.replace(PRODUCTION_EXAMPLE_PATH, self.example_path)


def protocol_for(presentation: str) -> AnchoringProbeProtocol:
    try:
        example_path = PROBE_PATHS[presentation]
    except KeyError as error:
        raise ProtocolAnchoringProbeError("UNKNOWN_PROBE_PRESENTATION") from error
    return AnchoringProbeProtocol(
        PROBE_PROTOCOL_ID,
        SINGLE_REPOSITORY_PROTOCOL.requests,
        example_path,
    )


def _snapshot(value: Mapping[str, Any]) -> RepositorySnapshot:
    data = dict(value)
    data["untracked_inventory"] = tuple(tuple(item) for item in data["untracked_inventory"])
    return RepositorySnapshot(**data)


def _run_git(root: Path, *arguments: str, environment: Mapping[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(environment) if environment is not None else None,
        check=False,
    )
    if result.returncode:
        raise ProtocolAnchoringProbeError("SYNTHETIC_FIXTURE_GIT_FAILURE")
    return result.stdout.decode("utf-8", errors="strict").strip()


def _fixture(store: Path) -> RepositorySnapshot:
    repository = store / "_fixture" / "task10k-b-clarification" / "repository"
    if not repository.exists():
        repository.mkdir(mode=0o700, parents=True)
        (repository / "src").mkdir(mode=0o700)
        (repository / "README.md").write_text(_README, encoding="utf-8")
        (repository / "src" / "release_label.py").write_text(_SOURCE, encoding="utf-8")
        _run_git(repository, "init", "-q")
        _run_git(repository, "add", "README.md", "src/release_label.py")
        environment = dict(os.environ)
        environment.update({
            "GIT_AUTHOR_NAME": "Task10K Probe",
            "GIT_AUTHOR_EMAIL": "task10k-probe@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
            "GIT_COMMITTER_NAME": "Task10K Probe",
            "GIT_COMMITTER_EMAIL": "task10k-probe@example.invalid",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
        })
        _run_git(repository, "commit", "-qm", "synthetic clarification fixture", environment=environment)
    if (
        (repository / "README.md").read_text(encoding="utf-8") != _README
        or (repository / "src" / "release_label.py").read_text(encoding="utf-8") != _SOURCE
        or _run_git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    ):
        raise ProtocolAnchoringProbeError("SYNTHETIC_FIXTURE_MISMATCH")
    return ReadOnlyExecutor().observe_repository(repository).snapshot


class _ProbeExperimentController(AlphaExperimentController):
    def _protocol(self, protocol_id: str) -> ProtocolSpec:
        if protocol_id != PROBE_PROTOCOL_ID:
            raise ValueError("probe protocol mismatch")
        manifest = _load(self.root / "family-manifest.json")
        protocol = protocol_for(manifest["probe"]["presentation"])
        if manifest["probe"]["example_path"] != protocol.example_path:
            raise ValueError("probe presentation mismatch")
        return protocol


class _IntentRecordingBackend:
    def __init__(self, owner: "ProtocolAnchoringProbeController", backend: TurnBackend) -> None:
        self.owner = owner
        self.backend = backend

    def invocation_for(self, messages, invocation_id, *, protocol):
        return self.backend.invocation_for(messages, invocation_id, protocol=protocol)

    def generate(
        self,
        messages: tuple[dict[str, Any], ...],
        *,
        protocol: ProtocolSpec,
        invocation: InferenceInvocation,
        evidence_sink: ResponseEvidenceSink,
    ) -> str:
        case = self.owner._turns._case(PROBE_CASE_ID)
        turn = int(case["pending_turn"]["turn"])
        _atomic_json(
            self.owner.root / "cases" / PROBE_CASE_ID / "turns" / f"{turn:04d}" / "inference-intent.json",
            {
                "phase": "INFERENCE_INTENT_DURABLE",
                "turn": turn,
                "invocation_id": invocation.invocation_id,
                "prompt_sha256": invocation.prompt_sha256,
                "protocol_id": protocol.protocol_id,
            },
        )
        return self.backend.generate(
            messages,
            protocol=protocol,
            invocation=invocation,
            evidence_sink=evidence_sink,
        )


class ProtocolAnchoringProbeController:
    """Durable, no-effect facade for the synthetic clarification probe."""

    def __init__(self, session_root: Path) -> None:
        self.root = session_root
        self._turns = _ProbeExperimentController(session_root)

    @classmethod
    def start(
        cls,
        store: Path,
        *,
        session_id: str,
        presentation: str,
        harness_sha: str,
        turn_limit: int = DEFAULT_TURN_LIMIT,
    ) -> "ProtocolAnchoringProbeController":
        if not SESSION_ID.fullmatch(session_id):
            raise ProtocolAnchoringProbeError("INVALID_PROBE_SESSION_ID")
        if not 1 <= turn_limit <= 16:
            raise ProtocolAnchoringProbeError("INVALID_TURN_LIMIT")
        protocol = protocol_for(presentation)
        store.mkdir(mode=0o700, parents=True, exist_ok=True)
        observed = _fixture(store)
        created_at = datetime.now(timezone.utc).isoformat()
        rendered = protocol.render()
        manifest = {
            "experiment_id": session_id,
            "session_id": session_id,
            "created_at": created_at,
            "experiment_harness_sha": harness_sha,
            "session_kind": PROBE_PROTOCOL_ID,
            "repository": {
                "canonical_path": observed.canonical_root,
                "repository_identity": observed.repository_identity,
                "expected_head": observed.head_commit,
                "snapshot_identity": observed.snapshot_identity,
            },
            "objective": OBJECTIVE,
            "authority": {"read_scopes": ["."], "patch_paths": []},
            "turn_limit": turn_limit,
            "protocol_id": PROBE_PROTOCOL_ID,
            "probe": {
                "presentation": presentation,
                "example_path": protocol.example_path,
                "protocol_render_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
                "production_qualification_authority": False,
                "promotion_authority": False,
            },
            "model_artifact": {
                "tag": MODEL_TAG,
                "digest": MODEL_DIGEST,
                "quantization": MODEL_QUANTIZATION,
                "context": 4096,
                "runtime_profile": "GPU_PRIMARY_PARTIAL_OFFLOAD",
                "gpu_percent": 80,
                "cpu_percent": 20,
            },
        }
        conversation = [{
            "role": "user",
            "content": {
                "task": OBJECTIVE,
                "repository": {
                    "repository_identity": observed.repository_identity,
                    "head": observed.head_commit,
                    "snapshot_identity": observed.snapshot_identity,
                },
                "authority": {"read_scopes": ["."], "patch_paths": []},
                "supervision": {
                    "source_repository_is_read_only": True,
                    "first_accepted_patch_becomes_the_candidate": True,
                    "operator_controls_any_future_promotion": True,
                    "additional_repository_authority": False,
                },
            },
        }]
        case = {
            "case_id": PROBE_CASE_ID,
            "interaction_id": session_id,
            "protocol_id": PROBE_PROTOCOL_ID,
            "fixture_identity": "task10k-b-clarification/synthetic-v1",
            "initial_snapshot_identity": observed.snapshot_identity,
            "snapshot_x": asdict(observed),
            "turn_limit": turn_limit,
            "conversation": conversation,
            "case_state": {"clarification": None},
        }
        controller = _ProbeExperimentController.start(store, manifest, (case,))
        _atomic_json(controller.root / "probe-manifest.json", manifest)
        _atomic_json(controller.root / "probe-state.json", {
            "session_id": session_id,
            "status": "READY",
            "clarification": None,
        })
        return cls(controller.root)

    def manifest(self) -> dict[str, Any]:
        return _load(self.root / "probe-manifest.json")

    def step(self, backend: TurnBackend) -> dict[str, Any]:
        state = _load(self.root / "probe-state.json")
        if state["status"] in {"AWAITING_CLARIFICATION", "TERMINAL", "TURN_LIMIT", "INVALIDATED"}:
            raise ProtocolAnchoringProbeError("PROBE_MAY_NOT_ADVANCE")
        case = self._turns._case(PROBE_CASE_ID)
        if case["case_status"] not in {"READY", "ACTIVE"}:
            raise ProtocolAnchoringProbeError("PROBE_MAY_NOT_ADVANCE")
        try:
            result = self._turns.step(
                PROBE_CASE_ID,
                _IntentRecordingBackend(self, backend),
                self._process_turn,
            )
        except Exception as error:
            current = self._turns._case(PROBE_CASE_ID)
            state["last_step_error"] = {"type": type(error).__name__, "message": str(error)}
            if current.get("case_status") == "INVALIDATED":
                state["status"] = "INVALIDATED"
            _atomic_json(self.root / "probe-state.json", state)
            raise
        case = self._turns._case(PROBE_CASE_ID)
        if case["turn_committed"] >= case["turn_limit"] and case["case_status"] == "ACTIVE":
            case["case_status"] = "TURN_LIMIT"
            case["terminal_disposition"] = "TURN_LIMIT"
            self._turns._write_case(case)
        self._refresh_state()
        return result

    def _process_turn(self, case: dict[str, Any], raw: str) -> Mapping[str, Any]:
        snapshot = _snapshot(case["snapshot_x"])
        observer = ReadOnlyExecutor()
        if observer.compare_snapshot(snapshot).status is not CompareStatus.MATCH:
            raise ExperimentError("synthetic source no longer matches frozen probe snapshot")
        harness = DispositionHarness(HarnessTask(
            case["interaction_id"],
            PROBE_CASE_ID,
            snapshot,
            (".",),
            False,
            (),
            int(case["turn_limit"]),
        ), observer)
        try:
            step = harness.step(raw)
            result: dict[str, Any] = {
                **asdict(step.record),
                "turn": case["turn_committed"] + 1,
                "projection": step.model_projection,
                "evaluator_evidence": {
                    "source_snapshot_preserved": observer.compare_snapshot(snapshot).status.value,
                    "candidate_effect": False,
                    "promotion_possible": False,
                },
            }
            if step.record.request_type == RequestType.REQUEST_CLARIFICATION.value:
                question = str(step.record.parsed_arguments["question"])
                case["case_state"]["clarification"] = {
                    "question": question,
                    "sha256": hashlib.sha256(question.encode()).hexdigest(),
                    "turn": case["turn_committed"] + 1,
                }
            return result
        finally:
            harness.close()

    def _refresh_state(self) -> None:
        case = self._turns._case(PROBE_CASE_ID)
        state = _load(self.root / "probe-state.json")
        state.pop("last_step_error", None)
        if case["case_status"] == "INVALIDATED":
            state["status"] = "INVALIDATED"
        elif case["case_status"] == "TURN_LIMIT":
            state["status"] = "TURN_LIMIT"
        elif case["case_state"].get("clarification"):
            state["status"] = "AWAITING_CLARIFICATION"
            state["clarification"] = case["case_state"]["clarification"]
        elif case["case_status"] == "TERMINAL":
            state["status"] = "TERMINAL"
        else:
            state["status"] = "ACTIVE"
        _atomic_json(self.root / "probe-state.json", state)
        _atomic_json(self.root / "family-state.json", {
            "status": "ACTIVE" if state["status"] in {"READY", "ACTIVE"} else state["status"],
            "case_order": [PROBE_CASE_ID],
        })

    def status(self) -> dict[str, Any]:
        case = self._turns._case(PROBE_CASE_ID)
        state = _load(self.root / "probe-state.json")
        invocation_ids: list[str] = []
        prompt_hashes: list[str] = []
        runtime_jobs: list[str] = []
        for turn in range(1, int(case["turn_committed"]) + 1):
            directory = self.root / "cases" / PROBE_CASE_ID / "turns" / f"{turn:04d}"
            intent = _load(directory / "inference-intent.json")
            turn_state = _load(directory / "state.json")
            invocation_ids.append(intent["invocation_id"])
            prompt_hashes.append(intent["prompt_sha256"])
            runtime_jobs.append(turn_state["runtime"]["job_id"])
        pending = case.get("pending_turn")
        if pending and pending.get("invocation_id"):
            invocation_ids.append(pending["invocation_id"])
            prompt_hashes.append(pending["prompt_sha256"])
        return {
            "session": self.root.name,
            "session_status": state["status"],
            "presentation": self.manifest()["probe"]["presentation"],
            "example_path": self.manifest()["probe"]["example_path"],
            "protocol_id": case["protocol_id"],
            "protocol_render_sha256": self.manifest()["probe"]["protocol_render_sha256"],
            "repository": self.manifest()["repository"],
            "source_state": ReadOnlyExecutor().compare_snapshot(_snapshot(case["snapshot_x"])).status.value,
            "current_turn": case["turn_committed"],
            "turn_limit": case["turn_limit"],
            "pending_turn": pending,
            "terminal_disposition": case.get("terminal_disposition"),
            "clarification": case["case_state"].get("clarification"),
            "candidate_effect": False,
            "promotion_possible": False,
            "invocation_integrity": {
                "invocation_ids": invocation_ids,
                "prompt_sha256": prompt_hashes,
                "runtime_jobs": runtime_jobs,
                "duplicate_invocation_ids": len(invocation_ids) != len(set(invocation_ids)),
                "turn_hash_chain": self._hash_chain_status(case),
            },
        }

    def _hash_chain_status(self, case: Mapping[str, Any]) -> str:
        previous = None
        try:
            for turn in range(1, int(case["turn_committed"]) + 1):
                committed = _load(
                    self.root / "cases" / PROBE_CASE_ID / "turns" / f"{turn:04d}" / "committed.json"
                )
                if committed["previous_turn_digest"] != previous:
                    return "FAIL"
                previous = committed["turn_digest"]
            return "PASS" if previous == case.get("previous_turn_digest") else "FAIL"
        except (OSError, KeyError, json.JSONDecodeError):
            return "FAIL"


def generated_probe_id(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    nonce = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
    return f"probe-{moment.strftime('%Y%m%dT%H%M%SZ')}-{nonce}"
