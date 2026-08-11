#!/usr/bin/env python3
"""Bounded operator interface for supervised single-repository work."""

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
    DEVSTRAL_MODEL_DIGEST,
    DevstralKatraOllamaDispositionBackend,
    KatraOllamaBackendError,
    KatraOllamaDispositionBackend,
    MODEL_DIGEST,
)
from ws_code_agent.supervised_work import (  # noqa: E402
    SYNTHETIC_V2_FIXTURES,
    SupervisedWorkController,
    SupervisedWorkError,
    generated_session_id,
)


STORE = Path.home() / ".local" / "share" / "ws-code-agent" / "work"
QUALIFICATION = ROOT / "docs" / "qualification" / "qwen3-coder-30b-alpha-v1.yaml"
DEVSTRAL_CANDIDATE = ROOT / "docs" / "qualification" / "devstral-small-2-v2-admission-candidate.yaml"


def _head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--repo", type=Path, action="append", required=True)
    start.add_argument("--expected-head", required=True)
    start.add_argument("--objective", type=Path, required=True)
    start.add_argument("--allow-read", action="append", required=True)
    start.add_argument("--allow-patch", action="append", default=[])
    start.add_argument("--turn-limit", type=int, default=8)
    start.add_argument("--session-id")
    synthetic_v2 = sub.add_parser("start-synthetic-v2")
    synthetic_v2.add_argument("--fixture", choices=SYNTHETIC_V2_FIXTURES, required=True)
    synthetic_v2.add_argument("--turn-limit", type=int, default=8)
    synthetic_v2.add_argument("--session-id")
    devstral_v2 = sub.add_parser("start-devstral-v2")
    devstral_v2.add_argument("--fixture", choices=SYNTHETIC_V2_FIXTURES, required=True)
    devstral_v2.add_argument("--turn-limit", type=int, default=8)
    devstral_v2.add_argument("--session-id")
    for command in ("status", "step", "review", "approve", "reject"):
        item = sub.add_parser(command)
        item.add_argument("session")
    args = parser.parse_args()
    try:
        if args.command == "start":
            if len(args.repo) != 1:
                raise SupervisedWorkError("SUPERVISION_REQUIRED_CROSS_REPOSITORY")
            if not args.objective.is_file() or args.objective.is_symlink():
                raise SupervisedWorkError("OBJECTIVE_FILE_UNAVAILABLE")
            session_id = args.session_id or generated_session_id()
            controller = SupervisedWorkController.start(
                STORE,
                session_id=session_id,
                repository=args.repo[0],
                expected_head=args.expected_head,
                objective=args.objective.read_text(encoding="utf-8"),
                read_scopes=tuple(args.allow_read),
                patch_paths=tuple(args.allow_patch),
                qualification_path=QUALIFICATION,
                harness_sha=_head(),
                turn_limit=args.turn_limit,
            )
            output = controller.status()
        elif args.command == "start-synthetic-v2":
            session_id = args.session_id or generated_session_id()
            controller = SupervisedWorkController.start_synthetic_v2(
                STORE,
                session_id=session_id,
                fixture_kind=args.fixture,
                qualification_path=QUALIFICATION,
                harness_sha=_head(),
                turn_limit=args.turn_limit,
            )
            output = controller.status()
        elif args.command == "start-devstral-v2":
            session_id = args.session_id or generated_session_id()
            controller = SupervisedWorkController.start_devstral_v2_admission(
                STORE,
                session_id=session_id,
                fixture_kind=args.fixture,
                candidate_path=DEVSTRAL_CANDIDATE,
                harness_sha=_head(),
                turn_limit=args.turn_limit,
            )
            output = controller.status()
        else:
            controller = SupervisedWorkController(STORE / args.session)
            if args.command == "step":
                digest = controller.manifest()["model_artifact"]["digest"]
                if digest == DEVSTRAL_MODEL_DIGEST:
                    backend = DevstralKatraOllamaDispositionBackend()
                elif digest == MODEL_DIGEST:
                    backend = KatraOllamaDispositionBackend()
                else:
                    raise SupervisedWorkError("MODEL_QUALIFICATION_MISMATCH")
                controller.step(backend)
                output = controller.status()
            elif args.command == "review":
                output = controller.review()
            elif args.command in {"approve", "reject"}:
                output = controller.disposition(args.command.upper())
            else:
                output = controller.status()
    except (OSError, UnicodeError, ExperimentError, KatraOllamaBackendError, SupervisedWorkError) as error:
        print(json.dumps({"status": "ERROR", "error": str(error)}, sort_keys=True, indent=2))
        return 2
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
