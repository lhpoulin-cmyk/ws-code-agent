#!/usr/bin/env python3
"""Calibrate the Task 11J real-repository validators under containment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.contained_validation import SystemdContainedValidationRunner  # noqa: E402
from ws_code_agent.isolated_patch import IsolatedContext  # noqa: E402
from ws_code_agent.readonly_executor import ExecutorFact, ReadOnlyExecutor  # noqa: E402
from ws_code_agent.supervised_validation import (  # noqa: E402
    TASK11J_VALIDATION_IDS,
    bind_validation_ids,
    validation_registry,
)
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationStatus  # noqa: E402


ORIGINAL = (
    "# Application boundary\n\n"
    "Implementation is intentionally absent in the foundation phase. Future code\n"
    "may normalize sources, invoke approved model adapters, validate candidates, and\n"
    "export accepted documents. It must not execute infrastructure commands.\n"
)
CALIBRATION_BASE = "# Application boundary\n\nCalibration source.\n"
EXPECTED = (
    "# Application boundary\n\n"
    "The `src/docwriter_web` package contains the Doc Writer application\n"
    "implementation. It must not execute infrastructure commands.\n"
)
CASES = {
    "exact_intended_replacement": (EXPECTED, False, ValidationStatus.VALIDATION_PASS),
    "original_stale_source": (ORIGINAL, False, ValidationStatus.VALIDATION_FAIL),
    "missing_infrastructure_prohibition": (
        "# Application boundary\n\nThe `src/docwriter_web` package contains the Doc Writer application implementation.\n",
        False,
        ValidationStatus.VALIDATION_FAIL,
    ),
    "wrong_package": (
        "# Application boundary\n\nThe `src/doc_writer` package contains the Doc Writer application\nimplementation. It must not execute infrastructure commands.\n",
        False,
        ValidationStatus.VALIDATION_FAIL,
    ),
    "unrelated_wording": (EXPECTED + "\nAdditional cleanup.\n", False, ValidationStatus.VALIDATION_FAIL),
    "heading_modified": (EXPECTED.replace("# Application boundary", "# Application"), False, ValidationStatus.VALIDATION_FAIL),
    "partial_stale_paragraph": (EXPECTED + "Future code may be added later.\n", False, ValidationStatus.VALIDATION_FAIL),
    "second_changed_file": (EXPECTED, True, ValidationStatus.VALIDATION_FAIL),
}


def git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_case(name: str, source: str, second_change: bool, expected: ValidationStatus) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ws-code-agent-isolated-task11j-calibration-") as temporary:
        repository = Path(temporary)
        (repository / "src").mkdir()
        (repository / "src/README.md").write_text(CALIBRATION_BASE, encoding="utf-8")
        (repository / "README.md").write_text("# Doc Writer\n", encoding="utf-8")
        git(repository, "init", "-q")
        git(repository, "add", "src/README.md", "README.md")
        git(repository, "-c", "user.name=Task11J", "-c", "user.email=task11j@example.invalid", "commit", "-qm", "calibration source")
        observer = ReadOnlyExecutor()
        initial = observer.observe_repository(repository).snapshot
        (repository / "src/README.md").write_text(source, encoding="utf-8")
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
                operation="TASK11J_VALIDATOR_CALIBRATION",
                success=True,
                snapshot_identity=initial.snapshot_identity,
                observed_result={"case": name},
            ),
        )
        executor = DescriptorValidationExecutor(
            validation_registry(), observer, SystemdContainedValidationRunner()
        )
        runs = [
            executor.run_validation(context, result, descriptor, TASK11J_VALIDATION_IDS)
            for descriptor in TASK11J_VALIDATION_IDS
        ]
        if any(run.status is not expected for run in runs):
            raise RuntimeError(
                f"{name}: expected {expected.value}, got {[run.status.value for run in runs]}"
            )
        if observer.observe_repository(repository).snapshot.snapshot_identity != result.snapshot_identity:
            raise RuntimeError(f"{name}: validator changed calibration repository")
        return {
            "case": name,
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
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
    contract = bind_validation_ids(TASK11J_VALIDATION_IDS)
    if contract["descriptors"][0]["source_sha256"] == contract["descriptors"][1]["source_sha256"]:
        raise RuntimeError("visible and hidden implementations are not independent")
    cases = [run_case(name, *case) for name, case in CASES.items()]
    result = {
        "validation_contract": contract,
        "cases": cases,
        "known_good": 1,
        "known_bad": len(CASES) - 1,
        "candidate_specific_overfit_check": "PASS",
        "containment_required": True,
        "model_inference_count": 0,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
