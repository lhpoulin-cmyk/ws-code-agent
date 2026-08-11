#!/usr/bin/env python3
"""Bounded operator interface for the synthetic protocol anchoring probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.alpha_experiment import ExperimentError  # noqa: E402
from ws_code_agent.katra_ollama_backend import (  # noqa: E402
    KatraOllamaBackendError,
    KatraOllamaDispositionBackend,
)
from ws_code_agent.protocol_anchoring_probe import (  # noqa: E402
    PROBE_A,
    PROBE_B,
    ProtocolAnchoringProbeController,
    ProtocolAnchoringProbeError,
    generated_probe_id,
)


STORE = Path.home() / ".local" / "share" / "ws-code-agent" / "protocol-probes"


def _head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start")
    start.add_argument("--presentation", choices=(PROBE_A, PROBE_B), required=True)
    start.add_argument("--session-id")
    start.add_argument("--turn-limit", type=int, default=8)
    for command in ("status", "step"):
        item = commands.add_parser(command)
        item.add_argument("session")
    args = parser.parse_args()
    try:
        if args.command == "start":
            controller = ProtocolAnchoringProbeController.start(
                STORE,
                session_id=args.session_id or generated_probe_id(),
                presentation=args.presentation,
                harness_sha=_head(),
                turn_limit=args.turn_limit,
            )
        else:
            controller = ProtocolAnchoringProbeController(STORE / args.session)
            if args.command == "step":
                controller.step(KatraOllamaDispositionBackend())
        output = controller.status()
    except (
        OSError,
        UnicodeError,
        ExperimentError,
        KatraOllamaBackendError,
        ProtocolAnchoringProbeError,
    ) as error:
        print(json.dumps({"status": "ERROR", "error": str(error)}, sort_keys=True, indent=2))
        return 2
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
