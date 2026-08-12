#!/usr/bin/env python3
"""Calibrate the Task 11M mid-file validators under fixed containment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.contained_validation import SystemdContainedValidationRunner  # noqa: E402
from ws_code_agent.isolated_patch import IsolatedContext  # noqa: E402
from ws_code_agent.readonly_executor import ExecutorFact, ReadOnlyExecutor  # noqa: E402
from ws_code_agent.supervised_validation import (  # noqa: E402
    TASK11M_VALIDATION_IDS,
    bind_validation_ids,
    validation_registry,
)
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationStatus  # noqa: E402


SOURCE = Path("/home/louis/helix-arpa/gpu-compute/CURRENT_STATE.md")
SOURCE_SHA256 = "5a06e84ce48c47bda4503e4b49b1eaf0348f2215d71455e7257f1044200d814d"
OLD = b"- Ollama `0.32.0` enabled only after CUDA smoke passed\n"
NEW = b"- Ollama `0.32.0+helix.repeatlimit.1` enabled only after CUDA smoke passed\n"


def git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def source_cases() -> dict[str, tuple[bytes, bool, ValidationStatus]]:
    source = SOURCE.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256 or source.count(OLD) != 1:
        raise RuntimeError("frozen Task 11M source is unavailable")
    prefix, suffix = source.split(OLD, 1)
    expected = prefix + NEW + suffix
    return {
        "exact_intended_edit": (expected, False, ValidationStatus.VALIDATION_PASS),
        "original_source": (source, False, ValidationStatus.VALIDATION_FAIL),
        "whole_file_replacement_only": (NEW, False, ValidationStatus.VALIDATION_FAIL),
        "lost_prefix": (NEW + suffix, False, ValidationStatus.VALIDATION_FAIL),
        "lost_suffix": (prefix + NEW, False, ValidationStatus.VALIDATION_FAIL),
        "unrelated_change": (expected + b"\nUnrelated change.\n", False, ValidationStatus.VALIDATION_FAIL),
        "incorrect_replacement": (
            prefix + NEW.replace(b"repeatlimit.1", b"repeatlimit.2") + suffix,
            False,
            ValidationStatus.VALIDATION_FAIL,
        ),
        "second_changed_file": (expected, True, ValidationStatus.VALIDATION_FAIL),
    }


def run_case(
    name: str,
    candidate: bytes,
    second_change: bool,
    expected: ValidationStatus,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(
        prefix="ws-code-agent-isolated-task11m-calibration-"
    ) as temporary:
        repository = Path(temporary)
        (repository / "CURRENT_STATE.md").write_text(
            "# Calibration source\n\nThe validator contract is not yet satisfied.\n",
            encoding="utf-8",
        )
        (repository / "README.md").write_text("# Calibration\n", encoding="utf-8")
        git(repository, "init", "-q")
        git(repository, "add", "CURRENT_STATE.md", "README.md")
        git(
            repository,
            "-c", "user.name=Task11M",
            "-c", "user.email=task11m@example.invalid",
            "commit", "-qm", "calibration source",
        )
        observer = ReadOnlyExecutor()
        initial = observer.observe_repository(repository).snapshot
        (repository / "CURRENT_STATE.md").write_bytes(candidate)
        if second_change:
            (repository / "README.md").write_text("# Changed\n", encoding="utf-8")
        result = observer.observe_repository(repository).snapshot
        context = IsolatedContext(
            source_snapshot=initial,
            workspace_root=temporary,
            isolated_root=temporary,
            initial_snapshot=initial,
            initial_manifest={},
            build_fact=ExecutorFact(
                operation="TASK11M_VALIDATOR_CALIBRATION",
                success=True,
                snapshot_identity=initial.snapshot_identity,
                observed_result={"case": name},
            ),
        )
        executor = DescriptorValidationExecutor(
            validation_registry(), observer, SystemdContainedValidationRunner()
        )
        runs = [
            executor.run_validation(context, result, descriptor, TASK11M_VALIDATION_IDS)
            for descriptor in TASK11M_VALIDATION_IDS
        ]
        if any(run.status is not expected for run in runs):
            raise RuntimeError(
                f"{name}: expected {expected.value}, got {[run.status.value for run in runs]}"
            )
        if observer.observe_repository(repository).snapshot.snapshot_identity != result.snapshot_identity:
            raise RuntimeError(f"{name}: validator changed calibration repository")
        return {
            "case": name,
            "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
            "second_changed_file": second_change,
            "expected": expected.value,
            "results": [
                {
                    "descriptor_id": run.descriptor_id,
                    "role": run.role.value,
                    "status": run.status.value,
                    "containment": dict(run.containment_evidence or {}),
                }
                for run in runs
            ],
        }


def main() -> int:
    contract = bind_validation_ids(TASK11M_VALIDATION_IDS)
    if contract["descriptors"][0]["source_sha256"] == contract["descriptors"][1]["source_sha256"]:
        raise RuntimeError("visible and hidden implementations are not separate")
    cases = [run_case(name, *case) for name, case in source_cases().items()]
    result = {
        "validation_contract": contract,
        "cases": cases,
        "known_good": 1,
        "known_bad": len(cases) - 1,
        "candidate_specific_overfit_check": "PASS",
        "validation_interpretation": "SEPARATELY_IMPLEMENTED_VALIDATION_CHECKS",
        "containment_required": True,
        "model_inference_count": 0,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
