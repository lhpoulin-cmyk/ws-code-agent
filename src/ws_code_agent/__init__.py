"""Bounded, read-only repository observation for ws-code-agent."""

from .readonly_executor import (
    CompareResult,
    CompareStatus,
    ExecutorFact,
    ObservationResult,
    ReadOnlyExecutor,
    RepositorySnapshot,
    SearchMatch,
)

__all__ = [
    "CompareResult",
    "CompareStatus",
    "ExecutorFact",
    "ObservationResult",
    "ReadOnlyExecutor",
    "RepositorySnapshot",
    "SearchMatch",
]
