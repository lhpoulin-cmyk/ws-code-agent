"""Small, signed presentation preferences with no editorial authority."""

from __future__ import annotations

import hashlib
import hmac

NORMAL = "normal"
DEVELOPER = "developer"


def _signature(value: str, secret: bytes) -> str:
    return hmac.new(secret, value.encode("ascii"), hashlib.sha256).hexdigest()


def mode_from_cookie(cookie: str, secret: bytes) -> str:
    for item in cookie.split(";"):
        if "=" not in item:
            continue
        key, value = item.strip().split("=", 1)
        if key != "docwriter_mode" or "." not in value:
            continue
        mode, signature = value.split(".", 1)
        if mode in {NORMAL, DEVELOPER} and hmac.compare_digest(signature, _signature(mode, secret)):
            return mode
    return NORMAL


def mode_cookie(mode: str, secret: bytes) -> str:
    if mode not in {NORMAL, DEVELOPER}:
        raise ValueError("unknown presentation mode")
    return f"docwriter_mode={mode}.{_signature(mode, secret)}; Path=/; Secure; HttpOnly; SameSite=Strict"
