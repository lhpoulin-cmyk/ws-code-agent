"""Unit tests for the fixed-profile Katra text transport; no remote call occurs."""

from __future__ import annotations

from pathlib import Path
import shlex
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.katra_ollama_backend import (  # noqa: E402
    EXECUTION_POLICY, KatraOllamaBackendError, KatraOllamaDispositionBackend,
    MODEL_DIGEST, MODEL_QUANTIZATION, MODEL_TAG, REMOTE_HOST, REMOTE_RUNNER, SSH_CERTIFICATE, SSH_IDENTITY,
)


class FakeTransport:
    def __init__(self, *, fail_first: bool = False) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.fail_first = fail_first

    def __call__(self, command, **_kwargs):
        self.calls.append(tuple(command))
        remote = shlex.split(command[-1])
        if self.fail_first and len(self.calls) == 1:
            return subprocess.CompletedProcess(command, 255, b"", b"transport failed")
        if remote[0] == REMOTE_RUNNER:
            return subprocess.CompletedProcess(command, 0, b"[job-20260810T120000Z-42] succeeded\n", b"")
        if remote[0] == "/usr/bin/cat" and "meta.yaml" in remote[2]:
            return subprocess.CompletedProcess(command, 0, (
                f"manifest_digest: {MODEL_DIGEST}\nquantization: {MODEL_QUANTIZATION}\nexecution_policy: {EXECUTION_POLICY}\n"
                "policy_result: GPU_PRIMARY_PARTIAL_OFFLOAD\nobserved_cpu_percent: 20\nobserved_gpu_percent: 80\nobserved_processor: 20%/80% CPU/GPU\n"
            ).encode(), b"")
        if remote[0] == "/usr/bin/cat":
            return subprocess.CompletedProcess(command, 0, b'{"request_type":"NO_CHANGE","arguments":{}}\n', b"")
        return subprocess.CompletedProcess(command, 0, b"", b"")


class KatraOllamaBackendTests(unittest.TestCase):
    def test_fixed_profile_transport_preserves_raw_response_and_runtime_evidence(self) -> None:
        transport = FakeTransport()
        backend = KatraOllamaDispositionBackend(transport)
        raw = backend.generate(({"role": "user", "content": {"case": "C01"}},))
        self.assertEqual('{"request_type":"NO_CHANGE","arguments":{}}\n', raw)
        self.assertEqual(1, len(backend.turn_evidence))
        evidence = backend.turn_evidence[0]
        self.assertEqual(MODEL_DIGEST, evidence.manifest_digest)
        self.assertEqual(MODEL_QUANTIZATION, evidence.quantization)
        self.assertEqual(EXECUTION_POLICY, evidence.execution_policy)
        self.assertEqual((20, 80), (evidence.observed_cpu_percent, evidence.observed_gpu_percent))
        inference = shlex.split(transport.calls[0][-1])
        self.assertEqual((REMOTE_RUNNER, "--model", MODEL_TAG), tuple(inference[:3]))
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
        backend.generate(({"role": "user", "content": injected},))
        remote = shlex.split(transport.calls[0][-1])
        prompt = remote[remote.index("--prompt") + 1]
        self.assertIn(injected, prompt)
        self.assertNotIn("touch", remote[:remote.index("--prompt")])
        self.assertEqual(REMOTE_RUNNER, remote[0])

    def test_transport_failure_and_profile_violation_fail_closed(self) -> None:
        failed = KatraOllamaDispositionBackend(FakeTransport(fail_first=True))
        with self.assertRaises(KatraOllamaBackendError) as captured:
            failed.generate(({"role": "user", "content": {}},))
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
            KatraOllamaDispositionBackend(BadEvidence()).generate(({"role": "user", "content": {}},))

    def test_no_caller_model_or_policy_override_exists(self) -> None:
        with self.assertRaises(TypeError):
            KatraOllamaDispositionBackend(model="anything")  # type: ignore[call-arg]
        with self.assertRaises(KatraOllamaBackendError):
            KatraOllamaDispositionBackend().generate(({"role": "tool", "content": {}, "extra": True},))

    def test_durable_sink_precedes_disposable_cleanup_and_failure_retains_output(self) -> None:
        events: list[str] = []
        class Sink:
            def capture_response(self, raw_response, evidence):
                events.append("durable:" + evidence.raw_sha256)
        transport = FakeTransport()
        KatraOllamaDispositionBackend(transport).generate(({"role": "user", "content": {}},), evidence_sink=Sink())
        cleanup = next(index for index, call in enumerate(transport.calls) if shlex.split(call[-1])[0] == "/usr/bin/rm")
        self.assertTrue(events)
        self.assertGreater(cleanup, 0)

        class FailingSink:
            def capture_response(self, raw_response, evidence):
                raise OSError("durable store unavailable")
        transport = FakeTransport()
        with self.assertRaises(OSError):
            KatraOllamaDispositionBackend(transport).generate(({"role": "user", "content": {}},), evidence_sink=FailingSink())
        self.assertFalse(any(shlex.split(call[-1])[0] == "/usr/bin/rm" for call in transport.calls))
