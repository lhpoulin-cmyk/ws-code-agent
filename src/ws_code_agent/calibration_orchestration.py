"""Deterministic, bounded orchestration for Alpha C03--C05 fixtures.

This module does not add a general repository or command interface.  Each
declared repository is bound to an observed snapshot and a fixed capability
scope before an interaction begins.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePath
from typing import Any, Mapping

from .executor_feedback import bounded_executor_feedback
from .isolated_patch import ApplicationStatus, IsolatedContext, IsolatedPatchExecutor, PatchApplicationResult, PatchProposal
from .readonly_executor import ExecutorOperationError, ReadOnlyExecutor, RepositorySnapshot
from .request_protocol import MULTI_REPOSITORY_PROTOCOL


MAX_RAW_RESPONSE_BYTES = 32_768
MAX_PATCH_BYTES = 16_384
MAX_PATHS = 8
MAX_SEARCH_RESULTS = 20

@dataclass(frozen=True)
class DeclaredRepository:
    """One immutable task-scoped repository capability, never a peer grant."""

    alias: str
    snapshot: RepositorySnapshot
    allowed_read_scopes: tuple[str, ...]
    allowed_patch_paths: tuple[str, ...]
    change_required: bool = True

    def __post_init__(self) -> None:
        if not self.alias or not self.allowed_read_scopes:
            raise ValueError("repository alias and read scope are required")


@dataclass(frozen=True)
class MultiRepositoryTask:
    """A small task-version representation for declared C05 fixture repositories."""

    task_version: str
    repositories: tuple[DeclaredRepository, ...]

    def __post_init__(self) -> None:
        aliases = [repository.alias for repository in self.repositories]
        if not self.task_version or not aliases or len(aliases) != len(set(aliases)):
            raise ValueError("task version and unique declared repositories are required")

    def repository(self, alias: str) -> DeclaredRepository | None:
        return next((repository for repository in self.repositories if repository.alias == alias), None)


@dataclass(frozen=True)
class MultiRepositoryStep:
    request_type: str
    repository_alias: str | None
    authority_outcome: str
    executor_operation: str | None
    projection: Mapping[str, Any]
    application: PatchApplicationResult | None = None


class MultiRepositoryDispositionHarness:
    """C05-only bounded dispatcher; selectors are aliases from one task version."""

    def __init__(self, task: MultiRepositoryTask, observer: ReadOnlyExecutor | None = None, patcher: IsolatedPatchExecutor | None = None) -> None:
        self.task = task
        self._observer = observer or ReadOnlyExecutor()
        self._patcher = patcher or IsolatedPatchExecutor(self._observer)
        self._contexts: dict[str, IsolatedContext] = {}

    def close(self) -> None:
        for context in self._contexts.values():
            self._patcher.cleanup(context)
        self._contexts.clear()

    def step(self, raw_response: str) -> MultiRepositoryStep:
        request_type, arguments = _parse_multi_repository_request(raw_response)
        if request_type == "NO_CHANGE":
            return MultiRepositoryStep(request_type, None, "NO_EXECUTOR_ACTION", None, {"status": "RECORDED"})
        alias = arguments["repository"]
        repository = self.task.repository(alias)
        if repository is None:
            return MultiRepositoryStep(request_type, alias, "REPOSITORY_DENIED", None, {
                "status": "DENIED", "error": "REPOSITORY_DENIED", "repository": alias,
            })
        if request_type == "READ":
            return self._read(repository, arguments["path"])
        if request_type == "SEARCH":
            return self._search(repository, arguments["literal"], arguments["scope"])
        return self._propose_patch(repository, arguments["patch"], tuple(arguments["proposed_paths"]))

    def aggregate_status(self, steps: tuple[MultiRepositoryStep, ...]) -> str:
        """Completion is bound to required effects, not mere repository declaration."""
        accepted = {
            step.repository_alias for step in steps
            if step.application is not None and step.application.status is ApplicationStatus.SUCCESS
        }
        required = {repository.alias for repository in self.task.repositories if repository.change_required}
        return "COMPLETE" if required <= accepted else "INCOMPLETE"

    def _read(self, repository: DeclaredRepository, path: str) -> MultiRepositoryStep:
        if not _in_scope(path, repository.allowed_read_scopes):
            return self._denied("READ", repository, "PATH_SCOPE_DENIED")
        try:
            result = self._observer.read_file(repository.snapshot, path)
        except ExecutorOperationError as error:
            status = error.fact.error_classification or "EXECUTOR_ERROR"
            return MultiRepositoryStep("READ", repository.alias, status, "READ_FILE", {
                "status": "STALE" if status == "STATE_STALE" else "ERROR",
                "error": status,
                **_repository_projection(repository),
            })
        return MultiRepositoryStep("READ", repository.alias, "AUTHORIZED", "READ_FILE", {
            "status": "OK", "path": path,
            "content": result.content.decode("utf-8", errors="replace"),
            **_repository_projection(repository),
        })

    def _propose_patch(self, repository: DeclaredRepository, patch: str, proposed_paths: tuple[str, ...]) -> MultiRepositoryStep:
        if not repository.allowed_patch_paths:
            return self._denied("PROPOSE_PATCH", repository, "PATCH_NOT_AUTHORIZED")
        if not set(proposed_paths) <= set(repository.allowed_patch_paths):
            return self._denied("PROPOSE_PATCH", repository, "PATH_SCOPE_DENIED")
        try:
            context = self._contexts.get(repository.alias)
            if context is None:
                context = self._patcher.build_isolated_copy(repository.snapshot)
                self._contexts[repository.alias] = context
            proposal = PatchProposal.create(repository.snapshot, patch.encode("utf-8"), proposed_paths)
            result = self._patcher.apply_patch_isolated(context, proposal, repository.allowed_patch_paths)
        except ExecutorOperationError as error:
            status = error.fact.error_classification or "EXECUTOR_ERROR"
            return MultiRepositoryStep("PROPOSE_PATCH", repository.alias, status, "APPLY_PATCH_ISOLATED", {
                "status": "REJECTED", "application": status, "changed_paths": [],
                "executor_feedback": bounded_executor_feedback(status, error.fact.observed_result, _roots(repository, self._contexts.get(repository.alias))),
                **_repository_projection(repository),
            })
        status = "ACCEPTED" if result.status is ApplicationStatus.SUCCESS else "REJECTED"
        projection: dict[str, Any] = {
            "status": status, "application": result.status.value,
            "changed_paths": list(result.actual_changed_paths), **_repository_projection(repository),
        }
        if result.status is not ApplicationStatus.SUCCESS:
            projection["executor_feedback"] = bounded_executor_feedback(
                result.status.value, result.fact.observed_result, _roots(repository, self._contexts.get(repository.alias))
            )
        return MultiRepositoryStep("PROPOSE_PATCH", repository.alias, result.status.value, "APPLY_PATCH_ISOLATED", projection, result)

    def _search(self, repository: DeclaredRepository, literal: str, scope: str) -> MultiRepositoryStep:
        if not _in_scope(scope, repository.allowed_read_scopes):
            return self._denied("SEARCH", repository, "PATH_SCOPE_DENIED")
        try:
            result = self._observer.search(repository.snapshot, literal, scope=scope, result_limit=MAX_SEARCH_RESULTS)
        except ExecutorOperationError as error:
            status = error.fact.error_classification or "EXECUTOR_ERROR"
            return MultiRepositoryStep("SEARCH", repository.alias, status, "SEARCH", {
                "status": "STALE" if status == "STATE_STALE" else "ERROR",
                "error": status,
                **_repository_projection(repository),
            })
        return MultiRepositoryStep("SEARCH", repository.alias, "AUTHORIZED", "SEARCH", {
            "status": "OK",
            "matches": [
                {"path": item.relative_path, "line": item.line_number, "text": item.line_text}
                for item in result.matches
            ],
            **_repository_projection(repository),
        })

    @staticmethod
    def _denied(request_type: str, repository: DeclaredRepository, classification: str) -> MultiRepositoryStep:
        projection: dict[str, Any] = {
            "status": "DENIED", "error": classification, **_repository_projection(repository),
        }
        if request_type == "PROPOSE_PATCH":
            projection["authority_feedback"] = {
                "origin": "executor",
                "classification": classification,
                "task_authority": {
                    "repository": repository.alias,
                    "patch_paths": list(repository.allowed_patch_paths),
                    "scope": "repository-local; non-transitive",
                },
            }
        return MultiRepositoryStep(request_type, repository.alias, classification, None, projection)


def _parse_multi_repository_request(raw_response: str) -> tuple[str, dict[str, Any]]:
    if not isinstance(raw_response, str) or len(raw_response.encode("utf-8")) > MAX_RAW_RESPONSE_BYTES:
        raise ValueError("response is not a bounded UTF-8 string")
    try:
        payload = json.loads(raw_response)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("response must be one JSON object") from error
    if not isinstance(payload, dict) or set(payload) != {"request_type", "arguments"}:
        raise ValueError("response requires only request_type and arguments")
    request_type, arguments = payload["request_type"], payload["arguments"]
    contract = MULTI_REPOSITORY_PROTOCOL.request(request_type) if isinstance(request_type, str) else None
    if contract is None or not isinstance(arguments, dict) or set(arguments) != set(contract.argument_names):
        raise ValueError("unsupported multi-repository request")
    if request_type != "NO_CHANGE" and (not isinstance(arguments["repository"], str) or not arguments["repository"]):
        raise ValueError("repository selector must be a declared alias")
    if request_type == "READ" and (not isinstance(arguments["path"], str) or len(arguments["path"]) > 512):
        raise ValueError("invalid read path")
    if request_type == "SEARCH" and (
        not isinstance(arguments["literal"], str) or not arguments["literal"] or len(arguments["literal"]) > 256
        or not isinstance(arguments["scope"], str) or len(arguments["scope"]) > 512
    ):
        raise ValueError("invalid search request")
    if request_type == "PROPOSE_PATCH":
        if (
            not isinstance(arguments["patch"], str) or len(arguments["patch"].encode("utf-8")) > MAX_PATCH_BYTES
            or not isinstance(arguments["proposed_paths"], list) or not 1 <= len(arguments["proposed_paths"]) <= MAX_PATHS
        ):
            raise ValueError("invalid patch proposal")
        if any(not isinstance(path, str) or len(path) > 512 for path in arguments["proposed_paths"]):
            raise ValueError("invalid proposed path")
    return request_type, arguments


def _in_scope(path: str, scopes: tuple[str, ...]) -> bool:
    value = PurePath(path)
    return not value.is_absolute() and ".." not in value.parts and any(
        scope == "." or path == scope or path.startswith(scope.rstrip("/") + "/") for scope in scopes
    )


def _repository_projection(repository: DeclaredRepository) -> dict[str, str]:
    return {
        "repository": repository.alias,
        "repository_identity": repository.snapshot.repository_identity,
        "snapshot_identity": repository.snapshot.snapshot_identity,
    }


def _roots(repository: DeclaredRepository, context: IsolatedContext | None) -> tuple[str, ...]:
    return (repository.snapshot.canonical_root, *( (context.isolated_root,) if context is not None else () ))
