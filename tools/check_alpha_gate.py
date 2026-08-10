"""Run the compact Alpha pre-push gate, including invariant-register sanity."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs/executor/adversarial-invariant-register.md"
ROWS = ("P3", "P5", "P6", "S2", "S3", "S4", "V1", "V2", "V6", "T1", "T4", "X3", "X4", "M3", "M4", "R1", "E6", "E7", "G3")


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    text = REGISTER.read_text(encoding="utf-8")
    if "| MISSING |" in text or any(f"| {row} |" not in text for row in ROWS):
        raise SystemExit("Alpha invariant register is incomplete")
    if "| G3 | PARTIAL | 2026-08-10:" not in text:
        raise SystemExit("G3 triage is incomplete")
    run(sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v")
    run(sys.executable, "-B", "-m", "unittest", "tests.test_private_calibration_material", "-v")
    run(sys.executable, "tools/verify_lineage.py")
    run("git", "diff", "--check")
    print("PASS alpha_invariant_register")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
