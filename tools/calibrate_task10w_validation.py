#!/usr/bin/env python3
"""Run the Task 10W validators against candidate-independent calibration forms."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.contained_validation import SystemdContainedValidationRunner  # noqa: E402
from ws_code_agent.isolated_patch import IsolatedPatchExecutor  # noqa: E402
from ws_code_agent.readonly_executor import CompareStatus, ReadOnlyExecutor  # noqa: E402
from ws_code_agent.supervised_validation import WRITE_VALIDATION_IDS, validation_registry  # noqa: E402
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationStatus  # noqa: E402


GOOD = {
    "multiline": 'def message():\n    return "hello"\n',
    "one_line": 'def message(): return "hello"\n',
    "annotated_documented": 'def message() -> str:\n    """Return the greeting."""\n    return "hello"\n',
}
BAD = {
    "missing_file": None,
    "syntax_error": 'def message(:\n',
    "missing_message": 'def other(): return "hello"\n',
    "requires_argument": 'def message(value): return "hello"\n',
    "wrong_case": 'def message(): return "Hello"\n',
    "returns_none": 'def message(): return None\n',
}


def git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def run_case(name: str, source: str | None, expected: ValidationStatus) -> dict[str, object]:
    observer = ReadOnlyExecutor()
    patcher = IsolatedPatchExecutor(observer)
    with tempfile.TemporaryDirectory(prefix="task10w-calibration-source-") as temporary:
        repository = Path(temporary) / "repository"
        repository.mkdir()
        (repository / "README.md").write_text("# Validator calibration\n", encoding="utf-8")
        git(repository, "init", "-q")
        git(repository, "add", "README.md")
        subprocess.run(
            [
                "git", "-C", str(repository),
                "-c", "user.name=Task 10W Calibration",
                "-c", "user.email=task10w@example.invalid",
                "commit", "-qm", "calibration source",
            ],
            check=True,
        )
        source_snapshot = observer.observe_repository(repository).snapshot
        context = patcher.build_isolated_copy(source_snapshot)
        try:
            isolated = Path(context.isolated_root)
            if source is None:
                (isolated / "calibration-marker.txt").write_text(name, encoding="utf-8")
            else:
                (isolated / "src").mkdir()
                (isolated / "src/message.py").write_text(source, encoding="utf-8")
            git(isolated, "add", "-A")
            result_snapshot = observer.observe_repository(isolated).snapshot
            executor = DescriptorValidationExecutor(
                validation_registry(), observer, SystemdContainedValidationRunner()
            )
            statuses = {}
            for descriptor_id in WRITE_VALIDATION_IDS:
                run = executor.run_validation(
                    context, result_snapshot, descriptor_id, WRITE_VALIDATION_IDS
                )
                statuses[descriptor_id] = run.status.value
                if run.status is not expected:
                    raise RuntimeError(
                        f"{name}: {descriptor_id} returned {run.status.value}, expected {expected.value}"
                    )
            if observer.compare_snapshot(source_snapshot).status is not CompareStatus.MATCH:
                raise RuntimeError(f"{name}: authoritative calibration source changed")
            return {"case": name, "expected": expected.value, "results": statuses}
        finally:
            patcher.cleanup(context)


def main() -> int:
    results = [
        *(run_case(name, source, ValidationStatus.VALIDATION_PASS) for name, source in GOOD.items()),
        *(run_case(name, source, ValidationStatus.VALIDATION_FAIL) for name, source in BAD.items()),
    ]
    print(json.dumps({"status": "PASS", "cases": results}, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
