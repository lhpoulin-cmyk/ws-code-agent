#!/usr/bin/env python3
"""Loopback-only entry point for the Doc Writer review surface."""
import sys
from pathlib import Path
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from docwriter_web import AppConfig, DocWriterApp  # noqa: E402


def main() -> None:
    make_server("127.0.0.1", 8787, DocWriterApp(AppConfig.from_environment())).serve_forever()


if __name__ == "__main__":
    main()
