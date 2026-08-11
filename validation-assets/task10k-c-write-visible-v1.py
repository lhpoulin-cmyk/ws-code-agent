"""Visible Task 10K-C write contract validator."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys


def fail(message: str) -> None:
    print(f"VISIBLE_VALIDATION_FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


path = Path("src/message.py")
if not path.is_file() or path.is_symlink():
    fail("src/message.py is unavailable")

try:
    spec = importlib.util.spec_from_file_location("task10k_visible_message", path)
    if spec is None or spec.loader is None:
        fail("src/message.py cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
except (OSError, SyntaxError, ImportError, RuntimeError) as error:
    fail(f"src/message.py is not valid loadable Python ({type(error).__name__})")

message = getattr(module, "message", None)
if not callable(message):
    fail("callable message is missing")
if inspect.signature(message).parameters:
    fail("message must accept no arguments")

try:
    result = message()
except Exception as error:
    fail(f"message() raised {type(error).__name__}")
if type(result) is not str or result != "hello":
    fail('message() must return exactly the string "hello"')

print("VISIBLE_VALIDATION_PASS")
