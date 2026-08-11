"""Unit tests for the fixed-profile Katra text transport; no remote call occurs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.katra_ollama_backend import (  # noqa: E402
    DEVSTRAL_MODEL_DIGEST, DEVSTRAL_MODEL_TAG, DEVSTRAL_RUNTIME_PROFILE,
    DevstralKatraOllamaDispositionBackend, EXECUTION_POLICY,
    KatraOllamaBackendError, KatraOllamaDispositionBackend,
    MODEL_DIGEST, MODEL_QUANTIZATION, MODEL_TAG, REMOTE_HOST, REMOTE_RUNNER, SSH_CERTIFICATE, SSH_IDENTITY,
)
from ws_code_agent.request_protocol import SINGLE_REPOSITORY_PROTOCOL  # noqa: E402


class FakeTransport:
    def __init__(self, *, fail_first: bool = False, devstral: bool = False) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.fail_first = fail_first
        self.devstral = devstral

    def completion_bytes(self) -> bytes:
        model = DEVSTRAL_MODEL_TAG if self.devstral else MODEL_TAG
        return (json.dumps({
            "evidence_contract": "OLLAMA_RESPONSE_META_V1",
            "model": model,
            "done": True,
            "done_reason_present": True,
            "done_reason": "stop",
            "prompt_eval_count": 17,
            "eval_count": 23,
            "total_duration": 101,
            "load_duration": 11,
            "prompt_eval_duration": 31,
            "eval_duration": 59,
        }, sort_keys=True, separators=(",", ":")) + "\n").encode()

    def __call__(self, command, **_kwargs):
        self.calls.append(tuple(command))
        remote = shlex.split(command[-1])
        if self.fail_first and len(self.calls) == 1:
            return subprocess.CompletedProcess(command, 255, b"", b"transport failed")
        if remote[0] == REMOTE_RUNNER:
            return subprocess.CompletedProcess(command, 0, b"[job-20260810T120000Z-42] succeeded\n", b"")
        if remote[0] == "/usr/bin/cat" and remote[-1].endswith("ollama-response-meta.json"):
            return subprocess.CompletedProcess(command, 0, self.completion_bytes(), b"")
        if remote[0] == "/usr/bin/cat" and "meta.yaml" in remote[2]:
            digest = DEVSTRAL_MODEL_DIGEST if self.devstral else MODEL_DIGEST
            cpu, gpu = (12, 88) if self.devstral else (20, 80)
            return subprocess.CompletedProcess(command, 0, (
                "invocation_id: alpha-test-family-C01-t0001-abcdef\n"
                f"manifest_digest: {digest}\nquantization: {MODEL_QUANTIZATION}\nexecution_policy: {EXECUTION_POLICY}\n"
                f"policy_result: GPU_PRIMARY_PARTIAL_OFFLOAD\nobserved_cpu_percent: {cpu}\nobserved_gpu_percent: {gpu}\n"
                f"observed_processor: {cpu}%/{gpu}% CPU/GPU\n"
                "response_evidence_contract: OLLAMA_RESPONSE_META_V1\n"
                f"completion_meta_sha256: {hashlib.sha256(self.completion_bytes()).hexdigest()}\n"
            ).encode(), b"")
        if remote[0] == "/usr/bin/cat":
            return subprocess.CompletedProcess(command, 0, b'{"request_type":"NO_CHANGE","arguments":{}}\n', b"")
        return subprocess.CompletedProcess(command, 0, b"", b"")


class KatraOllamaBackendTests(unittest.TestCase):
    @staticmethod
    def generate(backend, messages, **kwargs):
        invocation=backend.invocation_for(messages,"alpha-test-family-C01-t0001-abcdef",protocol=SINGLE_REPOSITORY_PROTOCOL)
        return backend.generate(messages,protocol=SINGLE_REPOSITORY_PROTOCOL,invocation=invocation,**kwargs)
    def test_fixed_profile_transport_preserves_raw_response_and_runtime_evidence(self) -> None:
        transport = FakeTransport()
        backend = KatraOllamaDispositionBackend(transport)
        raw = self.generate(backend,({"role": "user", "content": {"case": "C01"}},))
        self.assertEqual('{"request_type":"NO_CHANGE","arguments":{}}\n', raw)
        self.assertEqual(1, len(backend.turn_evidence))
        evidence = backend.turn_evidence[0]
        self.assertEqual(MODEL_DIGEST, evidence.manifest_digest)
        self.assertEqual(MODEL_QUANTIZATION, evidence.quantization)
        self.assertEqual(EXECUTION_POLICY, evidence.execution_policy)
        self.assertEqual((20, 80), (evidence.observed_cpu_percent, evidence.observed_gpu_percent))
        self.assertEqual("OLLAMA_RESPONSE_META_V1", evidence.completion_evidence_contract)
        self.assertEqual("stop", evidence.done_reason)
        self.assertEqual((17, 23), (evidence.prompt_eval_count, evidence.eval_count))
        inference = shlex.split(transport.calls[0][-1])
        self.assertEqual((REMOTE_RUNNER, "--invocation-id"), tuple(inference[:2]))
        self.assertIn(MODEL_TAG,inference)
        self.assertIn("--execution-policy", inference)
        self.assertEqual(EXECUTION_POLICY, inference[-1])
        self.assertNotIn("--tools", inference)
        self.assertIn(SSH_IDENTITY, transport.calls[0])
        self.assertIn(f"CertificateFile={SSH_CERTIFICATE}", transport.calls[0])
        self.assertIn(f"louis@{REMOTE_HOST}", transport.calls[0])

    def test_prompt_is_one_quoted_argument_not_a_remote_shell_program(self) -> None:
        transport = FakeTransport()
        backend = KatraOllamaDispositionBackend(transport)
        injected = "'; touch /tmp/escaped; #"
        self.generate(backend,({"role": "user", "content": injected},))
        remote = shlex.split(transport.calls[0][-1])
        prompt = remote[remote.index("--prompt") + 1]
        self.assertIn(injected, prompt)
        self.assertNotIn("touch", remote[:remote.index("--prompt")])
        self.assertEqual(REMOTE_RUNNER, remote[0])

    def test_devstral_backend_is_exact_profile_bound_and_fail_closed(self) -> None:
        transport = FakeTransport(devstral=True)
        backend = DevstralKatraOllamaDispositionBackend(transport)
        self.generate(backend, ({"role": "user", "content": {"fixture": "write"}},))
        inference = shlex.split(transport.calls[0][-1])
        self.assertEqual(DEVSTRAL_MODEL_TAG, inference[inference.index("--model") + 1])
        evidence = backend.turn_evidence[0]
        self.assertEqual(DEVSTRAL_RUNTIME_PROFILE.profile_id, backend.RUNTIME_PROFILE.profile_id)
        self.assertEqual(DEVSTRAL_MODEL_DIGEST, evidence.manifest_digest)
        self.assertEqual((12, 88), (evidence.observed_cpu_percent, evidence.observed_gpu_percent))
        with self.assertRaises(KatraOllamaBackendError):
            self.generate(
                DevstralKatraOllamaDispositionBackend(FakeTransport()),
                ({"role": "user", "content": {"fixture": "write"}},),
            )

    def test_transport_failure_and_profile_violation_fail_closed(self) -> None:
        failed = KatraOllamaDispositionBackend(FakeTransport(fail_first=True))
        with self.assertRaises(KatraOllamaBackendError) as captured:
            self.generate(failed,({"role": "user", "content": {}},))
        self.assertEqual(255, captured.exception.exit_code)
        self.assertEqual("transport failed", captured.exception.stderr)
        self.assertEqual(1, len(failed.failure_evidence))
        self.assertEqual("transport failed", failed.failure_evidence[0].stderr)

        class BadEvidence(FakeTransport):
            def __call__(self, command, **kwargs):
                result = super().__call__(command, **kwargs)
                if shlex.split(command[-1])[0] == "/usr/bin/cat" and "meta.yaml" in shlex.split(command[-1])[2]:
                    return subprocess.CompletedProcess(command, 0, result.stdout.replace(b"observed_gpu_percent: 80", b"observed_gpu_percent: 79"), b"")
                return result

        with self.assertRaises(KatraOllamaBackendError):
            self.generate(KatraOllamaDispositionBackend(BadEvidence()),({"role": "user", "content": {}},))

        class NonterminalCompletion(FakeTransport):
            def completion_bytes(self):
                return super().completion_bytes().replace(b'"done":true', b'"done":false')

        with self.assertRaises(KatraOllamaBackendError):
            self.generate(KatraOllamaDispositionBackend(NonterminalCompletion()),({"role": "user", "content": {}},))

    def test_no_caller_model_or_policy_override_exists(self) -> None:
        with self.assertRaises(TypeError):
            KatraOllamaDispositionBackend(model="anything")  # type: ignore[call-arg]
        with self.assertRaises(KatraOllamaBackendError):
            self.generate(KatraOllamaDispositionBackend(),({"role": "tool", "content": {}, "extra": True},))

    def test_durable_sink_precedes_disposable_cleanup_and_failure_retains_output(self) -> None:
        events: list[str] = []
        class Sink:
            def capture_response(self, raw_response, evidence):
                events.append("durable:" + evidence.raw_sha256)
        transport = FakeTransport()
        self.generate(KatraOllamaDispositionBackend(transport),({"role": "user", "content": {}},),evidence_sink=Sink())
        self.assertTrue(events)
        self.assertFalse(any(shlex.split(call[-1])[0] == "/usr/bin/rm" for call in transport.calls))

        class FailingSink:
            def capture_response(self, raw_response, evidence):
                raise OSError("durable store unavailable")
        transport = FakeTransport()
        with self.assertRaises(OSError):
            self.generate(KatraOllamaDispositionBackend(transport),({"role": "user", "content": {}},),evidence_sink=FailingSink())
        self.assertFalse(any(shlex.split(call[-1])[0] == "/usr/bin/rm" for call in transport.calls))
