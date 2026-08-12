#!/usr/bin/env python3
"""Calibrate Task 11A's pre-bound validators under production containment."""

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
from ws_code_agent.supervised_validation import WRITE_VALIDATION_IDS, bind_validation_ids, validation_registry  # noqa: E402
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationStatus  # noqa: E402


GOOD = {
    "multiline": 'def message():\n    return "hello"\n',
    "one_line": 'def message(): return "hello"\n',
    "annotated_docstring": 'def message() -> str:\n    """Greeting."""\n    return "hello"\n',
}
BAD = {
    "initial_hi": 'def message():\n    return "hi"\n',
    "syntax_error": 'def message(:\n',
    "missing_message": 'def other(): return "hello"\n',
    "requires_argument": 'def message(value): return "hello"\n',
    "wrong_case": 'def message(): return "Hello"\n',
    "none": 'def message(): return None\n',
}


def git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_case(name: str, source: str, expected: ValidationStatus) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ws-code-agent-isolated-task11a-calibration-") as temporary:
        workspace = Path(temporary)
        repository = workspace / "repository"
        (repository / "src").mkdir(parents=True)
        target = repository / "src/message.py"
        target.write_text('def message():\n    return "fixture-before"\n', encoding="utf-8")
        git(repository, "init", "-q")
        git(repository, "add", "src/message.py")
        git(
            repository,
            "-c", "user.name=Task11A",
            "-c", "user.email=task11a@example.invalid",
            "commit", "-qm", "calibration source",
        )
        observer = ReadOnlyExecutor()
        initial = observer.observe_repository(repository).snapshot
        target.write_text(source, encoding="utf-8")
        result = observer.observe_repository(repository).snapshot
        context = IsolatedContext(
            source_snapshot=initial,
            workspace_root=str(workspace),
            isolated_root=str(repository),
            initial_snapshot=initial,
            initial_manifest={},
            build_fact=ExecutorFact(
                operation="TASK11A_VALIDATOR_CALIBRATION",
                success=True,
                snapshot_identity=initial.snapshot_identity,
                observed_result={"case": name},
            ),
        )
        executor = DescriptorValidationExecutor(
            validation_registry(), observer, SystemdContainedValidationRunner()
        )
        runs = [
            executor.run_validation(context, result, descriptor, WRITE_VALIDATION_IDS)
            for descriptor in WRITE_VALIDATION_IDS
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
    contract = bind_validation_ids(WRITE_VALIDATION_IDS)
    if contract["descriptors"][0]["source_sha256"] == contract["descriptors"][1]["source_sha256"]:
        raise RuntimeError("visible and hidden implementations are not independent")
    cases = [
        *(run_case(name, source, ValidationStatus.VALIDATION_PASS) for name, source in GOOD.items()),
        *(run_case(name, source, ValidationStatus.VALIDATION_FAIL) for name, source in BAD.items()),
    ]
    result = {
        "validation_contract": contract,
        "known_good": len(GOOD),
        "known_bad": len(BAD),
        "cases": cases,
        "candidate_specific_overfit_check": "PASS",
        "containment_required": True,
        "model_inference_count": 0,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
