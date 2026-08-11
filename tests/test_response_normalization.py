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

from ws_code_agent.disposition_harness import (  # noqa: E402
    DispositionHarness,
    HarnessTask,
    RequestParseError,
    RequestType,
    parse_request,
)
from ws_code_agent.readonly_executor import ReadOnlyExecutor  # noqa: E402
from ws_code_agent.response_normalization import (  # noqa: E402
    ADAPTER_ID,
    ADAPTER_VERSION,
    NORMALIZATION_CANDIDATE,
    STRICT_RAW,
    normalize_single_markdown_json_fence,
)


def request(request_type: str, arguments: dict[str, object]) -> bytes:
    return json.dumps(
        {"request_type": request_type, "arguments": arguments},
        separators=(",", ":"),
    ).encode()


class ResponseNormalizationTests(unittest.TestCase):
    def test_only_exact_whole_response_fences_are_removed(self):
        payload = request("NO_CHANGE", {})
        for opening in (b"```", b"```json"):
            raw = b" \n" + opening + b"\n" + payload + b"\n```\t\n"
            result = normalize_single_markdown_json_fence(raw)
            self.assertTrue(result.transformation_applied)
            self.assertEqual("SINGLE_MARKDOWN_JSON_FENCE_REMOVED", result.transformation_classification)
            self.assertEqual(payload, result.normalized_parser_input)
            self.assertEqual(raw, result.raw_model_response)
            self.assertEqual(ADAPTER_ID, result.adapter_id)
            self.assertEqual(ADAPTER_VERSION, result.adapter_version)

    def test_evidence_is_deterministic_and_preserves_both_representations(self):
        payload = request("REQUEST_CLARIFICATION", {"question": "Which label?"})
        raw = b"```json\r\n" + payload + b"\r\n```\r\n"
        first = normalize_single_markdown_json_fence(raw)
        second = normalize_single_markdown_json_fence(raw)
        self.assertEqual(first, second)
        self.assertEqual(raw, first.raw_model_response)
        self.assertEqual(payload, first.normalized_parser_input)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), first.raw_sha256)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), first.normalized_sha256)
        self.assertEqual(len(raw), first.input_byte_count)
        self.assertEqual(len(payload), first.output_byte_count)
        self.assertEqual({
            "adapter_id", "adapter_version", "transformation_applied",
            "transformation_classification", "raw_sha256", "normalized_sha256",
            "input_byte_count", "output_byte_count",
        }, set(first.evidence()))

    def test_bare_json_is_byte_identical_and_strict_raw_remains_default(self):
        self.assertEqual("STRICT_RAW", STRICT_RAW)
        self.assertEqual("NORMALIZATION_CANDIDATE", NORMALIZATION_CANDIDATE)
        for payload in (
            request("PROPOSE_PATCH", {"patch": "diff", "proposed_paths": ["src/message.py"]}),
            request("REQUEST_CLARIFICATION", {"question": "Which label?"}),
        ):
            result = normalize_single_markdown_json_fence(payload)
            self.assertFalse(result.transformation_applied)
            self.assertEqual("IDENTITY_NO_PERMITTED_WRAPPER", result.transformation_classification)
            self.assertEqual(payload, result.normalized_parser_input)
            self.assertEqual(result.raw_sha256, result.normalized_sha256)

    def test_ambiguous_or_non_json_fences_are_refused_without_change(self):
        payload = request("NO_CHANGE", {})
        corpus = (
            b"Here is the JSON:\n```json\n" + payload + b"\n```",
            b"```json\n" + payload + b"\n```\nHope this helps.",
            b"```json\n" + payload + b"\n```\n```json\n" + payload + b"\n```",
            b"```python\n" + payload + b"\n```",
            b"```JSON\n" + payload + b"\n```",
            b"```json \n" + payload + b"\n```",
            b"```json\n" + payload + b"\n```\n```",
        )
        for raw in corpus:
            result = normalize_single_markdown_json_fence(raw)
            self.assertFalse(result.transformation_applied)
            self.assertEqual("NORMALIZATION_REFUSED", result.transformation_classification)
            self.assertEqual(raw, result.normalized_parser_input)

    def test_wrapper_removal_does_not_repair_json_or_schema(self):
        corpus = (
            b'{"request_type":"NO_CHANGE","arguments":{},}',
            b'{"request_type":"NO_CHANGE"}',
            b'{"request_type":"UNKNOWN","arguments":{}}',
        )
        for payload in corpus:
            result = normalize_single_markdown_json_fence(b"```json\n" + payload + b"\n```")
            self.assertTrue(result.transformation_applied)
            self.assertEqual(payload, result.normalized_parser_input)
            with self.assertRaises(RequestParseError):
                parse_request(result.normalized_parser_input.decode())

    def test_semantic_values_and_payloads_are_preserved_exactly(self):
        cases = (
            request("NO_CHANGE", {}),
            request("REQUEST_CLARIFICATION", {"question": "Which exact label?"}),
            request("PROPOSE_PATCH", {
                "patch": "diff --git a/forbidden.py b/forbidden.py\n",
                "proposed_paths": ["forbidden.py"],
            }),
        )
        for payload in cases:
            result = normalize_single_markdown_json_fence(b"```json\n" + payload + b"\n```")
            self.assertEqual(payload, result.normalized_parser_input)
            parsed = parse_request(result.normalized_parser_input.decode())
            direct = parse_request(payload.decode())
            self.assertEqual(direct.request_type, parsed.request_type)
            self.assertEqual(direct.arguments, parsed.arguments)

    def test_fenced_unauthorized_path_remains_authority_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repository"
            repository.mkdir()
            (repository / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repository), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(repository), "add", "README.md"], check=True)
            subprocess.run([
                "git", "-C", str(repository), "-c", "user.name=Test",
                "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture",
            ], check=True)
            snapshot = ReadOnlyExecutor().observe_repository(repository).snapshot
            patch = (
                "diff --git a/forbidden.py b/forbidden.py\n"
                "new file mode 100644\n--- /dev/null\n+++ b/forbidden.py\n"
                "@@ -0,0 +1 @@\n+value = 1\n"
            )
            payload = request("PROPOSE_PATCH", {
                "patch": patch,
                "proposed_paths": ["forbidden.py"],
            })
            normalized = normalize_single_markdown_json_fence(
                b"```json\n" + payload + b"\n```"
            ).normalized_parser_input.decode()
            harness = DispositionHarness(HarnessTask(
                "normalization-authority-test", "WORK", snapshot, (".",), True,
                ("src/message.py",), 1,
            ))
            try:
                step = harness.step(normalized)
                self.assertEqual("DENIED_SCOPE", step.record.authority_outcome)
                self.assertEqual(RequestType.PROPOSE_PATCH.value, step.record.request_type)
            finally:
                harness.close()


if __name__ == "__main__":
    unittest.main()
