"""Evaluator-only independent Task 11J ws-doc-writer README oracle."""

from __future__ import annotations

from pathlib import Path
import subprocess


target = Path("src/README.md")
try:
    text = target.read_text(encoding="utf-8", errors="strict")
except (OSError, UnicodeError):
    raise SystemExit(1)

lines = text.splitlines()
if lines.count("# Application boundary") != 1:
    raise SystemExit(1)
if "Implementation is intentionally absent in the foundation phase." in text:
    raise SystemExit(1)
if "Future code" in text:
    raise SystemExit(1)
if text.count("src/docwriter_web") != 1:
    raise SystemExit(1)
if text.count("It must not execute infrastructure commands.") != 1:
    raise SystemExit(1)
expected_lines = [
    "# Application boundary",
    "",
    "The `src/docwriter_web` package contains the Doc Writer application",
    "implementation. It must not execute infrastructure commands.",
]
if lines != expected_lines or not text.endswith("\n"):
    raise SystemExit(1)

process = subprocess.run(
    ["git", "diff", "--name-only", "HEAD", "--"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
if process.returncode != 0 or process.stdout.splitlines() != [b"src/README.md"]:
    raise SystemExit(1)
untracked = subprocess.run(
    ["git", "ls-files", "--others", "--exclude-standard"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
if untracked.returncode != 0 or untracked.stdout:
    raise SystemExit(1)

print("HIDDEN_VALIDATION_PASS")
