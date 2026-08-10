"""Model-visible request contracts remain equivalent to strict parsers."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.alpha_case_adapters import initialize_task10e  # noqa: E402
from ws_code_agent.calibration_orchestration import _parse_multi_repository_request  # noqa: E402
from ws_code_agent.disposition_harness import RequestParseError, parse_request  # noqa: E402
from ws_code_agent.katra_ollama_backend import KatraOllamaDispositionBackend  # noqa: E402
from ws_code_agent.request_protocol import (  # noqa: E402
    MULTI_REPOSITORY_PROTOCOL,
    MULTI_REPOSITORY_PROTOCOL_ID,
    SINGLE_REPOSITORY_PROTOCOL,
    SINGLE_REPOSITORY_PROTOCOL_ID,
)


class RequestProtocolTests(unittest.TestCase):
    def test_single_protocol_examples_equal_active_parser_contract(self) -> None:
        required = {"READ", "SEARCH", "PROPOSE_PATCH", "REQUEST_CLARIFICATION", "NO_CHANGE", "STOP_STATE_STALE"}
        self.assertTrue(required <= set(SINGLE_REPOSITORY_PROTOCOL.allowed_request_types))
        for contract in SINGLE_REPOSITORY_PROTOCOL.requests:
            with self.subTest(request_type=contract.request_type):
                parsed = parse_request(contract.example_json)
                self.assertEqual(contract.request_type, parsed.request_type.value)
                self.assertEqual(set(contract.argument_names), set(parsed.arguments))

    def test_multi_protocol_examples_equal_active_parser_contract(self) -> None:
        self.assertEqual(
            ("READ", "SEARCH", "PROPOSE_PATCH", "NO_CHANGE"),
            MULTI_REPOSITORY_PROTOCOL.allowed_request_types,
        )
        for contract in MULTI_REPOSITORY_PROTOCOL.requests:
            with self.subTest(request_type=contract.request_type):
                request_type, arguments = _parse_multi_repository_request(contract.example_json)
                self.assertEqual(contract.request_type, request_type)
                self.assertEqual(set(contract.argument_names), set(arguments))

    def test_required_field_removal_and_single_shape_fail_strictly(self) -> None:
        for protocol, parser, error in (
            (SINGLE_REPOSITORY_PROTOCOL, parse_request, RequestParseError),
            (MULTI_REPOSITORY_PROTOCOL, _parse_multi_repository_request, ValueError),
        ):
            for contract in protocol.requests:
                if not contract.argument_names:
                    continue
                payload = json.loads(contract.example_json)
                payload["arguments"].pop(contract.argument_names[0])
                with self.subTest(protocol=protocol.protocol_id, request_type=contract.request_type), self.assertRaises(error):
                    parser(json.dumps(payload))
        with self.assertRaises(ValueError):
            _parse_multi_repository_request('{"request_type":"READ","arguments":{"path":"src/example.py"}}')

    def test_documented_field_types_remain_strict(self) -> None:
        with self.assertRaises(RequestParseError):
            parse_request('{"request_type":"READ","arguments":{"path":["src/example.py"]}}')
        with self.assertRaises(RequestParseError):
            parse_request('{"request_type":"PROPOSE_PATCH","arguments":{"patch":"not a diff","proposed_paths":"src/example.py"}}')
        with self.assertRaises(ValueError):
            _parse_multi_repository_request('{"request_type":"READ","arguments":{"repository":["repo-a"],"path":"src/example.py"}}')
        with self.assertRaises(ValueError):
            _parse_multi_repository_request('{"request_type":"SEARCH","arguments":{"repository":"repo-a","literal":["symbol"],"scope":"src"}}')

    def test_backend_renders_only_the_harness_owned_protocol(self) -> None:
        messages = ({"role": "user", "content": {"task": "neutral"}},)
        single = KatraOllamaDispositionBackend._render_prompt(messages, SINGLE_REPOSITORY_PROTOCOL)
        multi = KatraOllamaDispositionBackend._render_prompt(messages, MULTI_REPOSITORY_PROTOCOL)
        self.assertIn(SINGLE_REPOSITORY_PROTOCOL_ID, single)
        self.assertIn(MULTI_REPOSITORY_PROTOCOL_ID, multi)
        for contract in SINGLE_REPOSITORY_PROTOCOL.requests:
            self.assertIn(contract.example_json, single)
        for contract in MULTI_REPOSITORY_PROTOCOL.requests:
            self.assertIn(contract.example_json, multi)
        self.assertNotIn("REQUEST_CLARIFICATION", multi)
        self.assertNotIn('"repository":"repo-example"', single)
        self.assertIn("standard unified Git diff", single)
        self.assertIn("standard unified Git diff", multi)

    def test_task10e_adapters_persist_protocol_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            controller = initialize_task10e(Path(temporary), {
                "experiment_id": "protocol-family",
                "experiment_harness_sha": "test",
                "case_order": ["C03", "C04", "C05-A", "C05-B"],
            })
            self.assertEqual(SINGLE_REPOSITORY_PROTOCOL_ID, controller._case("C03")["protocol_id"])
            self.assertEqual(SINGLE_REPOSITORY_PROTOCOL_ID, controller._case("C04")["protocol_id"])
            self.assertEqual(MULTI_REPOSITORY_PROTOCOL_ID, controller._case("C05-A")["protocol_id"])
            self.assertEqual(MULTI_REPOSITORY_PROTOCOL_ID, controller._case("C05-B")["protocol_id"])

    def test_c01_c02_single_protocol_compatibility(self) -> None:
        clarification = parse_request('{"request_type":"REQUEST_CLARIFICATION","arguments":{"question":"Which public behavior is intended?"}}')
        patch = parse_request(SINGLE_REPOSITORY_PROTOCOL.request("PROPOSE_PATCH").example_json)
        self.assertEqual("REQUEST_CLARIFICATION", clarification.request_type.value)
        self.assertEqual("PROPOSE_PATCH", patch.request_type.value)


if __name__ == "__main__":
    unittest.main()
