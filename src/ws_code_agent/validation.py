"""Trusted descriptor-only validation inside existing isolated workspaces."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path, PurePath
import shutil
import subprocess
import time
from typing import Mapping
from .isolated_patch import IsolatedContext
from .readonly_executor import ExecutorFact, RepositorySnapshot, ReadOnlyExecutor

class ValidationRole(str, Enum):
    VISIBLE = "VISIBLE"
    HIDDEN_ORACLE = "HIDDEN_ORACLE"

class ValidationStatus(str, Enum):
    VALIDATION_PASS = "VALIDATION_PASS"
    VALIDATION_FAIL = "VALIDATION_FAIL"
    VALIDATION_UNAVAILABLE = "VALIDATION_UNAVAILABLE"
    VALIDATION_TIMEOUT = "VALIDATION_TIMEOUT"
    EFFECT_VIOLATION = "EFFECT_VIOLATION"
    EXECUTOR_ERROR = "EXECUTOR_ERROR"

@dataclass(frozen=True)
class ValidationDescriptor:
    descriptor_id: str
    version: str
    executable: str
    arguments: tuple[str, ...]
    working_directory: str
    timeout_seconds: float
    role: ValidationRole
    model_visible_by_id_only: bool
    repository_writes_allowed: bool = False
    requires_post_patch: bool = True
    isolated_pythonpath: bool = False
    def __post_init__(self) -> None:
        if not self.descriptor_id or not self.version or not self.executable or self.timeout_seconds <= 0:
            raise ValueError("descriptor identity, executable, and positive timeout are required")
        if PurePath(self.working_directory).is_absolute() or ".." in PurePath(self.working_directory).parts:
            raise ValueError("working directory must be repository-relative")
        if any(any(token in arg for token in ("|", ";", "&&", "||", "`", "$(", ">", "<")) for arg in self.arguments):
            raise ValueError("shell syntax is not permitted")

@dataclass(frozen=True)
class ValidationRun:
    descriptor_id: str; role: ValidationRole; result_before: RepositorySnapshot; result_after: RepositorySnapshot
    executable_identity: str; argv: tuple[str, ...]; working_directory: str; started_monotonic_ns: int; ended_monotonic_ns: int
    exit_code: int | None; timed_out: bool; stdout: str; stderr: str; status: ValidationStatus; fact: ExecutorFact

class DescriptorValidationExecutor:
    """No generic command operation; lookup occurs only in this trusted registry."""
    def __init__(self, descriptors: Mapping[str, ValidationDescriptor], observer: ReadOnlyExecutor | None = None) -> None:
        if set(descriptors) != {value.descriptor_id for value in descriptors.values()}:
            raise ValueError("registry keys must equal descriptor IDs")
        self._descriptors, self._observer = dict(descriptors), observer or ReadOnlyExecutor()
    def run_validation(self, context: IsolatedContext, result_snapshot: RepositorySnapshot, validation_id: str, authorized_ids: tuple[str, ...]) -> ValidationRun:
        descriptor = self._descriptors.get(validation_id)
        before = self._observer.observe_repository(context.isolated_root).snapshot
        if descriptor is None or validation_id not in authorized_ids:
            return self._error(context, before, validation_id, ValidationStatus.EXECUTOR_ERROR, "descriptor unknown or unauthorized")
        if before.snapshot_identity != result_snapshot.snapshot_identity or (descriptor.requires_post_patch and before.snapshot_identity == context.initial_snapshot.snapshot_identity):
            return self._error(context, before, validation_id, ValidationStatus.EXECUTOR_ERROR, "result snapshot is not the required post-patch state")
        try:
            cwd = self._cwd(context, descriptor); executable = self._executable(descriptor.executable)
        except (OSError, ValueError) as error:
            return self._error(context, before, validation_id, ValidationStatus.VALIDATION_UNAVAILABLE, str(error))
        env = {"PATH": os.defpath, "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}
        if descriptor.isolated_pythonpath: env["PYTHONPATH"] = context.isolated_root
        argv, started = (executable, *descriptor.arguments), time.monotonic_ns()
        try:
            process = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=descriptor.timeout_seconds, check=False)
            stdout, stderr, code, timed_out = process.stdout, process.stderr, process.returncode, False
        except subprocess.TimeoutExpired as error:
            stdout, stderr, code, timed_out = error.stdout or b"", error.stderr or b"", None, True
        except OSError as error:
            return self._error(context, before, validation_id, ValidationStatus.VALIDATION_UNAVAILABLE, str(error), started)
        ended, after = time.monotonic_ns(), self._observer.observe_repository(context.isolated_root).snapshot
        if timed_out: status = ValidationStatus.VALIDATION_TIMEOUT
        elif before.snapshot_identity != after.snapshot_identity and not descriptor.repository_writes_allowed: status = ValidationStatus.EFFECT_VIOLATION
        elif code == 0: status = ValidationStatus.VALIDATION_PASS
        else: status = ValidationStatus.VALIDATION_FAIL
        out, err = stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
        fact = ExecutorFact(operation="RUN_VALIDATION", success=status is ValidationStatus.VALIDATION_PASS, snapshot_identity=before.snapshot_identity, error_classification=None if status is ValidationStatus.VALIDATION_PASS else status.value, observed_result={"descriptor_id": validation_id, "argv": argv, "working_directory": str(cwd), "exit_code": code, "timed_out": timed_out, "stdout": out, "stderr": err, "result_before": before.snapshot_identity, "result_after": after.snapshot_identity})
        return ValidationRun(validation_id, descriptor.role, before, after, executable, argv, str(cwd), started, ended, code, timed_out, out, err, status, fact)
    def _error(self, context, snapshot, validation_id, status, detail, started=None):
        now = time.monotonic_ns()
        return ValidationRun(validation_id, ValidationRole.VISIBLE, snapshot, snapshot, "", (), "", started or now, now, None, False, "", detail, status, ExecutorFact(operation="RUN_VALIDATION", success=False, snapshot_identity=snapshot.snapshot_identity, error_classification=status.value, observed_result={"descriptor_id": validation_id, "detail": detail}))
    @staticmethod
    def _executable(value: str) -> str:
        path = Path(value) if os.path.isabs(value) else Path(shutil.which(value, path=os.defpath) or "")
        if not path.is_file() or not os.access(path, os.X_OK): raise OSError("trusted executable unavailable")
        return str(path.resolve())
    @staticmethod
    def _cwd(context: IsolatedContext, descriptor: ValidationDescriptor) -> Path:
        root = Path(context.isolated_root).resolve(); candidate = (root / descriptor.working_directory).resolve(strict=True)
        try: candidate.relative_to(root)
        except ValueError as error: raise ValueError("working directory escapes isolated root") from error
        if not candidate.is_dir() or candidate.is_symlink(): raise ValueError("unsafe working directory")
        return candidate
