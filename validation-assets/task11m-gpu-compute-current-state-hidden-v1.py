"""Evaluator-only Task 11M gpu-compute CURRENT_STATE.md oracle."""

from __future__ import annotations

from pathlib import Path
import hashlib
import subprocess


OLD = b"- Ollama `0.32.0` enabled only after CUDA smoke passed\n"
NEW = b"- Ollama `0.32.0+helix.repeatlimit.1` enabled only after CUDA smoke passed\n"
EXPECTED_SHA256 = "962c2de28eaf28525e13a63f908e661ce7b94f45a07f43529edea6b4cdcf494e"


def git(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


target = Path("CURRENT_STATE.md")
try:
    candidate = target.read_bytes()
    candidate.decode("utf-8", errors="strict")
except (OSError, UnicodeDecodeError):
    raise SystemExit(1)

if hashlib.sha256(candidate).hexdigest() != EXPECTED_SHA256:
    raise SystemExit(1)
if candidate.count(OLD) != 0 or candidate.count(NEW) != 1:
    raise SystemExit(1)
before = b"- Secure Boot enabled\n"
after = b"- llama.cpp `b10173` / `e9fa0781f1c25fc4fe8c86be1edc6970661ad6f0`, built for `sm_120`\n"
if not (0 <= candidate.find(before) < candidate.find(NEW) < candidate.find(after)):
    raise SystemExit(1)

changed = git("diff", "--name-only", "HEAD", "--")
if changed.returncode != 0 or changed.stdout.splitlines() != [b"CURRENT_STATE.md"]:
    raise SystemExit(1)
untracked = git("ls-files", "--others", "--exclude-standard")
if untracked.returncode != 0 or untracked.stdout:
    raise SystemExit(1)

print("HIDDEN_VALIDATION_PASS")
