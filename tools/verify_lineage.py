#!/usr/bin/env python3
"""Read-only verification of this repository's recorded Git lineage."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


FORK_SOURCE = "dfb759afb7826a2b849fa95bf40ce6f06cd3cd05"
VERIFIED_CHECKPOINT = "7ae3d5794691fd769446702015f331367344df9d"
CONTRACT = Path("docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md")


def git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(("git", *args), cwd=cwd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False)


def report(name: str, passed: bool) -> bool:
    print(f"{'PASS' if passed else 'FAIL'} {name}")
    return passed


def main() -> int:
    root_result = git("rev-parse", "--show-toplevel")
    in_repository = root_result.returncode == 0
    ok = report("inside_git_repository", in_repository)
    if not in_repository:
        return 1

    root = Path(root_result.stdout.strip())
    source_exists = git("cat-file", "-e", f"{FORK_SOURCE}^{{commit}}", cwd=root).returncode == 0
    ok = report("fork_source_exists", source_exists) and ok
    source_ancestor = source_exists and git("merge-base", "--is-ancestor", FORK_SOURCE, "HEAD", cwd=root).returncode == 0
    ok = report("fork_source_is_head_ancestor", source_ancestor) and ok

    checkpoint_exists = git("cat-file", "-e", f"{VERIFIED_CHECKPOINT}^{{commit}}", cwd=root).returncode == 0
    ok = report("verified_checkpoint_exists", checkpoint_exists) and ok
    checkpoint_ancestor = checkpoint_exists and source_exists and git(
        "merge-base", "--is-ancestor", VERIFIED_CHECKPOINT, FORK_SOURCE, cwd=root
    ).returncode == 0
    ok = report("verified_checkpoint_is_fork_source_ancestor", checkpoint_ancestor) and ok

    contract = root / CONTRACT
    contract_records_source = contract.is_file() and FORK_SOURCE in contract.read_text(encoding="utf-8")
    ok = report("foundation_contract_records_fork_source", contract_records_source) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
