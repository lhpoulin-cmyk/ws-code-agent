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
from .contained_validation import SystemdContainedValidationRunner
from .isolated_patch import IsolatedContext, IsolatedPatchExecutor, PatchProposal
from .katra_ollama_backend import (
    DEVSTRAL_MODEL_DIGEST,
    DEVSTRAL_MODEL_QUANTIZATION,
    DEVSTRAL_MODEL_TAG,
    DEVSTRAL_RUNTIME_PROFILE,
    InferenceInvocation,
    MODEL_DIGEST,
    MODEL_QUANTIZATION,
    MODEL_TAG,
    QWEN_RUNTIME_PROFILE,
    QWEN25_MODEL_DIGEST,
    QWEN25_MODEL_QUANTIZATION,
    QWEN25_MODEL_TAG,
    QWEN25_RUNTIME_PROFILE,
    QWEN25_32B_MODEL_DIGEST,
    QWEN25_32B_MODEL_QUANTIZATION,
    QWEN25_32B_MODEL_TAG,
    QWEN25_32B_RUNTIME_PROFILE,
    ResponseEvidenceSink,
)
from .readonly_executor import CompareStatus, ExecutorFact, ReadOnlyExecutor, RepositorySnapshot
from .request_protocol import (
    SINGLE_REPOSITORY_PROTOCOL_ID,
    VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
)
from .response_normalization import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    STRICT_RAW,
    normalize_single_markdown_json_fence,
)
from .supervised_validation import (
    HIDDEN_VALIDATION_ID,
    VISIBLE_VALIDATION_ID,
    WRITE_VALIDATION_IDS,
    bind_validation_ids,
    binding_matches,
    descriptor_binding,
    validation_registry,
)
from .validation import DescriptorValidationExecutor, ValidationRole, ValidationRun, ValidationStatus


WORK_CASE_ID = "WORK"
OPERATING_CLASS = "SUPERVISED_SINGLE_REPO"
QUALIFICATION_ID = "qwen3-coder-30b-alpha-v1"
ALPHA_VERSION = "HELIX_CODE_AGENT_ALPHA_V1"
DEFAULT_TURN_LIMIT = 8
MAX_OBJECTIVE_BYTES = 16_384
MAX_SCOPES = 8
MAX_PATCH_PATHS = 8
SESSION_ID = re.compile(r"work-[A-Za-z0-9][A-Za-z0-9._-]{7,95}")
SYNTHETIC_V2_SESSION_KIND = "SYNTHETIC_SUPERVISED_SINGLE_REPOSITORY_V2_ACCEPTANCE"
DEVSTRAL_V2_SESSION_KIND = "DEVSTRAL_V2_SUPERVISED_PRODUCTION_ADMISSION"
DEVSTRAL_CANDIDATE_ID = "devstral-small-2-q4"
QWEN25_V2_SESSION_KIND = "QWEN25_V2_SUPERVISED_PRODUCTION_ADMISSION"
QWEN25_CANDIDATE_ID = "qwen25-coder-14b-q4"
QWEN25_14B_INTERACTIVE_NORMALIZED_SESSION_KIND = "QWEN25_14B_INTERACTIVE_NORMALIZED_V1"
INTERACTIVE_NORMALIZED = "INTERACTIVE_NORMALIZED"
QWEN25_32B_V2_SESSION_KIND = "QWEN25_32B_V2_SUPERVISED_PRODUCTION_ADMISSION"
QWEN25_32B_CANDIDATE_ID = "qwen25-coder-32b-q4"
SYNTHETIC_V2_WRITE = "write"
SYNTHETIC_V2_CLARIFICATION = "clarification"
SYNTHETIC_V2_FIXTURES = (SYNTHETIC_V2_WRITE, SYNTHETIC_V2_CLARIFICATION)

STRICT_RAW_ADAPTER_BINDING = {
    "mode": STRICT_RAW,
    "adapter_id": "NONE",
    "adapter_version": None,
}
INTERACTIVE_NORMALIZED_ADAPTER_BINDING = {
    "mode": INTERACTIVE_NORMALIZED,
    "adapter_id": ADAPTER_ID,
    "adapter_version": ADAPTER_VERSION,
}

_WRITE_OBJECTIVE = (
    'Create src/message.py containing a simple function named message that takes no arguments and returns the string "hello".\n'
)
_WRITE_README = "# Message utility\n\nThe `src` package contains the small message utility.\n"
_CLARIFICATION_OBJECTIVE = (
    "Implement format_release_label(title) for release labels using the bounded repository interface.\n"
)
_CLARIFICATION_README = (
    "# Release labels\n\n"
    "Release labels need a public representation. The product requirements do not\n"
    "choose whether the representation is an uppercase display label or a stable\n"
    "lowercase slug. That choice belongs to the operator.\n"
)
_CLARIFICATION_SOURCE = (
    "def format_release_label(title: str) -> str:\n"
    '    """Return the product-approved release-label representation."""\n'
    "    raise NotImplementedError\n"
)


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
                **asdict(invocation.execution_identity),
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


def _qwen_model_artifact() -> dict[str, Any]:
    return {
        "tag": MODEL_TAG,
        "digest": MODEL_DIGEST,
        "quantization": MODEL_QUANTIZATION,
        "context": 4096,
        "sampling": "appliance/Ollama defaults",
        "runtime_profile": QWEN_RUNTIME_PROFILE.policy_result,
        "runtime_profile_id": QWEN_RUNTIME_PROFILE.profile_id,
        "minimum_gpu_percent": QWEN_RUNTIME_PROFILE.minimum_gpu_percent,
        "maximum_cpu_percent": QWEN_RUNTIME_PROFILE.maximum_cpu_percent,
    }


def _devstral_candidate_binding(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    required = (
        f"candidate_id: {DEVSTRAL_CANDIDATE_ID}",
        "status: SELECTED_FOR_EVALUATION",
        f"  model: {DEVSTRAL_MODEL_TAG}",
        f"  digest: {DEVSTRAL_MODEL_DIGEST}",
        f"  quantization: {DEVSTRAL_MODEL_QUANTIZATION}",
        "  context: 4096",
        "  temperature: 0.15",
        f"  profile_id: {DEVSTRAL_RUNTIME_PROFILE.profile_id}",
        "  status: RUNTIME_ACCEPTED",
        "  minimum_gpu_percent: 88",
        "  maximum_cpu_percent: 12",
        f"  protocol_id: {VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID}",
        "  production_admission: PENDING",
    )
    if any(item not in text for item in required):
        raise SupervisedWorkError("CHALLENGER_BINDING_MISMATCH")
    qualification = {
        "candidate_id": DEVSTRAL_CANDIDATE_ID,
        "manifest": "docs/qualification/devstral-small-2-v2-admission-candidate.yaml",
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "artifact_digest": DEVSTRAL_MODEL_DIGEST,
        "evaluation_scope": "V2_SYNTHETIC_PRODUCTION_ADMISSION",
        "runtime_status": "RUNTIME_ACCEPTED",
        "production_admission": "PENDING",
    }
    model_artifact = {
        "tag": DEVSTRAL_MODEL_TAG,
        "digest": DEVSTRAL_MODEL_DIGEST,
        "quantization": DEVSTRAL_MODEL_QUANTIZATION,
        "context": 4096,
        "sampling": {"temperature": 0.15, "other": "artifact/Ollama defaults"},
        "runtime_profile": DEVSTRAL_RUNTIME_PROFILE.policy_result,
        "runtime_profile_id": DEVSTRAL_RUNTIME_PROFILE.profile_id,
        "minimum_gpu_percent": DEVSTRAL_RUNTIME_PROFILE.minimum_gpu_percent,
        "maximum_cpu_percent": DEVSTRAL_RUNTIME_PROFILE.maximum_cpu_percent,
    }
    return qualification, model_artifact


def _qwen25_candidate_binding(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    required = (
        f"candidate_id: {QWEN25_CANDIDATE_ID}",
        "status: RUNTIME_ACCEPTED",
        f"  model: {QWEN25_MODEL_TAG}",
        f"  digest: {QWEN25_MODEL_DIGEST}",
        f"  quantization: {QWEN25_MODEL_QUANTIZATION}",
        "  context: 4096",
        "  generation_overrides: NONE",
        f"  profile_id: {QWEN25_RUNTIME_PROFILE.profile_id}",
        "  status: RUNTIME_ACCEPTED",
        "  execution: GPU_ONLY",
        "  minimum_gpu_percent: 100",
        "  maximum_cpu_percent: 0",
        "  ollama_version: 0.32.0+helix.repeatlimit.1",
        "  binary_sha256: b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143",
        "  build_id: ffd1f9f6c8ffd69fdca1316e7c032447479fe139",
        f"  protocol_id: {VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID}",
        "  production_admission: NOT_EVALUATED",
    )
    if any(item not in text for item in required):
        raise SupervisedWorkError("CHALLENGER_BINDING_MISMATCH")
    qualification = {
        "candidate_id": QWEN25_CANDIDATE_ID,
        "manifest": "docs/qualification/qwen25-coder-14b-v2-admission-candidate.yaml",
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "artifact_digest": QWEN25_MODEL_DIGEST,
        "evaluation_scope": "V2_SYNTHETIC_PRODUCTION_ADMISSION",
        "runtime_status": "RUNTIME_ACCEPTED",
        "production_admission": "NOT_EVALUATED",
    }
    model_artifact = {
        "tag": QWEN25_MODEL_TAG,
        "digest": QWEN25_MODEL_DIGEST,
        "quantization": QWEN25_MODEL_QUANTIZATION,
        "context": 4096,
        "sampling": "artifact/Ollama defaults; no generation overrides",
        "runtime_profile": QWEN25_RUNTIME_PROFILE.policy_result,
        "runtime_profile_id": QWEN25_RUNTIME_PROFILE.profile_id,
        "minimum_gpu_percent": QWEN25_RUNTIME_PROFILE.minimum_gpu_percent,
        "maximum_cpu_percent": QWEN25_RUNTIME_PROFILE.maximum_cpu_percent,
    }
    return qualification, model_artifact


def _qwen25_32b_candidate_binding(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    model_blob = "ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9"
    required = (
        f"candidate_id: {QWEN25_32B_CANDIDATE_ID}",
        "status: RUNTIME_ACCEPTED",
        f"  model: {QWEN25_32B_MODEL_TAG}",
        f"  digest: {QWEN25_32B_MODEL_DIGEST}",
        f"  model_blob: {model_blob}",
        f"  quantization: {QWEN25_32B_MODEL_QUANTIZATION}",
        "  context: 4096",
        "  generation_overrides: NONE",
        f"  profile_id: {QWEN25_32B_RUNTIME_PROFILE.profile_id}",
        "  status: RUNTIME_ACCEPTED",
        "  execution: GPU_PRIMARY_PARTIAL_OFFLOAD",
        "  minimum_gpu_percent: 71",
        "  maximum_cpu_percent: 29",
        "  ollama_version: 0.32.0+helix.repeatlimit.1",
        "  binary_sha256: b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143",
        "  build_id: ffd1f9f6c8ffd69fdca1316e7c032447479fe139",
        "  runtime_deviation: OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1",
        f"  protocol_id: {VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID}",
        "  production_admission: NOT_EVALUATED",
    )
    if any(item not in text for item in required):
        raise SupervisedWorkError("CHALLENGER_BINDING_MISMATCH")
    qualification = {
        "candidate_id": QWEN25_32B_CANDIDATE_ID,
        "manifest": "docs/qualification/qwen25-coder-32b-v2-admission-candidate.yaml",
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "artifact_digest": QWEN25_32B_MODEL_DIGEST,
        "model_blob": model_blob,
        "evaluation_scope": "V2_SYNTHETIC_PRODUCTION_ADMISSION",
        "runtime_status": "RUNTIME_ACCEPTED",
        "production_admission": "NOT_EVALUATED",
        "ollama_version": "0.32.0+helix.repeatlimit.1",
        "ollama_binary_sha256": "b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143",
        "ollama_build_id": "ffd1f9f6c8ffd69fdca1316e7c032447479fe139",
        "runtime_deviation": "OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1",
    }
    model_artifact = {
        "tag": QWEN25_32B_MODEL_TAG,
        "digest": QWEN25_32B_MODEL_DIGEST,
        "model_blob": model_blob,
        "quantization": QWEN25_32B_MODEL_QUANTIZATION,
        "context": 4096,
        "sampling": "artifact/Ollama defaults; no generation overrides",
        "runtime_profile": QWEN25_32B_RUNTIME_PROFILE.policy_result,
        "runtime_profile_id": QWEN25_32B_RUNTIME_PROFILE.profile_id,
        "minimum_gpu_percent": QWEN25_32B_RUNTIME_PROFILE.minimum_gpu_percent,
        "maximum_cpu_percent": QWEN25_32B_RUNTIME_PROFILE.maximum_cpu_percent,
    }
    return qualification, model_artifact


def _candidate_protocol_qualification(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    status_match = re.search(r"^  qualification_status: ([A-Z_]+)$", text, re.MULTILINE)
    production_match = re.search(r"^  production_qualified: (true|false)$", text, re.MULTILINE)
    acceptance_match = re.search(r"^  synthetic_acceptance: ([A-Z_]+)$", text, re.MULTILINE)
    required = (
        f"  alpha_evaluation_protocol: {SINGLE_REPOSITORY_PROTOCOL_ID}",
        f"  protocol_id: {VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID}",
        "  operating_class: SUPERVISED_SINGLE_REPO",
    )
    if (
        any(item not in text for item in required)
        or status_match is None
        or production_match is None
        or acceptance_match is None
    ):
        raise SupervisedWorkError("PROTOCOL_QUALIFICATION_MISMATCH")
    return {
        "id": VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
        "qualification_status": status_match.group(1),
        "production_qualified": production_match.group(1) == "true",
        "synthetic_acceptance": acceptance_match.group(1),
        "operating_class": OPERATING_CLASS,
        "alpha_evaluation_protocol": SINGLE_REPOSITORY_PROTOCOL_ID,
    }


def _production_protocol_qualification(path: Path) -> dict[str, Any]:
    candidate = _candidate_protocol_qualification(path)
    if (
        candidate["qualification_status"] == "SUPERVISED_SYNTHETIC_ACCEPTED"
        and candidate["synthetic_acceptance"] == "PASS"
        and candidate["production_qualified"]
    ):
        return candidate
    if not (
        candidate["qualification_status"] == "CANDIDATE"
        and candidate["synthetic_acceptance"] == "PENDING"
        and not candidate["production_qualified"]
    ):
        raise SupervisedWorkError("PROTOCOL_QUALIFICATION_MISMATCH")
    return {
        "id": SINGLE_REPOSITORY_PROTOCOL_ID,
        "qualification_status": "QUALIFIED",
        "production_qualified": True,
        "synthetic_acceptance": "HISTORICAL_ALPHA_V1",
        "operating_class": OPERATING_CLASS,
        "alpha_evaluation_protocol": SINGLE_REPOSITORY_PROTOCOL_ID,
    }


def _initialize_synthetic_v2_fixture(
    store: Path,
    session_id: str,
    fixture_kind: str,
) -> tuple[Path, str, tuple[str, ...], tuple[str, ...], str]:
    if fixture_kind not in SYNTHETIC_V2_FIXTURES:
        raise SupervisedWorkError("UNKNOWN_SYNTHETIC_V2_FIXTURE")
    repository = store / "_synthetic-v2-fixtures" / session_id / "repository"
    if repository.exists():
        raise SupervisedWorkError("SYNTHETIC_V2_FIXTURE_EXISTS")
    repository.mkdir(mode=0o700, parents=True)
    (repository / "src").mkdir(mode=0o700)
    if fixture_kind == SYNTHETIC_V2_WRITE:
        objective = _WRITE_OBJECTIVE
        (repository / "README.md").write_text(_WRITE_README, encoding="utf-8")
        patch_paths = ("src/message.py",)
    else:
        objective = _CLARIFICATION_OBJECTIVE
        (repository / "README.md").write_text(_CLARIFICATION_README, encoding="utf-8")
        (repository / "src" / "release_label.py").write_text(
            _CLARIFICATION_SOURCE,
            encoding="utf-8",
        )
        patch_paths = ()
    result = subprocess.run(
        ["git", "-C", str(repository), "init", "-q"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise SupervisedWorkError("SYNTHETIC_V2_FIXTURE_GIT_FAILURE")
    add_paths = ["README.md"]
    if fixture_kind == SYNTHETIC_V2_CLARIFICATION:
        add_paths.append("src/release_label.py")
    result = subprocess.run(
        ["git", "-C", str(repository), "add", *add_paths],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise SupervisedWorkError("SYNTHETIC_V2_FIXTURE_GIT_FAILURE")
    environment = dict(os.environ)
    environment.update({
        "GIT_AUTHOR_NAME": "Task10K V2",
        "GIT_AUTHOR_EMAIL": "task10k-v2@example.invalid",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
        "GIT_COMMITTER_NAME": "Task10K V2",
        "GIT_COMMITTER_EMAIL": "task10k-v2@example.invalid",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
    })
    result = subprocess.run(
        ["git", "-C", str(repository), "commit", "-qm", f"synthetic V2 {fixture_kind} fixture"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        check=False,
    )
    if result.returncode:
        raise SupervisedWorkError("SYNTHETIC_V2_FIXTURE_GIT_FAILURE")
    return repository, objective, (".",), patch_paths, f"task10k-c-{fixture_kind}/synthetic-v1"


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


def _validation_evidence(run: ValidationRun, binding: Mapping[str, Any]) -> dict[str, Any]:
    evidence = {
        "descriptor_id": run.descriptor_id,
        "descriptor_version": binding["version"],
        "descriptor_identity": binding["descriptor_identity"],
        "role": run.role.value,
        "status": run.status.value,
        "exit_code": run.exit_code,
        "timed_out": run.timed_out,
        "result_before": run.result_before.snapshot_identity,
        "result_after": run.result_after.snapshot_identity,
        "stdout_sha256": hashlib.sha256(run.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(run.stderr.encode()).hexdigest(),
        "containment": dict(run.containment_evidence or {}),
    }
    evidence["evidence_identity"] = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return evidence


class SupervisedWorkController:
    """One-task facade over the restart-safe durable turn controller."""

    def __init__(
        self,
        session_root: Path,
        contained_runner: SystemdContainedValidationRunner | None = None,
    ) -> None:
        self.root = session_root
        self._turns = AlphaExperimentController(session_root)
        self._contained_runner = contained_runner or SystemdContainedValidationRunner()

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
        qualification = _qualification_binding(qualification_path)
        protocol_qualification = _production_protocol_qualification(qualification_path)
        protocol_id = str(protocol_qualification["id"])
        return cls._start_bound(
            store,
            session_id=session_id,
            repository=repository,
            expected_head=expected_head,
            objective=objective,
            read_scopes=read_scopes,
            patch_paths=patch_paths,
            harness_sha=harness_sha,
            turn_limit=turn_limit,
            protocol_id=protocol_id,
            protocol_qualification=protocol_qualification,
            qualification=qualification,
            model_artifact=_qwen_model_artifact(),
            session_kind="SUPERVISED_SINGLE_REPOSITORY_WORK_V1",
            fixture_identity="operator-repository/snapshot-v1",
            validation_ids=(),
        )

    @classmethod
    def start_synthetic_v2(
        cls,
        store: Path,
        *,
        session_id: str,
        fixture_kind: str,
        qualification_path: Path,
        harness_sha: str,
        turn_limit: int = DEFAULT_TURN_LIMIT,
    ) -> "SupervisedWorkController":
        if not SESSION_ID.fullmatch(session_id):
            raise SupervisedWorkError("INVALID_SESSION_ID")
        qualification = _qualification_binding(qualification_path)
        protocol_qualification = _candidate_protocol_qualification(qualification_path)
        if (
            protocol_qualification["qualification_status"] != "CANDIDATE"
            or protocol_qualification["synthetic_acceptance"] != "PENDING"
            or protocol_qualification["production_qualified"]
        ):
            raise SupervisedWorkError("V2_CANDIDATE_SESSION_NOT_AUTHORIZED")
        qualification["protocol"] = protocol_qualification
        repository, objective, read_scopes, patch_paths, fixture_identity = (
            _initialize_synthetic_v2_fixture(store, session_id, fixture_kind)
        )
        expected_head = _git(repository, "rev-parse", "HEAD")
        return cls._start_bound(
            store,
            session_id=session_id,
            repository=repository,
            expected_head=expected_head,
            objective=objective,
            read_scopes=read_scopes,
            patch_paths=patch_paths,
            harness_sha=harness_sha,
            turn_limit=turn_limit,
            protocol_id=VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
            protocol_qualification=protocol_qualification,
            qualification=qualification,
            model_artifact=_qwen_model_artifact(),
            session_kind=SYNTHETIC_V2_SESSION_KIND,
            fixture_identity=fixture_identity,
            validation_ids=WRITE_VALIDATION_IDS if fixture_kind == SYNTHETIC_V2_WRITE else (),
        )

    @classmethod
    def start_devstral_v2_admission(
        cls,
        store: Path,
        *,
        session_id: str,
        fixture_kind: str,
        candidate_path: Path,
        harness_sha: str,
        turn_limit: int = DEFAULT_TURN_LIMIT,
    ) -> "SupervisedWorkController":
        if not SESSION_ID.fullmatch(session_id):
            raise SupervisedWorkError("INVALID_SESSION_ID")
        qualification, model_artifact = _devstral_candidate_binding(candidate_path)
        protocol_qualification = _candidate_protocol_qualification(candidate_path)
        if (
            protocol_qualification["qualification_status"] != "CANDIDATE"
            or protocol_qualification["synthetic_acceptance"] != "PENDING"
            or protocol_qualification["production_qualified"]
        ):
            raise SupervisedWorkError("V2_CANDIDATE_SESSION_NOT_AUTHORIZED")
        qualification["protocol"] = protocol_qualification
        repository, objective, read_scopes, patch_paths, fixture_identity = (
            _initialize_synthetic_v2_fixture(store, session_id, fixture_kind)
        )
        expected_head = _git(repository, "rev-parse", "HEAD")
        return cls._start_bound(
            store,
            session_id=session_id,
            repository=repository,
            expected_head=expected_head,
            objective=objective,
            read_scopes=read_scopes,
            patch_paths=patch_paths,
            harness_sha=harness_sha,
            turn_limit=turn_limit,
            protocol_id=VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
            protocol_qualification=protocol_qualification,
            qualification=qualification,
            model_artifact=model_artifact,
            session_kind=DEVSTRAL_V2_SESSION_KIND,
            fixture_identity=fixture_identity,
            validation_ids=WRITE_VALIDATION_IDS if fixture_kind == SYNTHETIC_V2_WRITE else (),
        )

    @classmethod
    def start_qwen25_v2_admission(
        cls,
        store: Path,
        *,
        session_id: str,
        fixture_kind: str,
        candidate_path: Path,
        harness_sha: str,
        turn_limit: int = DEFAULT_TURN_LIMIT,
    ) -> "SupervisedWorkController":
        if not SESSION_ID.fullmatch(session_id):
            raise SupervisedWorkError("INVALID_SESSION_ID")
        qualification, model_artifact = _qwen25_candidate_binding(candidate_path)
        protocol_qualification = _candidate_protocol_qualification(candidate_path)
        if (
            protocol_qualification["qualification_status"] != "CANDIDATE"
            or protocol_qualification["synthetic_acceptance"] != "PENDING"
            or protocol_qualification["production_qualified"]
        ):
            raise SupervisedWorkError("V2_CANDIDATE_SESSION_NOT_AUTHORIZED")
        qualification["protocol"] = protocol_qualification
        repository, objective, read_scopes, patch_paths, fixture_identity = (
            _initialize_synthetic_v2_fixture(store, session_id, fixture_kind)
        )
        expected_head = _git(repository, "rev-parse", "HEAD")
        return cls._start_bound(
            store,
            session_id=session_id,
            repository=repository,
            expected_head=expected_head,
            objective=objective,
            read_scopes=read_scopes,
            patch_paths=patch_paths,
            harness_sha=harness_sha,
            turn_limit=turn_limit,
            protocol_id=VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
            protocol_qualification=protocol_qualification,
            qualification=qualification,
            model_artifact=model_artifact,
            session_kind=QWEN25_V2_SESSION_KIND,
            fixture_identity=fixture_identity,
            validation_ids=WRITE_VALIDATION_IDS if fixture_kind == SYNTHETIC_V2_WRITE else (),
        )

    @classmethod
    def start_qwen25_interactive_normalized(
        cls,
        store: Path,
        *,
        session_id: str,
        fixture_kind: str,
        candidate_path: Path,
        harness_sha: str,
        turn_limit: int = DEFAULT_TURN_LIMIT,
    ) -> "SupervisedWorkController":
        """Start the exact 14B lane with downstream wrapper normalization."""

        if not SESSION_ID.fullmatch(session_id):
            raise SupervisedWorkError("INVALID_SESSION_ID")
        qualification, model_artifact = _qwen25_candidate_binding(candidate_path)
        protocol_qualification = _candidate_protocol_qualification(candidate_path)
        if (
            protocol_qualification["qualification_status"] != "CANDIDATE"
            or protocol_qualification["synthetic_acceptance"] != "PENDING"
            or protocol_qualification["production_qualified"]
        ):
            raise SupervisedWorkError("V2_CANDIDATE_SESSION_NOT_AUTHORIZED")
        qualification["protocol"] = protocol_qualification
        repository, objective, read_scopes, patch_paths, fixture_identity = (
            _initialize_synthetic_v2_fixture(store, session_id, fixture_kind)
        )
        expected_head = _git(repository, "rev-parse", "HEAD")
        return cls._start_bound(
            store,
            session_id=session_id,
            repository=repository,
            expected_head=expected_head,
            objective=objective,
            read_scopes=read_scopes,
            patch_paths=patch_paths,
            harness_sha=harness_sha,
            turn_limit=turn_limit,
            protocol_id=VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
            protocol_qualification=protocol_qualification,
            qualification=qualification,
            model_artifact=model_artifact,
            session_kind=QWEN25_14B_INTERACTIVE_NORMALIZED_SESSION_KIND,
            fixture_identity=fixture_identity,
            validation_ids=WRITE_VALIDATION_IDS if fixture_kind == SYNTHETIC_V2_WRITE else (),
            response_adapter=INTERACTIVE_NORMALIZED_ADAPTER_BINDING,
        )

    @classmethod
    def start_qwen25_32b_v2_admission(
        cls,
        store: Path,
        *,
        session_id: str,
        fixture_kind: str,
        candidate_path: Path,
        harness_sha: str,
        turn_limit: int = DEFAULT_TURN_LIMIT,
    ) -> "SupervisedWorkController":
        if not SESSION_ID.fullmatch(session_id):
            raise SupervisedWorkError("INVALID_SESSION_ID")
        qualification, model_artifact = _qwen25_32b_candidate_binding(candidate_path)
        protocol_qualification = _candidate_protocol_qualification(candidate_path)
        if (
            protocol_qualification["qualification_status"] != "CANDIDATE"
            or protocol_qualification["synthetic_acceptance"] != "PENDING"
            or protocol_qualification["production_qualified"]
        ):
            raise SupervisedWorkError("V2_CANDIDATE_SESSION_NOT_AUTHORIZED")
        qualification["protocol"] = protocol_qualification
        repository, objective, read_scopes, patch_paths, fixture_identity = (
            _initialize_synthetic_v2_fixture(store, session_id, fixture_kind)
        )
        expected_head = _git(repository, "rev-parse", "HEAD")
        return cls._start_bound(
            store,
            session_id=session_id,
            repository=repository,
            expected_head=expected_head,
            objective=objective,
            read_scopes=read_scopes,
            patch_paths=patch_paths,
            harness_sha=harness_sha,
            turn_limit=turn_limit,
            protocol_id=VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
            protocol_qualification=protocol_qualification,
            qualification=qualification,
            model_artifact=model_artifact,
            session_kind=QWEN25_32B_V2_SESSION_KIND,
            fixture_identity=fixture_identity,
            validation_ids=WRITE_VALIDATION_IDS if fixture_kind == SYNTHETIC_V2_WRITE else (),
        )

    @classmethod
    def _start_bound(
        cls,
        store: Path,
        *,
        session_id: str,
        repository: Path,
        expected_head: str,
        objective: str,
        read_scopes: tuple[str, ...],
        patch_paths: tuple[str, ...],
        harness_sha: str,
        turn_limit: int,
        protocol_id: str,
        protocol_qualification: Mapping[str, Any],
        qualification: Mapping[str, Any],
        model_artifact: Mapping[str, Any],
        session_kind: str,
        fixture_identity: str,
        validation_ids: tuple[str, ...],
        response_adapter: Mapping[str, Any] | None = None,
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

        try:
            validation_contract = bind_validation_ids(validation_ids)
        except ValueError as error:
            raise SupervisedWorkError("VALIDATION_DESCRIPTOR_BINDING_INVALID") from error
        validation_status = "VALIDATION_PENDING" if validation_ids else "VALIDATION_NOT_CONFIGURED"
        adapter_binding = dict(response_adapter or STRICT_RAW_ADAPTER_BINDING)
        if adapter_binding not in (
            STRICT_RAW_ADAPTER_BINDING,
            INTERACTIVE_NORMALIZED_ADAPTER_BINDING,
        ):
            raise SupervisedWorkError("RESPONSE_ADAPTER_BINDING_INVALID")
        created_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "experiment_id": session_id,
            "session_id": session_id,
            "created_at": created_at,
            "experiment_harness_sha": harness_sha,
            "session_kind": session_kind,
            "repository": {
                "canonical_path": observed.canonical_root,
                "repository_identity": observed.repository_identity,
                "expected_head": expected_head,
                "snapshot_identity": observed.snapshot_identity,
            },
            "objective": objective,
            "authority": {"read_scopes": list(bounded_reads), "patch_paths": list(bounded_patches)},
            "turn_limit": turn_limit,
            "protocol_id": protocol_id,
            "protocol_qualification": dict(protocol_qualification),
            "model_artifact": dict(model_artifact),
            "qualification": dict(qualification),
            "validation": validation_contract,
            "response_adapter": adapter_binding,
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
            "protocol_id": protocol_id,
            "fixture_identity": fixture_identity,
            "response_adapter": adapter_binding,
            "initial_snapshot_identity": observed.snapshot_identity,
            "snapshot_x": asdict(observed),
            "turn_limit": turn_limit,
            "conversation": conversation,
            "case_state": {
                "candidate": None,
                "clarification": None,
                "validation_status": validation_status,
            },
        }
        controller = AlphaExperimentController.start(store, manifest, (case,))
        _atomic_json(controller.root / "session-manifest.json", manifest)
        _atomic_json(controller.root / "session-state.json", {
            "session_id": session_id,
            "status": "READY",
            "source_state": "MATCH",
            "candidate_effect": False,
            "validation_status": validation_status,
            "operator_disposition": None,
            "response_adapter": adapter_binding,
        })
        if validation_ids:
            _atomic_json(controller.root / "validation-state.json", {
                "contract_origin": "SESSION_MANIFEST",
                "candidate_snapshot_identity": None,
                "phase": "NOT_STARTED",
                "status": "VALIDATION_PENDING",
                "visible_validation": None,
                "hidden_validation": None,
                "technical_correctness": "NOT_EVALUATED",
            })
        return cls(controller.root)

    def step(self, backend: TurnBackend) -> dict[str, Any]:
        state = _load(self.root / "session-state.json")
        self._response_adapter_binding()
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
            adapter = self._response_adapter_binding()
            parser_input = raw
            normalization_evidence: dict[str, Any] | None = None
            if adapter["mode"] == INTERACTIVE_NORMALIZED:
                normalized = normalize_single_markdown_json_fence(raw.encode("utf-8"))
                parser_input = normalized.normalized_parser_input.decode("utf-8", errors="strict")
                normalization_evidence = normalized.evidence()
                turn = case["turn_committed"] + 1
                directory = self.root / "cases" / WORK_CASE_ID / "turns" / f"{turn:04d}"
                _atomic_bytes(directory / "normalized-parser-input.txt", normalized.normalized_parser_input)
                _atomic_json(directory / "normalization-evidence.json", normalization_evidence)
            step = harness.step(parser_input)
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
            if normalization_evidence is not None:
                result["parser_input_sha256"] = record["raw_sha256"]
                result["raw_sha256"] = normalization_evidence["raw_sha256"]
                result["normalization"] = normalization_evidence
            if self._cross_repository_shape(parser_input):
                result["authority_outcome"] = "SUPERVISION_REQUIRED_CROSS_REPOSITORY"
                result["projection"] = {"status": "DENIED", "error": "SUPERVISION_REQUIRED_CROSS_REPOSITORY"}
            if step.record.projection.get("status") == "ACCEPTED":
                if harness._context is None:
                    raise ExperimentError("accepted patch lacks isolated result")
                request = parse_request(parser_input)
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

    def _response_adapter_binding(self) -> dict[str, Any]:
        """Require the immutable lane binding to agree across durable state."""

        manifest = self.manifest()
        state = _load(self.root / "session-state.json")
        case = self._turns._case(WORK_CASE_ID)
        legacy = dict(STRICT_RAW_ADAPTER_BINDING)
        manifest_binding = manifest.get("response_adapter", legacy)
        state_binding = state.get("response_adapter", legacy)
        case_binding = case.get("response_adapter", legacy)
        if not (
            manifest_binding == state_binding == case_binding
            and manifest_binding in (
                STRICT_RAW_ADAPTER_BINDING,
                INTERACTIVE_NORMALIZED_ADAPTER_BINDING,
            )
        ):
            raise SupervisedWorkError("RESPONSE_ADAPTER_BINDING_MISMATCH")
        return dict(manifest_binding)

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

    def bind_retrospective_validation(self, expected_candidate_identity: str) -> dict[str, Any]:
        """Bind current trusted validators to a preserved pre-validator candidate."""
        if (self.root / "retrospective-validation-contract.json").exists() or (self.root / "validation-state.json").exists():
            raise SupervisedWorkError("VALIDATION_ALREADY_BOUND")
        manifest = self.manifest()
        case = self._turns._case(WORK_CASE_ID)
        candidate = case["case_state"].get("candidate")
        if (
            case.get("fixture_identity") != "task10k-c-write/synthetic-v1"
            or manifest.get("objective") != _WRITE_OBJECTIVE
            or manifest.get("authority", {}).get("patch_paths") != ["src/message.py"]
            or candidate is None
        ):
            raise SupervisedWorkError("RETROSPECTIVE_VALIDATION_NOT_APPLICABLE")
        if candidate.get("candidate_snapshot_identity") != expected_candidate_identity:
            raise SupervisedWorkError("CANDIDATE_STATE_INVALID")
        if self._candidate_integrity(candidate) != "MATCH":
            raise SupervisedWorkError("CANDIDATE_STATE_INVALID")
        if ReadOnlyExecutor().compare_snapshot(_snapshot(case["snapshot_x"])).status is not CompareStatus.MATCH:
            raise SupervisedWorkError("SOURCE_STATE_STALE")
        contract = bind_validation_ids(WRITE_VALIDATION_IDS)
        application_root = Path(__file__).resolve().parents[2]
        implementation_sha = _git(application_root, "rev-parse", "HEAD")
        supplement = {
            "record_type": "RETROSPECTIVE_TECHNICAL_VALIDATION_BINDING",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "session_id": self.root.name,
            "historical_session_manifest_sha256": hashlib.sha256(
                (self.root / "session-manifest.json").read_bytes()
            ).hexdigest(),
            "candidate_snapshot_identity": expected_candidate_identity,
            "source_snapshot_identity": case["snapshot_x"]["snapshot_identity"],
            "validator_implementation_sha": implementation_sha,
            "validation": contract,
        }
        _atomic_json(self.root / "retrospective-validation-contract.json", supplement)
        state = {
            "contract_origin": "RETROSPECTIVE_TECHNICAL_VALIDATION",
            "candidate_snapshot_identity": expected_candidate_identity,
            "phase": "NOT_STARTED",
            "status": "VALIDATION_PENDING",
            "visible_validation": None,
            "hidden_validation": None,
            "technical_correctness": "NOT_EVALUATED",
        }
        _atomic_json(self.root / "validation-state.json", state)
        self._set_session_validation_status(state["status"])
        self._write_review_packet()
        return supplement

    def advance_validation(self) -> dict[str, Any]:
        """Advance exactly one restart-safe evaluator-owned validation phase."""
        contract = self._validation_contract()
        state_path = self.root / "validation-state.json"
        if not state_path.is_file():
            raise SupervisedWorkError("VALIDATION_NOT_CONFIGURED")
        state = _load(state_path)
        case = self._turns._case(WORK_CASE_ID)
        candidate = case["case_state"].get("candidate")
        if candidate is None:
            raise SupervisedWorkError("NO_CANDIDATE_EFFECT")
        if self._candidate_integrity(candidate) != "MATCH":
            raise SupervisedWorkError("CANDIDATE_STATE_INVALID")
        if ReadOnlyExecutor().compare_snapshot(_snapshot(case["snapshot_x"])).status is not CompareStatus.MATCH:
            raise SupervisedWorkError("SOURCE_STATE_STALE")
        candidate_identity = candidate["candidate_snapshot_identity"]
        if state.get("candidate_snapshot_identity") not in {None, candidate_identity}:
            raise SupervisedWorkError("CANDIDATE_STATE_INVALID")
        state["candidate_snapshot_identity"] = candidate_identity
        phase = state.get("phase")
        if phase in {"VISIBLE_VALIDATION_STARTED", "HIDDEN_VALIDATION_STARTED"}:
            state["phase"] = "BLOCKED"
            state["status"] = "EXECUTOR_ERROR"
            _atomic_json(state_path, state)
            self._set_session_validation_status(state["status"])
            raise SupervisedWorkError("VALIDATION_OUTCOME_AMBIGUOUS")
        if phase == "NOT_STARTED":
            descriptor_id = VISIBLE_VALIDATION_ID
            result_key = "visible_validation"
            state["phase"] = "VISIBLE_VALIDATION_STARTED"
        elif phase == "VISIBLE_COMPLETE":
            descriptor_id = HIDDEN_VALIDATION_ID
            result_key = "hidden_validation"
            state["phase"] = "HIDDEN_VALIDATION_STARTED"
        else:
            raise SupervisedWorkError("VALIDATION_MAY_NOT_ADVANCE")
        _atomic_json(state_path, state)

        bindings = {
            item["descriptor_id"]: item for item in contract["descriptors"]
        }
        binding = bindings[descriptor_id]
        registry = validation_registry()
        workspace: Path | None = None
        try:
            context, result_snapshot, workspace = self._validation_context(candidate, case)
            run = DescriptorValidationExecutor(
                registry,
                ReadOnlyExecutor(),
                self._contained_runner,
            ).run_validation(
                context,
                result_snapshot,
                descriptor_id,
                tuple(contract["authorized_validation_ids"]),
            )
        finally:
            if workspace is not None and workspace.exists():
                shutil.rmtree(workspace)

        if self._candidate_integrity(candidate) != "MATCH":
            raise SupervisedWorkError("CANDIDATE_STATE_INVALID")
        if ReadOnlyExecutor().compare_snapshot(_snapshot(case["snapshot_x"])).status is not CompareStatus.MATCH:
            raise SupervisedWorkError("SOURCE_STATE_STALE")
        evidence = _validation_evidence(run, binding)
        evidence_dir = self.root / "evaluator" / "validation"
        evidence_name = "visible.json" if run.role is ValidationRole.VISIBLE else "hidden.json"
        _atomic_json(evidence_dir / evidence_name, evidence)
        state[result_key] = evidence

        if run.status is ValidationStatus.VALIDATION_PASS and result_key == "visible_validation":
            state["phase"] = "VISIBLE_COMPLETE"
            state["status"] = "VISIBLE_VALIDATION_PASS"
        elif run.status is ValidationStatus.VALIDATION_PASS:
            state["phase"] = "COMPLETE"
            state["status"] = "VALIDATION_PASS"
            state["technical_correctness"] = "VALIDATED"
        else:
            state["phase"] = "TERMINAL" if run.status is ValidationStatus.VALIDATION_FAIL else "BLOCKED"
            if run.status is ValidationStatus.VALIDATION_FAIL:
                state["status"] = (
                    "VISIBLE_VALIDATION_FAIL"
                    if result_key == "visible_validation"
                    else "HIDDEN_VALIDATION_FAIL"
                )
                state["technical_correctness"] = "FAILED"
            else:
                state["status"] = run.status.value
        _atomic_json(state_path, state)
        self._set_session_validation_status(state["status"])
        self._write_review_packet()
        return evidence

    def _validation_contract(self) -> dict[str, Any]:
        manifest_contract = self.manifest().get("validation")
        if manifest_contract and manifest_contract.get("authorized_validation_ids"):
            contract = manifest_contract
        else:
            supplement_path = self.root / "retrospective-validation-contract.json"
            if not supplement_path.is_file():
                raise SupervisedWorkError("VALIDATION_NOT_CONFIGURED")
            contract = _load(supplement_path)["validation"]
        if not binding_matches(contract):
            raise SupervisedWorkError("VALIDATION_DESCRIPTOR_BINDING_MISMATCH")
        return contract

    def _validation_context(
        self,
        candidate: Mapping[str, Any],
        case: Mapping[str, Any],
    ) -> tuple[IsolatedContext, RepositorySnapshot, Path]:
        workspace = Path(tempfile.mkdtemp(prefix="ws-code-agent-isolated-validation-"))
        repository = workspace / "repository"
        try:
            shutil.copytree(self.root / "candidate" / "repository", repository, symlinks=True)
            result_snapshot = ReadOnlyExecutor().observe_repository(repository).snapshot
            expected = _snapshot(candidate["candidate_snapshot"])
            if not _same_material(expected, result_snapshot):
                raise SupervisedWorkError("CANDIDATE_STATE_INVALID")
            source = _snapshot(case["snapshot_x"])
            context = IsolatedContext(
                source_snapshot=source,
                workspace_root=str(workspace),
                isolated_root=str(repository),
                initial_snapshot=source,
                initial_manifest={},
                build_fact=ExecutorFact(
                    operation="RECONSTRUCT_CANDIDATE_FOR_VALIDATION",
                    success=True,
                    snapshot_identity=source.snapshot_identity,
                    observed_result={
                        "candidate_snapshot_identity": candidate["candidate_snapshot_identity"],
                        "validation_copy_snapshot_identity": result_snapshot.snapshot_identity,
                    },
                ),
            )
            return context, result_snapshot, workspace
        except Exception:
            shutil.rmtree(workspace)
            raise

    def _validation_summary(self) -> dict[str, Any]:
        path = self.root / "validation-state.json"
        if path.is_file():
            return _load(path)
        return {
            "status": "VALIDATION_NOT_CONFIGURED",
            "visible_validation": None,
            "hidden_validation": None,
            "technical_correctness": "NOT_EVALUATED",
        }

    def _set_session_validation_status(self, status: str) -> None:
        state = _load(self.root / "session-state.json")
        state["validation_status"] = status
        _atomic_json(self.root / "session-state.json", state)

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
            "validation_status": self._validation_summary()["status"],
            "clarification": case["case_state"].get("clarification"),
            "operator_disposition": state.get("operator_disposition"),
            "last_step_error": state.get("last_step_error"),
            "qualification": self.manifest()["qualification"],
            "protocol_id": case["protocol_id"],
            "protocol_qualification": self.manifest()["protocol_qualification"],
            "response_adapter": self._response_adapter_binding(),
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
                "raw_sha256": result.get("raw_sha256"),
                "parser_input_sha256": result.get("parser_input_sha256", result.get("raw_sha256")),
                "normalization": result.get("normalization"),
            })
            if "DENIED" in str(result.get("authority_outcome")) or result.get("authority_outcome") == "FORBIDDEN_RECORDED":
                anomalies.append({"turn": turn, "authority_outcome": result.get("authority_outcome")})
            turn_state = _load(directory / "state.json")
            runtime.append({"turn": turn, **turn_state.get("runtime", {})})
        source_state = ReadOnlyExecutor().compare_snapshot(_snapshot(case["snapshot_x"])).status.value
        patch = (self.root / "candidate" / "patch.diff").read_text(encoding="utf-8") if candidate else None
        validation = self._validation_summary()
        packet = {
            "session_id": self.root.name,
            "starting_head": manifest["repository"]["expected_head"],
            "snapshot_identity": manifest["repository"]["snapshot_identity"],
            "source_state": source_state,
            "objective": manifest["objective"],
            "authority": manifest["authority"],
            "protocol_id": manifest["protocol_id"],
            "protocol_qualification": manifest["protocol_qualification"],
            "response_adapter": self._response_adapter_binding(),
            "request_sequence": requests,
            "candidate_patch": patch,
            "changed_paths": candidate.get("changed_paths", []) if candidate else [],
            "executor_application": candidate.get("application") if candidate else None,
            "technical_correctness": validation["technical_correctness"],
            "validation_result": validation["status"],
            "visible_validation": validation.get("visible_validation"),
            "hidden_validation": validation.get("hidden_validation"),
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
