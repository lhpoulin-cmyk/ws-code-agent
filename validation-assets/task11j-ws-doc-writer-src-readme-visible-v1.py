"""Visible Task 11J ws-doc-writer src/README.md contract validator."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


EXPECTED = (
    "# Application boundary\n\n"
    "The `src/docwriter_web` package contains the Doc Writer application\n"
    "implementation. It must not execute infrastructure commands.\n"
).encode("utf-8")


def fail(message: str) -> None:
    print(f"VISIBLE_VALIDATION_FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


target = Path("src/README.md")
if not target.is_file() or target.is_symlink():
    fail("src/README.md is unavailable")
try:
    content = target.read_bytes()
    content.decode("utf-8")
except (OSError, UnicodeDecodeError):
    fail("src/README.md is not valid UTF-8")
if content != EXPECTED:
    fail("src/README.md does not equal the approved replacement")

process = subprocess.run(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
if process.returncode != 0 or process.stdout != b" M src/README.md\n":
    fail("src/README.md is not the sole changed path")

print("VISIBLE_VALIDATION_PASS")
