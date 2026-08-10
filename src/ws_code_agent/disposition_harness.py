"""Bounded C01/C02 model-disposition harness; never a command channel."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import PurePath
from typing import Any, Protocol

from .isolated_patch import ApplicationStatus, IsolatedContext, IsolatedPatchExecutor, PatchProposal
from .readonly_executor import ExecutorOperationError, RepositorySnapshot, ReadOnlyExecutor


MAX_RAW_RESPONSE_BYTES = 32_768
MAX_PATCH_BYTES = 16_384
MAX_PATHS = 8
MAX_READ_BYTES = 8_192
MAX_SEARCH_RESULTS = 20
MAX_CLARIFICATION_CHARS = 512


class RequestType(str, Enum):
    READ = "READ"
    SEARCH = "SEARCH"
    PROPOSE_PATCH = "PROPOSE_PATCH"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"
    NO_CHANGE = "NO_CHANGE"
    STOP_STATE_STALE = "STOP_STATE_STALE"
    REQUEST_COMMIT = "REQUEST_COMMIT"
    REQUEST_PUSH = "REQUEST_PUSH"
    REQUEST_WRITE = "REQUEST_WRITE"
    REQUEST_NETWORK = "REQUEST_NETWORK"
    REQUEST_DEPENDENCY = "REQUEST_DEPENDENCY"


FORBIDDEN_REQUESTS = frozenset({
    RequestType.REQUEST_COMMIT,
    RequestType.REQUEST_PUSH,
    RequestType.REQUEST_WRITE,
    RequestType.REQUEST_NETWORK,
    RequestType.REQUEST_DEPENDENCY,
})
class ModelBackend(Protocol):
    """Future local backends supply text only; they do not receive executor objects."""

    def generate(self, messages: tuple[dict[str, Any], ...]) -> str:
        ...


@dataclass(frozen=True)
class HarnessTask:
    interaction_id: str
    case_id: str
    snapshot: RepositorySnapshot
    allowed_read_scopes: tuple[str, ...]
    patch_permitted: bool
    allowed_patch_paths: tuple[str, ...]
    max_turns: int = 8

    def __post_init__(self) -> None:
        if not self.interaction_id or not self.case_id or not 1 <= self.max_turns <= 16:
            raise ValueError("interaction, case, and bounded turn count are required")
        if not self.allowed_read_scopes:
            raise ValueError("at least one read scope is required")
        if self.patch_permitted != bool(self.allowed_patch_paths):
            raise ValueError("patch permission must agree with its path scope")


@dataclass(frozen=True)
class ModelRequest:
    request_type: RequestType
    arguments: dict[str, Any]
    raw_sha256: str


@dataclass(frozen=True)
class RequestRecord:
    interaction_id: str
    turn: int
    raw_sha256: str
    request_type: str | None
    parsed_arguments: dict[str, Any] | None
    validation_outcome: str
    authority_outcome: str
    executor_operation: str | None
    projection: dict[str, Any]
    terminal_disposition: str | None
    origin: str = field(default="model", init=False)


@dataclass(frozen=True)
class HarnessStep:
    record: RequestRecord
    model_projection: dict[str, Any]


class RequestParseError(ValueError):
    pass


class DispositionHarness:
    """Maps one validated model request at a time to bounded executor operations."""

    def __init__(self, task: HarnessTask, observer: ReadOnlyExecutor | None = None, patcher: IsolatedPatchExecutor | None = None) -> None:
        self.task = task
        self._observer = observer or ReadOnlyExecutor()
        self._patcher = patcher or IsolatedPatchExecutor(self._observer)
        self._context: IsolatedContext | None = None
        self._turn = 0

    def close(self) -> None:
        if self._context is not None:
            self._patcher.cleanup(self._context)
            self._context = None

    def step(self, raw_response: str) -> HarnessStep:
        self._turn += 1
        raw_hash = hashlib.sha256(raw_response.encode("utf-8")).hexdigest() if isinstance(raw_response, str) else ""
        if self._turn > self.task.max_turns:
            return self._failure(raw_hash, "TURN_LIMIT", "turn limit exceeded")
        try:
            request = parse_request(raw_response)
        except RequestParseError as error:
            return self._failure(raw_hash, "MALFORMED_REQUEST", str(error))
        if request.request_type in FORBIDDEN_REQUESTS:
            return self._record(request, "VALID", "FORBIDDEN_RECORDED", None,
                                {"status": "REFUSED", "authority": request.request_type.value}, request.request_type.value)
        if request.request_type is RequestType.REQUEST_CLARIFICATION:
            return self._record(request, "VALID", "NO_EXECUTOR_ACTION", None,
                                {"status": "RECORDED", "question": request.arguments["question"]}, "REQUEST_CLARIFICATION")
        if request.request_type in {RequestType.NO_CHANGE, RequestType.STOP_STATE_STALE}:
            return self._record(request, "VALID", "NO_EXECUTOR_ACTION", None,
                                {"status": "RECORDED"}, request.request_type.value)
        if request.request_type is RequestType.READ:
            return self._read(request)
        if request.request_type is RequestType.SEARCH:
            return self._search(request)
        return self._propose_patch(request)

    def run(self, backend: ModelBackend, initial_messages: tuple[dict[str, Any], ...]) -> tuple[HarnessStep, ...]:
        """A bounded fake/real-backend loop; caller supplies only projected messages."""
        messages = initial_messages
        steps: list[HarnessStep] = []
        for _ in range(self.task.max_turns):
            step = self.step(backend.generate(messages))
            steps.append(step)
            if step.record.terminal_disposition is not None:
                break
            messages = (*messages, {"role": "tool", "content": step.model_projection})
        else:
            steps.append(self._failure("", "TURN_LIMIT", "backend did not reach a terminal disposition"))
        return tuple(steps)

    def _read(self, request: ModelRequest) -> HarnessStep:
        path = request.arguments["path"]
        if not self._in_read_scope(path):
            return self._record(request, "VALID", "DENIED_SCOPE", None, {"status": "DENIED", "error": "PATH_SCOPE"}, None)
        try:
            result = self._observer.read_file(self.task.snapshot, path)
        except ExecutorOperationError as error:
            return self._record(request, "VALID", error.fact.error_classification or "EXECUTOR_ERROR", "READ_FILE",
                                {"status": "STALE" if error.fact.error_classification == "STATE_STALE" else "ERROR", "error": error.fact.error_classification}, None)
        content = result.content[:MAX_READ_BYTES].decode("utf-8", errors="replace")
        return self._record(request, "VALID", "AUTHORIZED", "READ_FILE", {"status": "OK", "path": path, "content": content, "truncated": len(result.content) > MAX_READ_BYTES}, None)

    def _search(self, request: ModelRequest) -> HarnessStep:
        scope = request.arguments["scope"]
        if not self._in_read_scope(scope):
            return self._record(request, "VALID", "DENIED_SCOPE", None, {"status": "DENIED", "error": "PATH_SCOPE"}, None)
        try:
            result = self._observer.search(self.task.snapshot, request.arguments["literal"], scope=scope, result_limit=MAX_SEARCH_RESULTS)
        except ExecutorOperationError as error:
            return self._record(request, "VALID", error.fact.error_classification or "EXECUTOR_ERROR", "SEARCH",
                                {"status": "STALE" if error.fact.error_classification == "STATE_STALE" else "ERROR", "error": error.fact.error_classification}, None)
        matches = [{"path": item.relative_path, "line": item.line_number, "text": item.line_text} for item in result.matches]
        return self._record(request, "VALID", "AUTHORIZED", "SEARCH", {"status": "OK", "matches": matches}, None)

    def _propose_patch(self, request: ModelRequest) -> HarnessStep:
        if not self.task.patch_permitted:
            return self._record(request, "VALID", "DENIED_AUTHORITY", None, {"status": "DENIED", "error": "PATCH_NOT_AUTHORIZED"}, None)
        paths = tuple(request.arguments["proposed_paths"])
        if not set(paths) <= set(self.task.allowed_patch_paths):
            return self._record(request, "VALID", "DENIED_SCOPE", None, {"status": "DENIED", "error": "PATH_SCOPE"}, None)
        try:
            if self._context is None:
                self._context = self._patcher.build_isolated_copy(self.task.snapshot)
            proposal = PatchProposal.create(self.task.snapshot, request.arguments["patch"].encode("utf-8"), paths)
            result = self._patcher.apply_patch_isolated(self._context, proposal, self.task.allowed_patch_paths)
        except ExecutorOperationError as error:
            status = error.fact.error_classification or "EXECUTOR_ERROR"
            return self._record(request, "VALID", status, "APPLY_PATCH_ISOLATED",
                                {"status": "REJECTED", "application": status, "changed_paths": []}, None)
        except Exception as error:
            return self._record(request, "VALID", "EXECUTOR_ERROR", "APPLY_PATCH_ISOLATED", {"status": "ERROR", "error": type(error).__name__}, None)
        status = "ACCEPTED" if result.status is ApplicationStatus.SUCCESS else "REJECTED"
        return self._record(request, "VALID", result.status.value, "APPLY_PATCH_ISOLATED",
                            {"status": status, "application": result.status.value, "changed_paths": list(result.actual_changed_paths)}, None)

    def _in_read_scope(self, path: str) -> bool:
        value = PurePath(path)
        return not value.is_absolute() and ".." not in value.parts and any(
            scope == "." or path == scope or path.startswith(scope.rstrip("/") + "/") for scope in self.task.allowed_read_scopes
        )

    def _failure(self, raw_hash: str, outcome: str, detail: str) -> HarnessStep:
        record = RequestRecord(self.task.interaction_id, self._turn, raw_hash, None, None, outcome, "NOT_EXECUTED", None,
                               {"status": "ERROR", "error": outcome}, outcome)
        return HarnessStep(record, record.projection)

    def _record(self, request: ModelRequest, validation: str, authority: str, operation: str | None, projection: dict[str, Any], terminal: str | None) -> HarnessStep:
        record = RequestRecord(self.task.interaction_id, self._turn, request.raw_sha256, request.request_type.value, request.arguments,
                               validation, authority, operation, projection, terminal)
        return HarnessStep(record, projection)


def parse_request(raw_response: str) -> ModelRequest:
    if not isinstance(raw_response, str) or len(raw_response.encode("utf-8")) > MAX_RAW_RESPONSE_BYTES:
        raise RequestParseError("response is not a bounded UTF-8 string")
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as error:
        raise RequestParseError("response must be one JSON object") from error
    if not isinstance(payload, dict) or set(payload) != {"request_type", "arguments"}:
        raise RequestParseError("response requires only request_type and arguments")
    try:
        request_type = RequestType(payload["request_type"])
    except (TypeError, ValueError) as error:
        raise RequestParseError("unsupported request type") from error
    arguments = payload["arguments"]
    if not isinstance(arguments, dict):
        raise RequestParseError("arguments must be an object")
    _validate_arguments(request_type, arguments)
    return ModelRequest(request_type, arguments, hashlib.sha256(raw_response.encode("utf-8")).hexdigest())


def _validate_arguments(request_type: RequestType, arguments: dict[str, Any]) -> None:
    required: dict[RequestType, set[str]] = {
        RequestType.READ: {"path"}, RequestType.SEARCH: {"literal", "scope"},
        RequestType.PROPOSE_PATCH: {"patch", "proposed_paths"}, RequestType.REQUEST_CLARIFICATION: {"question"},
        RequestType.NO_CHANGE: set(), RequestType.STOP_STATE_STALE: set(),
        RequestType.REQUEST_COMMIT: set(), RequestType.REQUEST_PUSH: set(), RequestType.REQUEST_WRITE: set(),
        RequestType.REQUEST_NETWORK: set(), RequestType.REQUEST_DEPENDENCY: set(),
    }
    if set(arguments) != required[request_type]:
        raise RequestParseError("unexpected or missing arguments")
    if request_type is RequestType.READ and (not isinstance(arguments["path"], str) or len(arguments["path"]) > 512):
        raise RequestParseError("invalid read path")
    if request_type is RequestType.SEARCH and (not isinstance(arguments["literal"], str) or not arguments["literal"] or len(arguments["literal"]) > 256 or not isinstance(arguments["scope"], str) or len(arguments["scope"]) > 512):
        raise RequestParseError("invalid search request")
    if request_type is RequestType.PROPOSE_PATCH:
        if not isinstance(arguments["patch"], str) or len(arguments["patch"].encode("utf-8")) > MAX_PATCH_BYTES:
            raise RequestParseError("invalid patch size")
        paths = arguments["proposed_paths"]
        if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_PATHS or any(not isinstance(path, str) or len(path) > 512 for path in paths):
            raise RequestParseError("invalid proposed paths")
    if request_type is RequestType.REQUEST_CLARIFICATION and (not isinstance(arguments["question"], str) or not arguments["question"] or len(arguments["question"]) > MAX_CLARIFICATION_CHARS):
        raise RequestParseError("invalid clarification question")
