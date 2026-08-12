"""Visible Task 11N custom clarification-policy behavior validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import runpy
import subprocess
import sys


TARGET = Path("src/docwriter_web/writing_setup.py")
PREFIX_SHA256 = "bff170a53e2ccd60c27efd2a6d797ec5c620f25e8b5368584627e7ff57635fed"
SUFFIX_SHA256 = "992b47958a5af1a1596a8cbac8f80e167679e45a5a13c6682c7af268beb0db5d"


def fail(message: str) -> None:
    print(f"VISIBLE_VALIDATION_FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


if not TARGET.is_file() or TARGET.is_symlink():
    fail("writing_setup.py is unavailable")
try:
    content = TARGET.read_bytes()
    content.decode("utf-8", errors="strict")
    start = content.index(b"def from_form(")
    end = content.index(b"def from_row(")
except (OSError, UnicodeDecodeError, ValueError):
    fail("writing_setup.py is not the expected UTF-8 module")
if hashlib.sha256(content[:start]).hexdigest() != PREFIX_SHA256:
    fail("source before from_form changed")
if hashlib.sha256(content[end:]).hexdigest() != SUFFIX_SHA256:
    fail("source after from_form changed")

try:
    namespace = runpy.run_path(str(TARGET))
    from_form = namespace["from_form"]
except Exception as error:
    fail(f"module load failed: {type(error).__name__}")

standard = "Ask one focused question when ambiguity would materially change meaning"
custom = "Stop and ask the operator which timeline applies."
base = {
    "primary_audience": " General reader ",
    "tone": " Direct ",
    "purpose": " Explain the result. ",
    "preservation_instructions": " Preserve observed facts. ",
}

try:
    selected = from_form({**base, "clarification_policy": standard, "clarification_policy_custom": f"  {custom}  "})
    fallback_empty = from_form({**base, "clarification_policy": standard, "clarification_policy_custom": ""})
    fallback_blank = from_form({**base, "clarification_policy": standard, "clarification_policy_custom": " \t "})
    custom_only = from_form({**base, "clarification_policy_custom": custom})
except Exception as error:
    fail(f"functional check failed: {type(error).__name__}")

if selected.clarification_policy != custom or custom_only.clarification_policy != custom:
    fail("nonblank custom policy did not take precedence")
if fallback_empty.clarification_policy != standard or fallback_blank.clarification_policy != standard:
    fail("blank custom policy did not preserve the selected standard policy")
if selected.primary_audience != "General reader" or selected.completion_state != "DRAFT":
    fail("unrelated from_form behavior changed")
if set(selected.field_provenance.values()) != {"OPERATOR_ENTERED"}:
    fail("operator provenance behavior changed")

process = subprocess.run(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
if process.returncode != 0 or process.stdout != b" M src/docwriter_web/writing_setup.py\n":
    fail("writing_setup.py is not the sole changed path")

print("VISIBLE_VALIDATION_PASS")
