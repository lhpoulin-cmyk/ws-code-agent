"""Fixed-profile Katra text transport for the Task 10A disposition experiment.

This module is deliberately not a provider framework.  It sends one rendered
text prompt through gpu-compute's accepted ``bin/run`` path, retrieves the raw
text artifact, and retains the policy evidence emitted by that path.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import shlex
import subprocess
from typing import Any, Callable, Protocol

from .request_protocol import ProtocolSpec


MODEL_TAG = "qwen3-coder:30b"
MODEL_DIGEST = "06c1097efce0431c2045fe7b2e5108366e43bee1b4603a7aded8f21689e90bca"
MODEL_QUANTIZATION = "Q4_K_M"
EXECUTION_POLICY = "gpu-primary-partial"
DEVSTRAL_MODEL_TAG = "devstral-small-2:24b-instruct-2512-q4_K_M"
DEVSTRAL_MODEL_DIGEST = "24277f07f62db8f9cb68e9dfc679ea1818a7fbac47a50eff0a701d3f645b63c8"
DEVSTRAL_MODEL_QUANTIZATION = "Q4_K_M"
DEVSTRAL_EXECUTION_POLICY = "gpu-primary-partial"
QWEN25_MODEL_TAG = "qwen2.5-coder:14b-instruct-q4_K_M"
QWEN25_MODEL_DIGEST = "9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849"
QWEN25_MODEL_QUANTIZATION = "Q4_K_M"
QWEN25_EXECUTION_POLICY = "gpu-only"
QWEN25_32B_MODEL_TAG = "qwen2.5-coder:32b-instruct-q4_K_M"
QWEN25_32B_MODEL_DIGEST = "b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41"
QWEN25_32B_MODEL_QUANTIZATION = "Q4_K_M"
QWEN25_32B_EXECUTION_POLICY = "gpu-primary-partial"
# The retained VM hostname is not presently resolvable from ws-matriarch.  The
# approved operator path is the documented VM 320 address plus the vault-backed
# SSH certificate; neither is model-controlled.
REMOTE_HOST = "192.168.10.92"
SSH_IDENTITY = "/home/louis/lab-root-trust/ssh-ca/lab-operator-ed25519"
SSH_CERTIFICATE = "/home/louis/lab-root-trust/ssh-ca/lab-operator-ed25519-cert.pub"
REMOTE_RUNNER = "/srv/gpu-compute/bin/run"
REMOTE_STATUS = "/srv/gpu-compute/bin/run-status"
REMOTE_EVIDENCE_ROOT = "/srv/gpu-compute/evidence"
REMOTE_TEMP_ROOT = "/tmp"
RESPONSE_EVIDENCE_CONTRACT = "OLLAMA_RESPONSE_META_V2"
_JOB_ID = re.compile(r"\[?(job-[0-9]{8}T[0-9]{6}Z-[0-9]+)\]?")


class KatraOllamaBackendError(RuntimeError):
    """The fixed transport or runtime profile could not establish a turn."""

    def __init__(self, message: str, *, exit_code: int | None = None, stdout: bytes = b"", stderr: bytes = b"") -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.stdout = stdout.decode("utf-8", errors="replace")
        self.stderr = stderr.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class RuntimeTurnEvidence:
    raw_sha256: str
    job_id: str
    manifest_digest: str
    quantization: str
    execution_policy: str
    policy_result: str
    observed_cpu_percent: int
    observed_gpu_percent: int
    processor: str
    runner_stdout: str
    runner_stderr: str
    completion_evidence_contract: str | None = None
    completion_meta_sha256: str | None = None
    done: bool | None = None
    done_reason_present: bool | None = None
    done_reason: str | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_duration: int | None = None
    eval_duration: int | None = None


@dataclass(frozen=True)
class RuntimeFailureEvidence:
    stage: str
    exit_code: int | None
    stdout: str
    stderr: str


class ResponseEvidenceSink(Protocol):
    """Trusted local evidence commit point, invoked before remote cleanup."""

    def capture_response(self, raw_response: str, evidence: RuntimeTurnEvidence) -> None: ...


@dataclass(frozen=True)
class ExecutionArtifactIdentity:
    """Exact backend-owned artifact and runtime identity for durable intent."""

    model_tag: str
    manifest_digest: str
    quantization: str
    runtime_profile_id: str
    execution_policy: str


@dataclass(frozen=True)
class InferenceInvocation:
    invocation_id: str
    prompt_sha256: str
    execution_identity: ExecutionArtifactIdentity


@dataclass(frozen=True)
class FixedKatraRuntimeProfile:
    profile_id: str
    model_tag: str
    manifest_digest: str
    quantization: str
    execution_policy: str
    policy_result: str
    minimum_gpu_percent: int
    maximum_cpu_percent: int

    @property
    def execution_identity(self) -> ExecutionArtifactIdentity:
        return ExecutionArtifactIdentity(
            model_tag=self.model_tag,
            manifest_digest=self.manifest_digest,
            quantization=self.quantization,
            runtime_profile_id=self.profile_id,
            execution_policy=self.execution_policy,
        )


QWEN_RUNTIME_PROFILE = FixedKatraRuntimeProfile(
    "qwen3-coder-30b-katra-partial",
    MODEL_TAG,
    MODEL_DIGEST,
    MODEL_QUANTIZATION,
    EXECUTION_POLICY,
    "GPU_PRIMARY_PARTIAL_OFFLOAD",
    80,
    20,
)
DEVSTRAL_RUNTIME_PROFILE = FixedKatraRuntimeProfile(
    "devstral-small-2-24b-katra-partial",
    DEVSTRAL_MODEL_TAG,
    DEVSTRAL_MODEL_DIGEST,
    DEVSTRAL_MODEL_QUANTIZATION,
    DEVSTRAL_EXECUTION_POLICY,
    "GPU_PRIMARY_PARTIAL_OFFLOAD",
    88,
    12,
)
QWEN25_RUNTIME_PROFILE = FixedKatraRuntimeProfile(
    "qwen25-coder-14b-katra-4096",
    QWEN25_MODEL_TAG,
    QWEN25_MODEL_DIGEST,
    QWEN25_MODEL_QUANTIZATION,
    QWEN25_EXECUTION_POLICY,
    "GPU_ONLY",
    100,
    0,
)
QWEN25_32B_RUNTIME_PROFILE = FixedKatraRuntimeProfile(
    "qwen25-coder-32b-katra-4096",
    QWEN25_32B_MODEL_TAG,
    QWEN25_32B_MODEL_DIGEST,
    QWEN25_32B_MODEL_QUANTIZATION,
    QWEN25_32B_EXECUTION_POLICY,
    "GPU_PRIMARY_PARTIAL_OFFLOAD",
    71,
    29,
)


class KatraOllamaDispositionBackend:
    """Text-only, exact-artifact backend for a single accepted Katra profile."""

    RUNTIME_PROFILE = QWEN_RUNTIME_PROFILE

    def __init__(self, run_process: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run) -> None:
        self._run_process = run_process
        self.turn_evidence: list[RuntimeTurnEvidence] = []
        self.failure_evidence: list[RuntimeFailureEvidence] = []

    @property
    def execution_identity(self) -> ExecutionArtifactIdentity:
        return self.RUNTIME_PROFILE.execution_identity

    def generate(self, messages: tuple[dict[str, Any], ...], *, protocol: ProtocolSpec, invocation: InferenceInvocation, evidence_sink: ResponseEvidenceSink | None = None) -> str:
        prompt = self._render_prompt(messages, protocol)
        if invocation.execution_identity != self.execution_identity:
            raise KatraOllamaBackendError("DURABLE_MODEL_BINDING_MISMATCH")
        if not re.fullmatch(r"alpha-[A-Za-z0-9][A-Za-z0-9._-]{15,119}", invocation.invocation_id):
            raise KatraOllamaBackendError("invalid durable invocation identity")
        if hashlib.sha256(prompt.encode()).hexdigest() != invocation.prompt_sha256:
            raise KatraOllamaBackendError("durable invocation prompt mismatch")
        run = self._ssh(self._runner_command(prompt, invocation.invocation_id), required=False)
        try:
            if run.returncode != 0:
                self.failure_evidence.append(RuntimeFailureEvidence(
                    "controlled-run", run.returncode, run.stdout.decode("utf-8", errors="replace"),
                    run.stderr.decode("utf-8", errors="replace"),
                ))
                raise KatraOllamaBackendError(
                    f"controlled inference failed: exit {run.returncode}", exit_code=run.returncode,
                    stdout=run.stdout, stderr=run.stderr,
                )
            job_id = self._job_id(run.stdout)
            raw = self._ssh(("/usr/bin/cat", "--", f"{REMOTE_EVIDENCE_ROOT}/invocations/{invocation.invocation_id}/response.txt"))
            if raw.returncode != 0:
                raise KatraOllamaBackendError("controlled inference output retrieval failed")
            evidence = self._fetch_evidence(job_id)
            completion = self._fetch_completion_meta(invocation.invocation_id, evidence)
            text = raw.stdout.decode("utf-8", errors="strict")
            turn_evidence = self._validate_evidence(text, job_id, evidence, completion, run)
            # The remote output is disposable only after a trusted local sink
            # has durably accepted the exact bytes and runtime evidence.
            if evidence_sink is not None:
                evidence_sink.capture_response(text, turn_evidence)
            self.turn_evidence.append(turn_evidence)
            return text
        except UnicodeDecodeError as error:
            raise KatraOllamaBackendError("model response was not UTF-8 text") from error
        finally:
            pass

    @classmethod
    def invocation_for(cls, messages: tuple[dict[str, Any], ...], invocation_id: str, *, protocol: ProtocolSpec) -> InferenceInvocation:
        return InferenceInvocation(
            invocation_id,
            hashlib.sha256(cls._render_prompt(messages, protocol).encode()).hexdigest(),
            cls.RUNTIME_PROFILE.execution_identity,
        )

    @staticmethod
    def _render_prompt(messages: tuple[dict[str, Any], ...], protocol: ProtocolSpec) -> str:
        rendered: list[str] = [
            "You are interacting with a bounded coding disposition harness.",
            "Return exactly one JSON object and nothing else.",
            "The object must have exactly request_type and arguments.",
            "Do not use markdown, tools, shell commands, or prose outside the JSON object.",
            protocol.render(),
            "Conversation follows as JSON values; tool messages are bounded harness projections.",
        ]
        for message in messages:
            if not isinstance(message, dict) or set(message) != {"role", "content"} or message["role"] not in {"user", "tool"}:
                raise KatraOllamaBackendError("backend received an invalid harness message")
            rendered.append(f"{message['role'].upper()}: {json.dumps(message['content'], sort_keys=True, ensure_ascii=False, separators=(',', ':'))}")
        return "\n".join(rendered)

    @staticmethod
    def _remote_command(arguments: tuple[str, ...]) -> str:
        return " ".join(shlex.quote(value) for value in arguments)

    def _ssh(self, remote_arguments: tuple[str, ...], *, required: bool = True) -> subprocess.CompletedProcess[bytes]:
        command = (
            "/usr/bin/ssh", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no", "-o", "ClearAllForwardings=yes",
            "-o", "RequestTTY=no", "-i", SSH_IDENTITY, "-o", f"CertificateFile={SSH_CERTIFICATE}",
            f"louis@{REMOTE_HOST}", self._remote_command(remote_arguments),
        )
        result = self._run_process(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if required and result.returncode != 0:
            raise KatraOllamaBackendError(
                f"approved Katra transport failed: exit {result.returncode}", exit_code=result.returncode,
                stdout=result.stdout, stderr=result.stderr,
            )
        return result

    @classmethod
    def _runner_command(cls, prompt: str, invocation_id: str) -> tuple[str, ...]:
        profile = cls.RUNTIME_PROFILE
        return (REMOTE_RUNNER, "--invocation-id", invocation_id, "--model", profile.model_tag, "--prompt", prompt,
                "--execution-policy", profile.execution_policy)

    @staticmethod
    def _job_id(stdout: bytes) -> str:
        match = _JOB_ID.search(stdout.decode("utf-8", errors="replace"))
        if match is None:
            raise KatraOllamaBackendError("controlled runner did not return a bounded job identity")
        return match.group(1)

    def _fetch_evidence(self, job_id: str) -> dict[str, str]:
        if not _JOB_ID.fullmatch(job_id):
            raise KatraOllamaBackendError("unsafe controlled-run job identity")
        base = f"{REMOTE_EVIDENCE_ROOT}/{job_id}"
        paths = (f"{base}/meta.yaml", f"{base}/policy-result.yaml", f"{base}/ollama-ps.txt")
        fetched = self._ssh(("/usr/bin/cat", "--", *paths))
        if fetched.returncode != 0:
            raise KatraOllamaBackendError("controlled runtime evidence retrieval failed")
        text = fetched.stdout.decode("utf-8", errors="strict")
        values: dict[str, str] = {}
        for line in text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                if key.strip() in {
                    "invocation_id", "manifest_digest", "quantization",
                    "execution_policy", "policy_result", "observed_cpu_percent",
                    "observed_gpu_percent", "observed_processor",
                    "response_evidence_contract", "completion_meta_sha256",
                }:
                    values[key.strip()] = value.strip()
        return values

    def _fetch_completion_meta(self, invocation_id: str, evidence: dict[str, str]) -> dict[str, Any]:
        if evidence.get("invocation_id") != invocation_id:
            raise KatraOllamaBackendError("controlled completion evidence invocation mismatch")
        expected_sha = evidence.get("completion_meta_sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise KatraOllamaBackendError("controlled completion evidence identity is invalid")
        fetched = self._ssh((
            "/usr/bin/cat", "--",
            f"{REMOTE_EVIDENCE_ROOT}/invocations/{invocation_id}/ollama-envelope-meta.json",
        ))
        if fetched.returncode != 0:
            raise KatraOllamaBackendError("controlled completion evidence retrieval failed")
        if hashlib.sha256(fetched.stdout).hexdigest() != expected_sha:
            raise KatraOllamaBackendError("controlled completion evidence hash mismatch")
        try:
            completion = json.loads(fetched.stdout.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise KatraOllamaBackendError("controlled completion evidence is invalid") from error
        numeric_fields = {
            "prompt_eval_count", "eval_count", "total_duration", "load_duration",
            "prompt_eval_duration", "eval_duration",
        }
        required = {
            "evidence_contract", "envelope_body_byte_count", "envelope_body_sha256",
            "envelope_syntax_valid", "failure_classification", "model_present", "model",
            "response_present", "response_byte_count", "response_sha256", "done_present",
            "done", "done_reason_present", "done_reason",
        } | numeric_fields | {f"{name}_present" for name in numeric_fields}
        if not isinstance(completion, dict) or not required <= set(completion):
            raise KatraOllamaBackendError("controlled completion evidence fields are invalid")
        for name in numeric_fields:
            present = completion[f"{name}_present"]
            value = completion[name]
            if not isinstance(present, bool):
                raise KatraOllamaBackendError("controlled completion evidence presence is invalid")
            if present:
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise KatraOllamaBackendError("controlled completion evidence counts are invalid")
            elif value is not None:
                raise KatraOllamaBackendError("controlled completion absent value is invalid")
        reason_present = completion["done_reason_present"]
        reason = completion["done_reason"]
        if not isinstance(reason_present, bool) or (reason_present and not isinstance(reason, str)) or (not reason_present and reason is not None):
            raise KatraOllamaBackendError("controlled completion reason evidence is invalid")
        return completion

    @classmethod
    def _validate_evidence(cls, raw: str, job_id: str, evidence: dict[str, str], completion: dict[str, Any], run: subprocess.CompletedProcess[bytes]) -> RuntimeTurnEvidence:
        required = {
            "invocation_id", "manifest_digest", "quantization", "execution_policy",
            "policy_result", "observed_cpu_percent", "observed_gpu_percent",
            "observed_processor", "response_evidence_contract",
            "completion_meta_sha256",
        }
        if not required <= set(evidence):
            raise KatraOllamaBackendError("controlled runtime evidence is incomplete")
        try:
            cpu, gpu = int(evidence["observed_cpu_percent"]), int(evidence["observed_gpu_percent"])
        except ValueError as error:
            raise KatraOllamaBackendError("controlled runtime processor evidence is invalid") from error
        profile = cls.RUNTIME_PROFILE
        if (evidence["manifest_digest"] != profile.manifest_digest or evidence["quantization"] != profile.quantization
                or evidence["execution_policy"] != profile.execution_policy or evidence["policy_result"] != profile.policy_result
                or gpu < profile.minimum_gpu_percent or cpu > profile.maximum_cpu_percent
                or evidence["response_evidence_contract"] != RESPONSE_EVIDENCE_CONTRACT
                or completion["evidence_contract"] != RESPONSE_EVIDENCE_CONTRACT
                or completion["envelope_syntax_valid"] is not True
                or completion["failure_classification"] is not None
                or completion["model_present"] is not True
                or completion["model"] != profile.model_tag
                or completion["response_present"] is not True
                or completion["response_byte_count"] != len(raw.encode("utf-8"))
                or completion["response_sha256"] != hashlib.sha256(raw.encode("utf-8")).hexdigest()
                or completion["done_present"] is not True or completion["done"] is not True):
            raise KatraOllamaBackendError("accepted Katra runtime profile was not satisfied")
        return RuntimeTurnEvidence(
            hashlib.sha256(raw.encode("utf-8")).hexdigest(), job_id, evidence["manifest_digest"],
            evidence["quantization"], evidence["execution_policy"], evidence["policy_result"], cpu, gpu,
            evidence["observed_processor"], run.stdout.decode("utf-8", errors="replace"),
            run.stderr.decode("utf-8", errors="replace"), RESPONSE_EVIDENCE_CONTRACT,
            evidence["completion_meta_sha256"], completion["done"],
            completion["done_reason_present"], completion["done_reason"],
            completion["prompt_eval_count"], completion["eval_count"],
            completion["total_duration"], completion["load_duration"],
            completion["prompt_eval_duration"], completion["eval_duration"],
        )


class DevstralKatraOllamaDispositionBackend(KatraOllamaDispositionBackend):
    """Exact selected Devstral challenger bound to its accepted Katra profile."""

    RUNTIME_PROFILE = DEVSTRAL_RUNTIME_PROFILE


class Qwen25KatraOllamaDispositionBackend(KatraOllamaDispositionBackend):
    """Exact selected Qwen2.5 challenger bound to its accepted Katra profile."""

    RUNTIME_PROFILE = QWEN25_RUNTIME_PROFILE


class Qwen25_32BKatraOllamaDispositionBackend(KatraOllamaDispositionBackend):
    """Exact Qwen2.5-Coder 32B scale control bound to its accepted profile."""

    RUNTIME_PROFILE = QWEN25_32B_RUNTIME_PROFILE
