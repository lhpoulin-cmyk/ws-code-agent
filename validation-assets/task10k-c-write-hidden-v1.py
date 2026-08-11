"""Evaluator-only independent Task 10K-C write oracle."""

from __future__ import annotations

import inspect
from pathlib import Path


target = Path("src/message.py")
try:
    program = compile(target.read_bytes(), str(target), "exec")
except (OSError, SyntaxError):
    raise SystemExit(1)

namespace: dict[str, object] = {"__name__": "task10k_hidden_message"}
try:
    exec(program, namespace)
except Exception:
    raise SystemExit(1)

candidate = namespace.get("message")
if not callable(candidate):
    raise SystemExit(1)

try:
    signature = inspect.signature(candidate)
    signature.bind()
    try:
        signature.bind(object())
    except TypeError:
        pass
    else:
        raise SystemExit(1)
    first = candidate()
    second = candidate()
except Exception:
    raise SystemExit(1)

if type(first) is not str or type(second) is not str:
    raise SystemExit(1)
if first != "hello" or second != "hello":
    raise SystemExit(1)

print("HIDDEN_VALIDATION_PASS")
