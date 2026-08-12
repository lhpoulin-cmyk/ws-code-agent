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
from .isolated_patch import ApplicationStatus, IsolatedPatchExecutor, PatchProposal
from .validation import DescriptorValidationExecutor, ValidationDescriptor, ValidationRole, ValidationStatus
from .structured_edit import (
    StructuredTextReplacement,
    StructuredTextReplacementExecutor,
    StructuredTextReplacementResult,
    TextReplacementStatus,
)

__all__ = [
    "CompareResult",
    "CompareStatus",
    "ExecutorFact",
    "ObservationResult",
    "ReadOnlyExecutor",
    "RepositorySnapshot",
    "SearchMatch",
    "ApplicationStatus",
    "IsolatedPatchExecutor",
    "PatchProposal",
    "DescriptorValidationExecutor",
    "ValidationDescriptor",
    "ValidationRole",
    "ValidationStatus",
    "StructuredTextReplacement",
    "StructuredTextReplacementExecutor",
    "StructuredTextReplacementResult",
    "TextReplacementStatus",
]
