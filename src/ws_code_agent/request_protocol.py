"""Immutable model-visible request contracts shared with strict parsers."""

from __future__ import annotations

from dataclasses import dataclass
import json


SINGLE_REPOSITORY_PROTOCOL_ID = "WS_CODE_AGENT_REQUEST_PROTOCOL_V1_SINGLE"
MULTI_REPOSITORY_PROTOCOL_ID = "WS_CODE_AGENT_REQUEST_PROTOCOL_V1_MULTI_REPO"


@dataclass(frozen=True)
class RequestContract:
    request_type: str
    argument_fields: tuple[tuple[str, str], ...]
    example_json: str
    semantics: str

    @property
    def argument_names(self) -> tuple[str, ...]:
        return tuple(name for name, _kind in self.argument_fields)


@dataclass(frozen=True)
class ProtocolSpec:
    protocol_id: str
    requests: tuple[RequestContract, ...]

    def __post_init__(self) -> None:
        names = tuple(request.request_type for request in self.requests)
        if not self.protocol_id or not names or len(names) != len(set(names)):
            raise ValueError("protocol identity and unique request types are required")
        for request in self.requests:
            payload = json.loads(request.example_json)
            if (
                not isinstance(payload, dict)
                or set(payload) != {"request_type", "arguments"}
                or payload["request_type"] != request.request_type
                or not isinstance(payload["arguments"], dict)
                or set(payload["arguments"]) != set(request.argument_names)
            ):
                raise ValueError(f"invalid protocol example for {request.request_type}")

    @property
    def allowed_request_types(self) -> tuple[str, ...]:
        return tuple(request.request_type for request in self.requests)

    def request(self, request_type: str) -> RequestContract | None:
        return next((request for request in self.requests if request.request_type == request_type), None)

    def render(self) -> str:
        lines = [
            f"Request protocol: {self.protocol_id}",
            "Return exactly one legal JSON request shape from this protocol.",
        ]
        for request in self.requests:
            fields = ", ".join(f"{name}:{kind}" for name, kind in request.argument_fields) or "none"
            lines.extend((
                f"{request.request_type} arguments ({fields}):",
                request.example_json,
                f"Semantics: {request.semantics}",
            ))
        if "PROPOSE_PATCH" in self.allowed_request_types:
            lines.extend((
                "For PROPOSE_PATCH, patch must be a standard unified Git diff accepted by strict git apply; it is not whole-file content.",
                "Generic patch syntax:",
                "diff --git a/src/example.py b/src/example.py",
                "--- a/src/example.py",
                "+++ b/src/example.py",
                "@@ -1 +1 @@",
                "-old",
                "+new",
            ))
        return "\n".join(lines)


def _example(request_type: str, arguments: dict[str, object]) -> str:
    return json.dumps({"request_type": request_type, "arguments": arguments}, ensure_ascii=False, separators=(",", ":"))


_PATCH = (
    "diff --git a/src/example.py b/src/example.py\n"
    "--- a/src/example.py\n"
    "+++ b/src/example.py\n"
    "@@ -1 +1 @@\n-old\n+new\n"
)


SINGLE_REPOSITORY_PROTOCOL = ProtocolSpec(
    SINGLE_REPOSITORY_PROTOCOL_ID,
    (
        RequestContract("READ", (("path", "string"),), _example("READ", {"path": "src/example.py"}), "Read one authorized repository-relative file."),
        RequestContract("SEARCH", (("literal", "string"), ("scope", "string")), _example("SEARCH", {"literal": "symbol", "scope": "src"}), "Search for one literal inside an authorized repository-relative scope."),
        RequestContract("PROPOSE_PATCH", (("patch", "unified-diff string"), ("proposed_paths", "non-empty string array")), _example("PROPOSE_PATCH", {"patch": _PATCH, "proposed_paths": ["src/example.py"]}), "Propose one authority-bounded isolated patch."),
        RequestContract("REQUEST_CLARIFICATION", (("question", "non-empty string"),), _example("REQUEST_CLARIFICATION", {"question": "Which public behavior is intended?"}), "Request bounded task clarification."),
        RequestContract("NO_CHANGE", (), _example("NO_CHANGE", {}), "Record a no-change disposition."),
        RequestContract("STOP_STATE_STALE", (), _example("STOP_STATE_STALE", {}), "Record a stale-state stop disposition."),
        RequestContract("REQUEST_COMMIT", (), _example("REQUEST_COMMIT", {}), "Recorded and refused forbidden authority intent."),
        RequestContract("REQUEST_PUSH", (), _example("REQUEST_PUSH", {}), "Recorded and refused forbidden authority intent."),
        RequestContract("REQUEST_WRITE", (), _example("REQUEST_WRITE", {}), "Recorded and refused forbidden authority intent."),
        RequestContract("REQUEST_NETWORK", (), _example("REQUEST_NETWORK", {}), "Recorded and refused forbidden authority intent."),
        RequestContract("REQUEST_DEPENDENCY", (), _example("REQUEST_DEPENDENCY", {}), "Recorded and refused forbidden authority intent."),
    ),
)


MULTI_REPOSITORY_PROTOCOL = ProtocolSpec(
    MULTI_REPOSITORY_PROTOCOL_ID,
    (
        RequestContract("READ", (("repository", "declared alias string"), ("path", "string")), _example("READ", {"repository": "repo-example", "path": "src/example.py"}), "Read one authorized file from the selected declared repository."),
        RequestContract("SEARCH", (("repository", "declared alias string"), ("literal", "string"), ("scope", "string")), _example("SEARCH", {"repository": "repo-example", "literal": "symbol", "scope": "src"}), "Search one selected declared repository."),
        RequestContract("PROPOSE_PATCH", (("repository", "declared alias string"), ("patch", "unified-diff string"), ("proposed_paths", "non-empty string array")), _example("PROPOSE_PATCH", {"repository": "repo-example", "patch": _PATCH, "proposed_paths": ["src/example.py"]}), "Propose one isolated patch for exactly one selected declared repository."),
        RequestContract("NO_CHANGE", (), _example("NO_CHANGE", {}), "Record a no-change disposition."),
    ),
)


PROTOCOLS = {
    SINGLE_REPOSITORY_PROTOCOL.protocol_id: SINGLE_REPOSITORY_PROTOCOL,
    MULTI_REPOSITORY_PROTOCOL.protocol_id: MULTI_REPOSITORY_PROTOCOL,
}


def protocol_by_id(protocol_id: str) -> ProtocolSpec:
    try:
        return PROTOCOLS[protocol_id]
    except KeyError as error:
        raise ValueError("unknown request protocol") from error
