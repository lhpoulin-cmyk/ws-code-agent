"""Evaluator-only Task 11N custom clarification-policy behavior oracle."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import subprocess


TARGET = Path("src/docwriter_web/writing_setup.py")
OUTSIDE_FROM_FORM_AST_SHA256 = "cdf4585029dbf9b2052d346f5a8f8bc8bfd173d7967876ebcdd935fae2b012ae"


def git(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


try:
    source = TARGET.read_text(encoding="utf-8", errors="strict")
    tree = ast.parse(source)
except (OSError, UnicodeDecodeError, SyntaxError):
    raise SystemExit(1)

from_form_nodes = [
    node for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "from_form"
]
if len(from_form_nodes) != 1:
    raise SystemExit(1)
tree.body = [node for node in tree.body if node not in from_form_nodes]
outside = ast.dump(tree, annotate_fields=True, include_attributes=False)
if hashlib.sha256(outside.encode()).hexdigest() != OUTSIDE_FROM_FORM_AST_SHA256:
    raise SystemExit(1)

namespace: dict[str, object] = {"__name__": "__main__"}
try:
    exec(compile(source, str(TARGET), "exec"), namespace)
    from_form = namespace["from_form"]
    standard = "Preserve ambiguity and draft without guessing"
    unicode_custom = "Ask which café résumé is authoritative."
    chosen = from_form({"clarification_policy": standard, "clarification_policy_custom": f"\n{unicode_custom}\t"})
    fallback = from_form({"clarification_policy": standard, "clarification_policy_custom": "\n\t"})
    maximum = from_form({"clarification_policy": standard, "clarification_policy_custom": "x" * 1000})
    empty = from_form({})
except Exception:
    raise SystemExit(1)

if chosen.clarification_policy != unicode_custom:
    raise SystemExit(1)
if fallback.clarification_policy != standard:
    raise SystemExit(1)
if maximum.clarification_policy != "x" * 1000:
    raise SystemExit(1)
if empty.clarification_policy != "" or "clarification_policy" not in empty.missing_fields:
    raise SystemExit(1)
try:
    from_form({"clarification_policy": standard, "clarification_policy_custom": "x" * 1001})
except ValueError:
    pass
else:
    raise SystemExit(1)

changed = git("diff", "--name-only", "HEAD", "--")
if changed.returncode != 0 or changed.stdout.splitlines() != [b"src/docwriter_web/writing_setup.py"]:
    raise SystemExit(1)
untracked = git("ls-files", "--others", "--exclude-standard")
if untracked.returncode != 0 or untracked.stdout:
    raise SystemExit(1)

print("HIDDEN_VALIDATION_PASS")
