"""Model-visible request contracts remain equivalent to strict parsers."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import re
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
    VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL,
    VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
)


V1_SINGLE_RENDER_SHA256 = "c9e7082955f796cad94c49f037acda3033728a80aec2f25d176f7378ec2d9367"
V1_MULTI_RENDER_SHA256 = "74ace33121cbc1d077509bf2d6aa3afb2933e6dbc994a66575d3fcfaf3991bd9"
V2_VALUE_FREE_RENDER_SHA256 = "3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e"


class RequestProtocolTests(unittest.TestCase):
    def test_frozen_v1_render_hashes_remain_unchanged(self) -> None:
        self.assertEqual(
            V1_SINGLE_RENDER_SHA256,
            hashlib.sha256(SINGLE_REPOSITORY_PROTOCOL.render().encode()).hexdigest(),
        )
        self.assertEqual(
            V1_MULTI_RENDER_SHA256,
            hashlib.sha256(MULTI_REPOSITORY_PROTOCOL.render().encode()).hexdigest(),
        )

    def test_value_free_v2_has_same_schema_without_populated_examples(self) -> None:
        self.assertEqual(
            VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL_ID,
            VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.protocol_id,
        )
        self.assertEqual(
            SINGLE_REPOSITORY_PROTOCOL.allowed_request_types,
            VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.allowed_request_types,
        )
        self.assertEqual(
            [
                (request.request_type, request.argument_fields, request.semantics)
                for request in SINGLE_REPOSITORY_PROTOCOL.requests
            ],
            [
                (request.request_type, request.argument_fields, request.semantics)
                for request in VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.requests
            ],
        )
        self.assertFalse(VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.has_populated_examples)
        self.assertTrue(all(
            request.example_json is None
            for request in VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.requests
        ))
        rendered = VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.render()
        self.assertEqual(
            V2_VALUE_FREE_RENDER_SHA256,
            hashlib.sha256(rendered.encode()).hexdigest(),
        )
        for forbidden in (
            "src/example.py",
            "src/message.py",
            "probe_alpha/neutral.py",
            "probe_beta/neutral.py",
            "foo.py",
            "repo-example",
            '"Which public behavior is intended?"',
            "-old",
            "+new",
        ):
            self.assertNotIn(forbidden, rendered)
        self.assertIsNone(re.search(
            r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",
            rendered,
        ))
        self.assertIn("Top-level object keys exactly: request_type, arguments.", rendered)
        self.assertIn("valid JSON object", rendered)

    def test_value_free_v2_schema_equals_strict_parser_contract(self) -> None:
        generated_patch = (
            "diff --git a/generated-target b/generated-target\n"
            "--- /dev/null\n"
            "+++ b/generated-target\n"
            "@@ -0,0 +1 @@\n"
            "+generated content\n"
        )
        valid_arguments = {
            "READ": {"path": "generated-target"},
            "SEARCH": {"literal": "generated-token", "scope": "."},
            "PROPOSE_PATCH": {
                "patch": generated_patch,
                "proposed_paths": ["generated-target"],
            },
            "REQUEST_CLARIFICATION": {"question": "Generated clarification request?"},
            "NO_CHANGE": {},
            "STOP_STATE_STALE": {},
            "REQUEST_COMMIT": {},
            "REQUEST_PUSH": {},
            "REQUEST_WRITE": {},
            "REQUEST_NETWORK": {},
            "REQUEST_DEPENDENCY": {},
        }
        for contract in VALUE_FREE_SINGLE_REPOSITORY_PROTOCOL.requests:
            payload = {
                "request_type": contract.request_type,
                "arguments": valid_arguments[contract.request_type],
            }
            with self.subTest(request_type=contract.request_type):
                parsed = parse_request(json.dumps(payload))
                self.assertEqual(contract.request_type, parsed.request_type.value)
                self.assertEqual(set(contract.argument_names), set(parsed.arguments))
                invalid = json.loads(json.dumps(payload))
                if contract.argument_names:
                    invalid["arguments"].pop(contract.argument_names[0])
                else:
                    invalid["arguments"]["unexpected"] = "generated"
                with self.assertRaises(RequestParseError):
                    parse_request(json.dumps(invalid))
                extra = json.loads(json.dumps(payload))
                extra["arguments"]["unexpected"] = "generated"
                with self.assertRaises(RequestParseError):
                    parse_request(json.dumps(extra))

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
