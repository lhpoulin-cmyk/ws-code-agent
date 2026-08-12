#!/usr/bin/env python3
"""Calibrate the Task 11N real-code validators under fixed containment."""

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
    TASK11N_VALIDATION_IDS,
    bind_validation_ids,
    validation_registry,
)
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationStatus  # noqa: E402


SOURCE = Path("/home/louis/src/ws-doc-writer/src/docwriter_web/writing_setup.py")
SOURCE_SHA256 = "f6031119600919e4004c57c6229b7bd911f6befb9e67af04ce719da99f444a6f"
START = b"def from_form("
END = b"def from_row("
GOOD_FUNCTION = b'''def from_form(form: dict[str, str]) -> WritingSetup:\n    custom_policy = _clean("clarification_policy", form.get("clarification_policy_custom"))\n    policy = custom_policy or form.get("clarification_policy")\n    values = {field: _clean(field, form.get(field)) for field in FIELDS if field != "clarification_policy"}\n    values["clarification_policy"] = _clean("clarification_policy", policy)\n    provenance = {field: PROVENANCE_OPERATOR for field, value in values.items() if value}\n    # Saving values is not confirmation. A separate authenticated action\n    # creates the COMPLETE immutable version.\n    return WritingSetup(**values, completion_state="DRAFT", field_provenance=provenance)\n\n\n'''
PARTIAL_FUNCTION = b'''def from_form(form: dict[str, str]) -> WritingSetup:\n    policy = form.get("clarification_policy_custom") or form.get("clarification_policy")\n    values = {field: _clean(field, form.get(field)) for field in FIELDS if field != "clarification_policy"}\n    values["clarification_policy"] = _clean("clarification_policy", policy)\n    provenance = {field: PROVENANCE_OPERATOR for field, value in values.items() if value}\n    # Saving values is not confirmation. A separate authenticated action\n    # creates the COMPLETE immutable version.\n    return WritingSetup(**values, completion_state="DRAFT", field_provenance=provenance)\n\n\n'''


def git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def replace_function(source: bytes, function: bytes) -> bytes:
    start = source.index(START)
    end = source.index(END)
    return source[:start] + function + source[end:]


def source_cases() -> dict[str, tuple[bytes, bool, ValidationStatus]]:
    source = SOURCE.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise RuntimeError("frozen Task 11N source is unavailable")
    good = replace_function(source, GOOD_FUNCTION)
    partial = replace_function(source, PARTIAL_FUNCTION)
    wrong = source.replace(
        b'policy = form.get("clarification_policy") or form.get("clarification_policy_custom")',
        b'policy = form.get("clarification_policy")',
        1,
    )
    unrelated = good.replace(b'"tone": 400,', b'"tone": 401,', 1)
    return {
        "known_good_behavior": (good, False, ValidationStatus.VALIDATION_PASS),
        "original_defect": (source, False, ValidationStatus.VALIDATION_FAIL),
        "wrong_value": (wrong, False, ValidationStatus.VALIDATION_FAIL),
        "partial_raw_precedence": (partial, False, ValidationStatus.VALIDATION_FAIL),
        "unrelated_code_change": (unrelated, False, ValidationStatus.VALIDATION_FAIL),
        "second_changed_path": (good, True, ValidationStatus.VALIDATION_FAIL),
    }


def run_case(
    name: str,
    candidate: bytes,
    second_change: bool,
    expected: ValidationStatus,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(
        prefix="ws-code-agent-isolated-task11n-calibration-"
    ) as temporary:
        repository = Path(temporary)
        target = repository / "src/docwriter_web/writing_setup.py"
        target.parent.mkdir(parents=True)
        target.write_text(
            '"""Calibration source that does not satisfy Task 11N."""\n',
            encoding="utf-8",
        )
        (repository / "README.md").write_text("# Calibration\n", encoding="utf-8")
        git(repository, "init", "-q")
        git(repository, "add", ".")
        git(
            repository,
            "-c", "user.name=Task11N",
            "-c", "user.email=task11n@example.invalid",
            "commit", "-qm", "calibration source",
        )
        observer = ReadOnlyExecutor()
        initial = observer.observe_repository(repository).snapshot
        target.write_bytes(candidate)
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
                operation="TASK11N_VALIDATOR_CALIBRATION",
                success=True,
                snapshot_identity=initial.snapshot_identity,
                observed_result={"case": name},
            ),
        )
        executor = DescriptorValidationExecutor(
            validation_registry(), observer, SystemdContainedValidationRunner()
        )
        runs = [
            executor.run_validation(context, result, descriptor, TASK11N_VALIDATION_IDS)
            for descriptor in TASK11N_VALIDATION_IDS
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
    contract = bind_validation_ids(TASK11N_VALIDATION_IDS)
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
        "behavioral_diversity": "PASS",
        "containment_required": True,
        "model_inference_count": 0,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
