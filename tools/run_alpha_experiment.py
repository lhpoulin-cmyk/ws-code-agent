#!/usr/bin/env python3
"""Bounded Task 10E start/status/one-turn operator entrypoint."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ws_code_agent.alpha_case_adapters import CASE_ORDER, initialize_task10e
from ws_code_agent.alpha_experiment import AlphaExperimentController
from ws_code_agent.katra_ollama_backend import KatraOllamaDispositionBackend, MODEL_DIGEST, MODEL_QUANTIZATION, MODEL_TAG

STORE=Path.home() / ".local/share/ws-code-agent/experiments"
PEERS={"ws-cp": Path("/home/louis/helix-arpa/ws-cp"), "gpu-compute": Path("/home/louis/helix-arpa/gpu-compute"), "gpu-cp": Path("/home/louis/helix-arpa/gpu-cp"), "ws-doc-writer": Path("/home/louis/src/ws-doc-writer")}

def head(path: Path) -> str: return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()

def main() -> int:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command", required=True)
    start=sub.add_parser("start-task10e"); start.add_argument("experiment_id")
    status=sub.add_parser("status"); status.add_argument("experiment_id")
    step=sub.add_parser("step"); step.add_argument("experiment_id"); step.add_argument("case_id", choices=CASE_ORDER)
    args=parser.parse_args()
    if args.command == "start-task10e":
        manifest={"experiment_id": args.experiment_id, "created_at": datetime.now(timezone.utc).isoformat(), "experiment_harness_sha": head(ROOT), "peer_shas": {name: head(path) for name,path in PEERS.items()}, "model": {"tag": MODEL_TAG, "digest": MODEL_DIGEST, "quantization": MODEL_QUANTIZATION}, "transport": "OLLAMA_MACHINE_RESPONSE_V1", "execution_policy": "GPU_PRIMARY_PARTIAL_OFFLOAD; GPU>=80; CPU<=20", "context": 4096, "sampling": "appliance/Ollama defaults", "alpha_gate": "PASS", "case_order": list(CASE_ORDER)}
        controller=initialize_task10e(STORE, manifest)
    else: controller=AlphaExperimentController(STORE / args.experiment_id)
    if args.command == "step": controller.step_registered(args.case_id, KatraOllamaDispositionBackend())
    print(json.dumps(controller.status(), sort_keys=True, indent=2)); return 0

if __name__ == "__main__": raise SystemExit(main())
