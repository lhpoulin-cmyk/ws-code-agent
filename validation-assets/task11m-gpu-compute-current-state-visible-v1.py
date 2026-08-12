"""Visible Task 11M gpu-compute CURRENT_STATE.md contract validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys


EXPECTED_SHA256 = "962c2de28eaf28525e13a63f908e661ce7b94f45a07f43529edea6b4cdcf494e"


def fail(message: str) -> None:
    print(f"VISIBLE_VALIDATION_FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


target = Path("CURRENT_STATE.md")
if not target.is_file() or target.is_symlink():
    fail("CURRENT_STATE.md is unavailable")
try:
    content = target.read_bytes()
    content.decode("utf-8", errors="strict")
except (OSError, UnicodeDecodeError):
    fail("CURRENT_STATE.md is not valid UTF-8")
if hashlib.sha256(content).hexdigest() != EXPECTED_SHA256:
    fail("CURRENT_STATE.md does not equal the approved one-line correction")

process = subprocess.run(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
if process.returncode != 0 or process.stdout != b" M CURRENT_STATE.md\n":
    fail("CURRENT_STATE.md is not the sole changed path")

print("VISIBLE_VALIDATION_PASS")
