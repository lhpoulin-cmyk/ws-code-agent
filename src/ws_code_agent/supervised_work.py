"""Durable supervised single-repository work sessions.

This module is a production lane, not an Alpha case and not a promotion
mechanism.  It reuses the durable turn journal and fixed inference backend while
keeping the operator repository frozen and every candidate effect isolated.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

from .alpha_experiment import AlphaExperimentController, ExperimentError, TurnBackend, _atomic_bytes, _atomic_json, _load
from .disposition_harness import DispositionHarness, HarnessTask, RequestType, parse_request
from .isolated_patch import IsolatedPatchExecutor, PatchProposal
from .katra_ollama_backend import InferenceInvocation, MODEL_DIGEST, MODEL_QUANTIZATION, MODEL_TAG, ResponseEvidenceSink
from .readonly_executor import CompareStatus, ReadOnlyExecutor, RepositorySnapshot
from .request_protocol import SINGLE_REPOSITORY_PROTOCOL_ID


WORK_CASE_ID = "WORK"
OPERATING_CLASS = "SUPERVISED_SINGLE_REPO"
QUALIFICATION_ID = "qwen3-coder-30b-alpha-v1"
ALPHA_VERSION = "HELIX_CODE_AGENT_ALPHA_V1"
DEFAULT_TURN_LIMIT = 8
MAX_OBJECTIVE_BYTES = 16_384
MAX_SCOPES = 8
MAX_PATCH_PATHS = 8
SESSION_ID = re.compile(r"work-[A-Za-z0-9][A-Za-z0-9._-]{7,95}")


class SupervisedWorkError(RuntimeError):
    """The supervised session cannot safely perform the requested transition."""


class _IntentRecordingBackend:
    """Retain the controller-owned invocation identity after generic commit."""

    def __init__(self, owner: "SupervisedWorkController", backend: TurnBackend) -> None:
        self.owner = owner
        self.backend = backend

    def invocation_for(self, messages, invocation_id, *, protocol):
        return self.backend.invocation_for(messages, invocation_id, protocol=protocol)

    def generate(
        self,
        messages: tuple[dict[str, Any], ...],
        *,
        protocol,
        invocation: InferenceInvocation,
        evidence_sink: ResponseEvidenceSink,
    ) -> str:
        case = self.owner._turns._case(WORK_CASE_ID)
        turn = int(case["pending_turn"]["turn"])
        _atomic_json(
            self.owner.root / "cases" / WORK_CASE_ID / "turns" / f"{turn:04d}" / "inference-intent.json",
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


def _snapshot(value: Mapping[str, Any]) -> RepositorySnapshot:
    data = dict(value)
    data["untracked_inventory"] = tuple(tuple(item) for item in data["untracked_inventory"])
    return RepositorySnapshot(**data)


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise SupervisedWorkError("SOURCE_NOT_A_GIT_REPOSITORY")
    return result.stdout.decode("utf-8", errors="strict").strip()


def _safe_relative(value: str, *, allow_dot: bool) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise SupervisedWorkError("INVALID_AUTHORITY_PATH")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise SupervisedWorkError("SUPERVISION_REQUIRED_CROSS_REPOSITORY")
    normalized = path.as_posix()
    if normalized == "." and not allow_dot:
        raise SupervisedWorkError("REPOSITORY_ROOT_PATCH_AUTHORITY_DENIED")
    if not allow_dot and (not path.parts or path.parts[0] == ".git"):
        raise SupervisedWorkError("INVALID_PATCH_AUTHORITY")
    if path.parts and path.parts[0] == ".git":
        raise SupervisedWorkError("INVALID_AUTHORITY_PATH")
    return normalized


def _qualification_binding(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    required = (
        f"qualification_id: {QUALIFICATION_ID}",
        f"  model: {MODEL_TAG}",
        f"  digest: {MODEL_DIGEST}",
        f"  quantization: {MODEL_QUANTIZATION}",
        "  context: 4096",
        "  runtime_profile: GPU_PRIMARY_PARTIAL_OFFLOAD",
        f"  alpha_version: {ALPHA_VERSION}",
        f"  {OPERATING_CLASS}: QUALIFIED",
        "  AUTONOMOUS_MULTI_REPO: NOT_QUALIFIED",
    )
    if any(item not in text for item in required):
        raise SupervisedWorkError("MODEL_QUALIFICATION_MISMATCH")
    return {
        "qualification_id": QUALIFICATION_ID,
        "manifest": "docs/qualification/qwen3-coder-30b-alpha-v1.yaml",
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "artifact_digest": MODEL_DIGEST,
        "alpha_version": ALPHA_VERSION,
        "operating_class": OPERATING_CLASS,
    }


def _same_material(left: RepositorySnapshot, right: RepositorySnapshot) -> bool:
    return (
        left.head_commit,
        left.branch,
        left.index_identity,
        left.tracked_worktree_identity,
        left.untracked_identity,
        left.submodule_identity,
        left.ignored_file_policy,
    ) == (
        right.head_commit,
        right.branch,
        right.index_identity,
        right.tracked_worktree_identity,
        right.untracked_identity,
        right.submodule_identity,
        right.ignored_file_policy,
    )


class SupervisedWorkController:
    """One-task facade over the restart-safe durable turn controller."""

    def __init__(self, session_root: Path) -> None:
        self.root = session_root
        self._turns = AlphaExperimentController(session_root)

    @classmethod
    def start(
        cls,
        store: Path,
        *,
        session_id: str,
        repository: Path,
        expected_head: str,
        objective: str,
        read_scopes: tuple[str, ...],
        patch_paths: tuple[str, ...],
        qualification_path: Path,
        harness_sha: str,
        turn_limit: int = DEFAULT_TURN_LIMIT,
    ) -> "SupervisedWorkController":
        if not SESSION_ID.fullmatch(session_id):
            raise SupervisedWorkError("INVALID_SESSION_ID")
        if not objective or len(objective.encode("utf-8")) > MAX_OBJECTIVE_BYTES:
            raise SupervisedWorkError("INVALID_OBJECTIVE")
        if not 1 <= turn_limit <= 16:
            raise SupervisedWorkError("INVALID_TURN_LIMIT")
        if not 1 <= len(read_scopes) <= MAX_SCOPES or len(set(read_scopes)) != len(read_scopes):
            raise SupervisedWorkError("INVALID_READ_AUTHORITY")
        if len(patch_paths) > MAX_PATCH_PATHS or len(set(patch_paths)) != len(patch_paths):
            raise SupervisedWorkError("INVALID_PATCH_AUTHORITY")
        bounded_reads = tuple(_safe_relative(item, allow_dot=True) for item in read_scopes)
        bounded_patches = tuple(_safe_relative(item, allow_dot=False) for item in patch_paths)

        observer = ReadOnlyExecutor()
        try:
            observed = observer.observe_repository(repository).snapshot
        except Exception as error:
            raise SupervisedWorkError("SOURCE_NOT_A_GIT_REPOSITORY") from error
        if not re.fullmatch(r"[0-9a-f]{40,64}", expected_head) or observed.head_commit != expected_head:
            raise SupervisedWorkError("EXPECTED_HEAD_MISMATCH")
        if _git(Path(observed.canonical_root), "status", "--porcelain=v1", "--untracked-files=all"):
            raise SupervisedWorkError("SOURCE_MUST_BE_CLEAN")

        qualification = _qualification_binding(qualification_path)
        created_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "experiment_id": session_id,
            "session_id": session_id,
            "created_at": created_at,
            "experiment_harness_sha": harness_sha,
            "session_kind": "SUPERVISED_SINGLE_REPOSITORY_WORK_V1",
            "repository": {
                "canonical_path": observed.canonical_root,
                "repository_identity": observed.repository_identity,
                "expected_head": expected_head,
                "snapshot_identity": observed.snapshot_identity,
            },
            "objective": objective,
            "authority": {"read_scopes": list(bounded_reads), "patch_paths": list(bounded_patches)},
            "turn_limit": turn_limit,
            "protocol_id": SINGLE_REPOSITORY_PROTOCOL_ID,
            "model_artifact": {
                "tag": MODEL_TAG,
                "digest": MODEL_DIGEST,
                "quantization": MODEL_QUANTIZATION,
                "context": 4096,
                "runtime_profile": "GPU_PRIMARY_PARTIAL_OFFLOAD",
                "gpu_percent": 80,
                "cpu_percent": 20,
            },
            "qualification": qualification,
        }
        conversation = [{
            "role": "user",
            "content": {
                "task": objective,
                "repository": {
                    "repository_identity": observed.repository_identity,
                    "head": observed.head_commit,
                    "snapshot_identity": observed.snapshot_identity,
                },
                "authority": {"read_scopes": list(bounded_reads), "patch_paths": list(bounded_patches)},
                "supervision": {
                    "source_repository_is_read_only": True,
                    "first_accepted_patch_becomes_the_candidate": True,
                    "operator_controls_any_future_promotion": True,
                    "additional_repository_authority": False,
                },
            },
        }]
        case = {
            "case_id": WORK_CASE_ID,
            "interaction_id": session_id,
            "protocol_id": SINGLE_REPOSITORY_PROTOCOL_ID,
            "fixture_identity": "operator-repository/snapshot-v1",
            "initial_snapshot_identity": observed.snapshot_identity,
            "snapshot_x": asdict(observed),
            "turn_limit": turn_limit,
            "conversation": conversation,
            "case_state": {
                "candidate": None,
                "clarification": None,
                "validation_status": "VALIDATION_NOT_CONFIGURED",
            },
        }
        controller = AlphaExperimentController.start(store, manifest, (case,))
        _atomic_json(controller.root / "session-manifest.json", manifest)
        _atomic_json(controller.root / "session-state.json", {
            "session_id": session_id,
            "status": "READY",
            "source_state": "MATCH",
            "candidate_effect": False,
            "validation_status": "VALIDATION_NOT_CONFIGURED",
            "operator_disposition": None,
        })
        return cls(controller.root)

    def step(self, backend: TurnBackend) -> dict[str, Any]:
        state = _load(self.root / "session-state.json")
        if state["status"] in {"AWAITING_REVIEW", "AWAITING_CLARIFICATION", "TERMINAL", "TURN_LIMIT", "APPROVED", "REJECTED", "INVALIDATED"}:
            raise SupervisedWorkError("SESSION_MAY_NOT_ADVANCE")
        case = self._turns._case(WORK_CASE_ID)
        if case["case_status"] not in {"READY", "ACTIVE"}:
            raise SupervisedWorkError("SESSION_MAY_NOT_ADVANCE")
        try:
            result = self._turns.step(WORK_CASE_ID, _IntentRecordingBackend(self, backend), self._process_turn)
        except Exception as error:
            current = self._turns._case(WORK_CASE_ID)
            state["last_step_error"] = {"type": type(error).__name__, "message": str(error)}
            if current.get("case_status") == "INVALIDATED":
                state["status"] = "INVALIDATED"
                state["infrastructure_failure"] = current.get("pending_turn")
                _atomic_json(self.root / "session-state.json", state)
            elif current.get("pending_turn", {}).get("phase") == "INFERENCE_INTENT_DURABLE":
                state["status"] = "ACTIVE"
                state["pending_inference"] = current["pending_turn"]
                _atomic_json(self.root / "session-state.json", state)
            else:
                state["status"] = "ACTIVE"
                _atomic_json(self.root / "session-state.json", state)
            raise
        case = self._turns._case(WORK_CASE_ID)
        if case["turn_committed"] >= case["turn_limit"] and case["case_status"] == "ACTIVE":
            case["case_status"] = "TURN_LIMIT"
            case["terminal_disposition"] = "TURN_LIMIT"
            self._turns._write_case(case)
        self._refresh_state()
        if self._turns._case(WORK_CASE_ID)["case_state"].get("candidate"):
            self._write_review_packet()
        return result

    def _process_turn(self, case: dict[str, Any], raw: str) -> Mapping[str, Any]:
        snapshot = _snapshot(case["snapshot_x"])
        observer = ReadOnlyExecutor()
        if observer.compare_snapshot(snapshot).status is not CompareStatus.MATCH:
            raise ExperimentError("authoritative source no longer matches frozen session snapshot")
        task = HarnessTask(
            case["interaction_id"], WORK_CASE_ID, snapshot,
            tuple(self.manifest()["authority"]["read_scopes"]),
            bool(self.manifest()["authority"]["patch_paths"]),
            tuple(self.manifest()["authority"]["patch_paths"]),
            int(case["turn_limit"]),
        )
        harness = DispositionHarness(task, observer, IsolatedPatchExecutor(observer))
        try:
            step = harness.step(raw)
            record = asdict(step.record)
            result: dict[str, Any] = {
                **record,
                "turn": case["turn_committed"] + 1,
                "projection": step.model_projection,
                "evaluator_evidence": {
                    "source_snapshot_preserved": observer.compare_snapshot(snapshot).status.value,
                    "candidate_effect": False,
                },
            }
            if self._cross_repository_shape(raw):
                result["authority_outcome"] = "SUPERVISION_REQUIRED_CROSS_REPOSITORY"
                result["projection"] = {"status": "DENIED", "error": "SUPERVISION_REQUIRED_CROSS_REPOSITORY"}
            if step.record.projection.get("status") == "ACCEPTED":
                if harness._context is None:
                    raise ExperimentError("accepted patch lacks isolated result")
                request = parse_request(raw)
                proposal = PatchProposal.create(
                    snapshot,
                    request.arguments["patch"].encode("utf-8"),
                    tuple(request.arguments["proposed_paths"]),
                )
                candidate = self._freeze_candidate(harness._context.isolated_root, proposal, tuple(step.record.projection["changed_paths"]))
                case["case_state"]["candidate"] = candidate
                result["terminal_disposition"] = "CANDIDATE_READY"
                result["case_status"] = "TERMINAL"
                result["evaluator_evidence"].update({"candidate_effect": True, "candidate_identity": candidate["candidate_snapshot_identity"]})
            elif step.record.request_type == RequestType.REQUEST_CLARIFICATION.value:
                question = str(step.record.parsed_arguments["question"])
                case["case_state"]["clarification"] = {
                    "question": question,
                    "sha256": hashlib.sha256(question.encode()).hexdigest(),
                    "turn": case["turn_committed"] + 1,
                }
            return result
        finally:
            harness.close()

    @staticmethod
    def _cross_repository_shape(raw: str) -> bool:
        try:
            request = parse_request(raw)
        except Exception:
            return False
        values: list[str] = []
        if request.request_type is RequestType.READ:
            values.append(request.arguments["path"])
        elif request.request_type is RequestType.SEARCH:
            values.append(request.arguments["scope"])
        elif request.request_type is RequestType.PROPOSE_PATCH:
            values.extend(request.arguments["proposed_paths"])
        return any(PurePosixPath(item).is_absolute() or ".." in PurePosixPath(item).parts for item in values)

    def _freeze_candidate(self, isolated_root: str, proposal: PatchProposal, changed_paths: tuple[str, ...]) -> dict[str, Any]:
        destination = self.root / "candidate"
        if destination.exists():
            raise ExperimentError("candidate effect already exists")
        temporary = Path(tempfile.mkdtemp(prefix=".candidate-", dir=self.root))
        try:
            repository = temporary / "repository"
            shutil.copytree(isolated_root, repository, symlinks=True)
            candidate_snapshot = ReadOnlyExecutor().observe_repository(repository).snapshot
            isolated_snapshot = ReadOnlyExecutor().observe_repository(isolated_root).snapshot
            if not _same_material(candidate_snapshot, isolated_snapshot):
                raise ExperimentError("candidate reconstruction mismatch")
            _atomic_bytes(temporary / "patch.diff", proposal.patch_content)
            metadata = {
                "proposal_identity": proposal.proposal_identity,
                "patch_sha256": proposal.patch_content_identity,
                "proposed_paths": list(proposal.proposed_paths),
                "changed_paths": list(changed_paths),
                "source_snapshot_identity": proposal.source_snapshot_identity,
                "candidate_snapshot": asdict(candidate_snapshot),
                "candidate_snapshot_identity": candidate_snapshot.snapshot_identity,
                "isolated_result_location": str(destination / "repository"),
                "application": "SUCCESS",
                "technical_correctness": "NOT_CLAIMED",
            }
            os.replace(temporary, destination)
            final_snapshot = ReadOnlyExecutor().observe_repository(destination / "repository").snapshot
            if not _same_material(final_snapshot, isolated_snapshot):
                raise ExperimentError("candidate final identity mismatch")
            metadata["candidate_snapshot"] = asdict(final_snapshot)
            metadata["candidate_snapshot_identity"] = final_snapshot.snapshot_identity
            _atomic_json(destination / "candidate.json", metadata)
            directory = os.open(self.root, os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            return metadata
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    def manifest(self) -> dict[str, Any]:
        return _load(self.root / "session-manifest.json")

    def status(self) -> dict[str, Any]:
        case = self._turns._case(WORK_CASE_ID)
        state = _load(self.root / "session-state.json")
        source_status = ReadOnlyExecutor().compare_snapshot(_snapshot(case["snapshot_x"])).status.value
        candidate = case["case_state"].get("candidate")
        candidate_integrity = "NOT_PRESENT"
        if candidate:
            candidate_integrity = self._candidate_integrity(candidate)
        invocation_ids = []
        runtime_jobs = []
        for turn in range(1, case["turn_committed"] + 1):
            directory = self.root / "cases" / WORK_CASE_ID / "turns" / f"{turn:04d}"
            turn_state = _load(directory / "state.json")
            runtime = turn_state.get("runtime", {})
            if runtime.get("job_id"):
                runtime_jobs.append(runtime["job_id"])
            intent = self._intent_for_turn(case, turn)
            if intent:
                invocation_ids.append(intent)
        pending = case.get("pending_turn")
        if pending and pending.get("invocation_id"):
            invocation_ids.append(pending["invocation_id"])
        return {
            "session": self.root.name,
            "session_status": state["status"],
            "repository": self.manifest()["repository"],
            "source_state": source_status,
            "current_turn": case["turn_committed"],
            "turn_limit": case["turn_limit"],
            "pending_turn": pending,
            "terminal_disposition": case.get("terminal_disposition"),
            "candidate_effect": candidate is not None,
            "candidate_integrity": candidate_integrity,
            "changed_paths": candidate.get("changed_paths", []) if candidate else [],
            "validation_status": case["case_state"]["validation_status"],
            "clarification": case["case_state"].get("clarification"),
            "operator_disposition": state.get("operator_disposition"),
            "last_step_error": state.get("last_step_error"),
            "qualification": self.manifest()["qualification"],
            "protocol_id": case["protocol_id"],
            "invocation_integrity": {
                "invocation_ids": invocation_ids,
                "runtime_jobs": runtime_jobs,
                "duplicate_invocation_ids": len(invocation_ids) != len(set(invocation_ids)),
                "turn_hash_chain": self._hash_chain_status(case),
            },
        }

    def _intent_for_turn(self, case: Mapping[str, Any], turn: int) -> str | None:
        # Invocation intent is retained in the case while pending and is bound
        # into the raw runtime evidence once committed. Older generic journal
        # turns do not duplicate it in committed.json.
        pending = case.get("pending_turn")
        if pending and pending.get("turn") == turn:
            return pending.get("invocation_id")
        intent_path = self.root / "cases" / WORK_CASE_ID / "turns" / f"{turn:04d}" / "inference-intent.json"
        return _load(intent_path).get("invocation_id") if intent_path.exists() else None

    def _candidate_integrity(self, candidate: Mapping[str, Any]) -> str:
        try:
            expected = _snapshot(candidate["candidate_snapshot"])
            return ReadOnlyExecutor().compare_snapshot(expected).status.value
        except Exception:
            return "ERROR"

    def _hash_chain_status(self, case: Mapping[str, Any]) -> str:
        previous = None
        try:
            for turn in range(1, int(case["turn_committed"]) + 1):
                committed = _load(self.root / "cases" / WORK_CASE_ID / "turns" / f"{turn:04d}" / "committed.json")
                if committed["previous_turn_digest"] != previous:
                    return "FAIL"
                previous = committed["turn_digest"]
            return "PASS" if previous == case.get("previous_turn_digest") else "FAIL"
        except (OSError, KeyError, json.JSONDecodeError):
            return "FAIL"

    def _refresh_state(self) -> None:
        case = self._turns._case(WORK_CASE_ID)
        state = _load(self.root / "session-state.json")
        state.pop("pending_inference", None)
        state.pop("last_step_error", None)
        if case["case_status"] == "INVALIDATED":
            state["status"] = "INVALIDATED"
        elif case["case_status"] == "TURN_LIMIT":
            state["status"] = "TURN_LIMIT"
        elif case["case_state"].get("candidate"):
            state["status"] = "AWAITING_REVIEW"
            state["candidate_effect"] = True
        elif case["case_state"].get("clarification"):
            state["status"] = "AWAITING_CLARIFICATION"
        elif case["case_status"] == "TERMINAL":
            state["status"] = "TERMINAL"
        else:
            state["status"] = "ACTIVE"
        _atomic_json(self.root / "session-state.json", state)
        _atomic_json(self.root / "family-state.json", {
            "status": "ACTIVE" if state["status"] in {"READY", "ACTIVE"} else state["status"],
            "case_order": [WORK_CASE_ID],
        })

    def review(self) -> dict[str, Any]:
        packet = self._write_review_packet()
        if packet["source_state"] != "MATCH":
            state = _load(self.root / "session-state.json")
            state["source_state"] = "SOURCE_STATE_STALE"
            _atomic_json(self.root / "session-state.json", state)
        return packet

    def _write_review_packet(self) -> dict[str, Any]:
        case = self._turns._case(WORK_CASE_ID)
        manifest = self.manifest()
        candidate = case["case_state"].get("candidate")
        requests = []
        runtime = []
        anomalies = []
        for turn in range(1, case["turn_committed"] + 1):
            directory = self.root / "cases" / WORK_CASE_ID / "turns" / f"{turn:04d}"
            result = _load(directory / "harness-result.json")
            requests.append({
                "turn": turn,
                "request_type": result.get("request_type"),
                "parsed_arguments": result.get("parsed_arguments"),
                "authority_outcome": result.get("authority_outcome"),
                "executor_operation": result.get("executor_operation"),
                "projection": result.get("projection"),
            })
            if "DENIED" in str(result.get("authority_outcome")) or result.get("authority_outcome") == "FORBIDDEN_RECORDED":
                anomalies.append({"turn": turn, "authority_outcome": result.get("authority_outcome")})
            turn_state = _load(directory / "state.json")
            runtime.append({"turn": turn, **turn_state.get("runtime", {})})
        source_state = ReadOnlyExecutor().compare_snapshot(_snapshot(case["snapshot_x"])).status.value
        patch = (self.root / "candidate" / "patch.diff").read_text(encoding="utf-8") if candidate else None
        packet = {
            "session_id": self.root.name,
            "starting_head": manifest["repository"]["expected_head"],
            "snapshot_identity": manifest["repository"]["snapshot_identity"],
            "source_state": source_state,
            "objective": manifest["objective"],
            "authority": manifest["authority"],
            "request_sequence": requests,
            "candidate_patch": patch,
            "changed_paths": candidate.get("changed_paths", []) if candidate else [],
            "executor_application": candidate.get("application") if candidate else None,
            "technical_correctness": candidate.get("technical_correctness") if candidate else "NOT_EVALUATED",
            "validation_result": case["case_state"]["validation_status"],
            "runtime_evidence": runtime,
            "authority_denials_or_anomalies": anomalies,
            "isolated_result_location": candidate.get("isolated_result_location") if candidate else None,
            "candidate_integrity": self._candidate_integrity(candidate) if candidate else "NOT_PRESENT",
            "clarification": case["case_state"].get("clarification"),
            "operator_disposition": _load(self.root / "session-state.json").get("operator_disposition"),
        }
        _atomic_json(self.root / "review-packet.json", packet)
        return packet

    def disposition(self, decision: str) -> dict[str, Any]:
        if decision not in {"APPROVE", "REJECT"}:
            raise SupervisedWorkError("INVALID_OPERATOR_DISPOSITION")
        state = _load(self.root / "session-state.json")
        if state.get("operator_disposition") is not None:
            raise SupervisedWorkError("OPERATOR_DISPOSITION_ALREADY_RECORDED")
        case = self._turns._case(WORK_CASE_ID)
        if not case["case_state"].get("candidate"):
            raise SupervisedWorkError("NO_CANDIDATE_EFFECT")
        packet = self.review()
        if packet["candidate_integrity"] != "MATCH":
            raise SupervisedWorkError("CANDIDATE_STATE_INVALID")
        if decision == "APPROVE" and packet["source_state"] != "MATCH":
            raise SupervisedWorkError("SOURCE_STATE_STALE")
        evidence = {
            "decision": decision,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "operator_origin": True,
            "promotion_performed": False,
            "source_state": packet["source_state"],
            "candidate_snapshot_identity": case["case_state"]["candidate"]["candidate_snapshot_identity"],
        }
        _atomic_json(self.root / "operator-disposition.json", evidence)
        state["operator_disposition"] = decision
        state["status"] = "APPROVED" if decision == "APPROVE" else "REJECTED"
        _atomic_json(self.root / "session-state.json", state)
        return evidence


def generated_session_id(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    nonce = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
    return f"work-{moment.strftime('%Y%m%dT%H%M%SZ')}-{nonce}"
