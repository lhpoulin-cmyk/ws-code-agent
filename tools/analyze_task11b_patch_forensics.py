#!/usr/bin/env python3
"""Analyze pinned Task 10/11 patch evidence without model inference or production repair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.contained_validation import SystemdContainedValidationRunner  # noqa: E402
from ws_code_agent.disposition_harness import RequestType, parse_request  # noqa: E402
from ws_code_agent.isolated_patch import IsolatedContext  # noqa: E402
from ws_code_agent.readonly_executor import ExecutorFact, ReadOnlyExecutor  # noqa: E402
from ws_code_agent.response_normalization import normalize_single_markdown_json_fence  # noqa: E402
from ws_code_agent.supervised_validation import WRITE_VALIDATION_IDS, validation_registry  # noqa: E402
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationStatus  # noqa: E402
from tools.task11b_patch_forensics import canonical_unified_diff, inspect_patch  # noqa: E402


STORE = Path.home() / ".local" / "share" / "ws-code-agent" / "work"
AFTER = b'def message():\n    return "hello"\n'
BEFORE_EXISTING = b'def message():\n    return "hi"\n'

EVIDENCE = (
    {
        "experiment": "TASK10R_14B_HISTORICAL_WRITE",
        "session": "work-task10r-restart-qwen25-write-20260811T191242Z",
        "turn": 1,
        "history": "docs/experiments/task10r-qwen25-coder-14b-v2-admission.md",
        "supplement": "docs/experiments/task10x-qwen25-coder-14b-adapter-calibration.md",
        "raw": "05b465998a33116f2d27af3d1598992a6d4b3d5721da5e2b316a24030ac36a76",
        "normalized": "829ccc3ffcec594e3af0e17a275914ed964b96d27c2beb193699a438a8b4070b",
        "patch": "c74b4378fdb032c7accb7405665702a988b749381908a6d2c16d3fa363efca3d",
        "historical_executor": "MALFORMED_REQUEST_STRICT_RAW; PATCH_REJECTED_NORMALIZED_REPLAY",
        "fixture": "new",
        "correction": "recalculate new hunk count 3 to 2",
        "corrected": "8cf8904302ab6e6dcd845a633b7ab692b91a3830d5fd14b1cbe1851bfbcccc41",
    },
    {
        "experiment": "TASK10Y_14B_WRITE",
        "session": "work-task10y-qwen25-14b-write-20260811T235900Z",
        "turn": 1,
        "history": "docs/experiments/task10y-qwen25-coder-14b-normalized-production-lane.md",
        "raw": "c71599a739e700cab11516bb8f82e7e6ca8a7566966c6e9c44f4d87cdd955a91",
        "normalized": "e1c63e910a36a175ee5c07635f7c092834ca9cf7f15452812f0b18a4c4311b55",
        "patch": "e6c95167412085836fb880f42b51bf571f600dc2b2d88251c0357df26478cfa2",
        "historical_executor": "PATCH_REJECTED",
        "fixture": "new",
        "correction": "recalculate new hunk count 3 to 2",
        "corrected": "85ebb1e42342fc6645066b1bced8af2a1640f64abf58c57cf768adc9be20e99b",
    },
    {
        "experiment": "TASK11A_14B_WRITE",
        "session": "work-task11a-qwen25-14b-positive-20260812T142051Z",
        "turn": 2,
        "history": "docs/experiments/task11a-restricted-interactive-coder-acceptance.md",
        "raw": "7b367e7154161e9b727d4727226f9dde4fdb73d3aa3917e53cfc773332be688a",
        "normalized": "1a0a9d585a764d2c6be594ccce029f761a6a0107caeb7209d183751522838911",
        "patch": "4d4ec9023252de2f1997c77c2df1db5f1fed8b89d9e88337db686c54e0902752",
        "historical_executor": "PATCH_REJECTED",
        "fixture": "existing",
        "correction": "add exact path-derived file headers; prefix source-matching context; append LF",
        "corrected": "8acca1c12f6482ad9d55661f7945eb4561840a3b4e42ecf05b808c42f9f31a8a",
    },
    {
        "experiment": "TASK11A_14B_WRITE",
        "session": "work-task11a-qwen25-14b-positive-20260812T142051Z",
        "turn": 3,
        "history": "docs/experiments/task11a-restricted-interactive-coder-acceptance.md",
        "raw": "a766d876888b62252091dec4fb0fccf5774aa9e84122b3172b90179352e158a5",
        "normalized": "42ac1348d09a317038524af58809619cba9ec7c84f33909844188e5938c8a3ca",
        "patch": "08344b89080431907a13260dde38ab5af46c4ac2c62c22bb57f0a1b74a10bd72",
        "historical_executor": "PATCH_REJECTED",
        "fixture": "existing",
        "correction": "prefix source-matching context; append LF",
        "corrected": "8acca1c12f6482ad9d55661f7945eb4561840a3b4e42ecf05b808c42f9f31a8a",
    },
    {
        "experiment": "TASK10V_32B_WRITE",
        "session": "work-task10v-qwen25-32b-write-20260811T203928Z",
        "turn": 1,
        "history": "docs/experiments/task10v-qwen25-coder-32b-v2-scale-control.md",
        "raw": "66c8b6cc053a15c782e579db4d18cdc22fa315d80592c968f6332b91bf7c1ba3",
        "normalized": "66c8b6cc053a15c782e579db4d18cdc22fa315d80592c968f6332b91bf7c1ba3",
        "patch": "b9ac785eaf771e743c0d343f3b64cf35c3f8b8ff6a988d2e9360ce69b0654624",
        "historical_executor": "PATCH_REJECTED",
        "fixture": "new-one-line",
        "correction": "append LF",
        "corrected": "ecebf6c32629655c7fdaa6234b6e65fc6efa656a16352da3f8090e70d7033751",
    },
    {
        "experiment": "TASK10V_32B_WRITE",
        "session": "work-task10v-qwen25-32b-write-20260811T203928Z",
        "turn": 2,
        "history": "docs/experiments/task10v-qwen25-coder-32b-v2-scale-control.md",
        "raw": "7664074a04d9d18008d9eae6452c85c3ea87777feb6a9dfe2ee21fbcb129d7d7",
        "normalized": "7664074a04d9d18008d9eae6452c85c3ea87777feb6a9dfe2ee21fbcb129d7d7",
        "patch": "d0ba6193c65c7abd20101d74b98dc1bec23d41239b7b380a983cbf7500f8f44b",
        "historical_executor": "CANDIDATE_READY",
        "fixture": "new-one-line",
        "correction": "none",
        "corrected": "d0ba6193c65c7abd20101d74b98dc1bec23d41239b7b380a983cbf7500f8f44b",
    },
)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def fail(detail: str) -> None:
    raise RuntimeError(f"TASK11B_EVIDENCE_BINDING_FAILURE: {detail}")


def git_check(repository: Path, patch: bytes) -> dict[str, object]:
    process = subprocess.run(
        ["git", "-C", str(repository), "apply", "--check", "--whitespace=nowarn", "-"],
        input=patch,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "applies": process.returncode == 0,
        "exit_code": process.returncode,
        "stderr": process.stderr.decode("utf-8", errors="replace").strip(),
    }


def forensic_minimum_control(spec: dict[str, object], patch: bytes) -> bytes:
    """Exact evidence-specific control; deliberately unavailable to production."""

    experiment = str(spec["experiment"])
    turn = int(spec["turn"])
    text = patch.decode("utf-8")
    if experiment == "TASK10R_14B_HISTORICAL_WRITE" or experiment == "TASK10Y_14B_WRITE":
        if text.count("@@ -0,0 +1,3 @@") != 1:
            fail(f"{experiment}: pinned hunk header changed")
        result = text.replace("@@ -0,0 +1,3 @@", "@@ -0,0 +1,2 @@")
    elif experiment == "TASK11A_14B_WRITE" and turn == 2:
        if text.count("\ndef message():") != 1:
            fail("Task 11A turn 2 context changed")
        result = (
            "diff --git a/src/message.py b/src/message.py\n"
            "--- a/src/message.py\n"
            "+++ b/src/message.py\n"
            + text.replace("\ndef message():", "\n def message():")
            + "\n"
        )
    elif experiment == "TASK11A_14B_WRITE" and turn == 3:
        if text.count("\ndef message():") != 1:
            fail("Task 11A turn 3 context changed")
        result = text.replace("\ndef message():", "\n def message():") + "\n"
    elif experiment == "TASK10V_32B_WRITE" and turn == 1:
        result = text + "\n"
    else:
        result = text
    return result.encode("utf-8")


def semantic_classification(fixture: str, patch_evidence: dict[str, object]) -> str:
    hunks = patch_evidence["hunks"]
    if len(hunks) != 1:
        return "SEMANTIC_EDIT_NOT_RECOVERABLE"
    hunk = hunks[0]
    added = tuple(hunk["added_lines"])
    removed = tuple(hunk["removed_lines"])
    invalid = tuple(hunk["invalid_lines"])
    context = tuple(hunk["context_content"])
    if fixture == "new" and added == ("def message():", '    return "hello"') and not removed:
        return "SEMANTIC_EDIT_CORRECT"
    if fixture == "new-one-line" and added == ('def message(): return "hello"',) and not removed:
        return "SEMANTIC_EDIT_CORRECT"
    if (
        fixture == "existing"
        and added == ('    return "hello"',)
        and removed == ('    return "hi"',)
        and (invalid == ("def message():",) or context == ("def message():",))
    ):
        return "SEMANTIC_EDIT_CORRECT"
    return "SEMANTIC_EDIT_INCORRECT"


def inspect_evidence(spec: dict[str, object]) -> dict[str, object]:
    session = STORE / str(spec["session"])
    turn = session / "cases" / "WORK" / "turns" / f"{int(spec['turn']):04d}"
    raw = (turn / "raw-response.txt").read_bytes()
    state = json.loads((turn / "state.json").read_text(encoding="utf-8"))
    harness = json.loads((turn / "harness-result.json").read_text(encoding="utf-8"))
    if sha256(raw) != spec["raw"] or state["raw_sha256"] != spec["raw"]:
        fail(f"{spec['experiment']} turn {spec['turn']}: raw SHA")
    for document in (spec["history"], spec.get("supplement")):
        if document and str(spec["raw"]) not in (ROOT / str(document)).read_text(encoding="utf-8"):
            fail(f"{spec['experiment']} turn {spec['turn']}: historical raw reference")

    normalized_path = turn / "normalized-parser-input.txt"
    normalized = (
        normalized_path.read_bytes()
        if normalized_path.exists()
        else normalize_single_markdown_json_fence(raw).normalized_parser_input
    )
    if sha256(normalized) != spec["normalized"]:
        fail(f"{spec['experiment']} turn {spec['turn']}: normalized SHA")
    request = parse_request(normalized.decode("utf-8"))
    if request.request_type is not RequestType.PROPOSE_PATCH:
        fail(f"{spec['experiment']} turn {spec['turn']}: request type")
    patch = request.arguments["patch"].encode("utf-8")
    paths = tuple(request.arguments["proposed_paths"])
    if sha256(patch) != spec["patch"] or paths != ("src/message.py",):
        fail(f"{spec['experiment']} turn {spec['turn']}: parsed patch binding")
    if harness.get("parsed_arguments") is not None and harness["parsed_arguments"] != request.arguments:
        fail(f"{spec['experiment']} turn {spec['turn']}: historical parsed arguments")

    manifest = json.loads((session / "session-manifest.json").read_text(encoding="utf-8"))
    repository = Path(manifest["repository"]["canonical_path"])
    structure = inspect_patch(patch, paths).evidence()
    correction_one = forensic_minimum_control(spec, patch)
    correction_two = forensic_minimum_control(spec, patch)
    if correction_one != correction_two or sha256(correction_one) != spec["corrected"]:
        fail(f"{spec['experiment']} turn {spec['turn']}: deterministic control")
    corrected_structure = inspect_patch(correction_one, paths).evidence()
    if corrected_structure["findings"]:
        fail(f"{spec['experiment']} turn {spec['turn']}: corrected structure")
    original_semantic = semantic_classification(str(spec["fixture"]), structure)
    corrected_semantic = semantic_classification(str(spec["fixture"]), corrected_structure)
    if original_semantic != "SEMANTIC_EDIT_CORRECT" or corrected_semantic != original_semantic:
        fail(f"{spec['experiment']} turn {spec['turn']}: semantic preservation")
    return {
        "experiment": spec["experiment"],
        "session": spec["session"],
        "turn": spec["turn"],
        "raw_sha256": spec["raw"],
        "normalized_sha256": spec["normalized"],
        "strict_historical_request_type": harness.get("request_type"),
        "forensic_request_type": request.request_type.value,
        "patch_sha256": spec["patch"],
        "patch_bytes": len(patch),
        "proposed_paths": list(paths),
        "historical_executor_result": spec["historical_executor"],
        "structure": structure,
        "semantic_classification": original_semantic,
        "minimum_correction": spec["correction"],
        "minimum_correction_classification": "NOT_REQUIRED" if spec["correction"] == "none" else "MECHANICAL",
        "corrected_patch_sha256": spec["corrected"],
        "determinism": {
            "unique_result": True,
            "semantic_bytes_changed": False,
            "authority_changed": False,
            "git_apply_check": git_check(repository, correction_one),
        },
    }


def canonical_control(name: str, session_id: str, before: bytes | None, after: bytes) -> dict[str, object]:
    source_session = STORE / session_id
    manifest = json.loads((source_session / "session-manifest.json").read_text(encoding="utf-8"))
    source = Path(manifest["repository"]["canonical_path"])
    patch = canonical_unified_diff("src/message.py", before, after)
    with tempfile.TemporaryDirectory(prefix="ws-code-agent-isolated-task11b-control-") as temporary:
        workspace = Path(temporary)
        repository = workspace / "repository"
        shutil.copytree(source, repository, symlinks=True)
        observer = ReadOnlyExecutor()
        initial = observer.observe_repository(repository).snapshot
        process = subprocess.run(
            ["git", "-C", str(repository), "apply", "--index", "--whitespace=nowarn", "-"],
            input=patch,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(f"canonical control failed: {process.stderr.decode()}")
        result = observer.observe_repository(repository).snapshot
        context = IsolatedContext(
            source_snapshot=initial,
            workspace_root=str(workspace),
            isolated_root=str(repository),
            initial_snapshot=initial,
            initial_manifest={},
            build_fact=ExecutorFact(
                operation="TASK11B_CANONICAL_DIFF_CONTROL",
                success=True,
                snapshot_identity=initial.snapshot_identity,
                observed_result={"control": name},
            ),
        )
        executor = DescriptorValidationExecutor(
            validation_registry(), observer, SystemdContainedValidationRunner()
        )
        validations = [
            executor.run_validation(context, result, descriptor, WRITE_VALIDATION_IDS)
            for descriptor in WRITE_VALIDATION_IDS
        ]
        if any(item.status is not ValidationStatus.VALIDATION_PASS for item in validations):
            raise RuntimeError(f"canonical control validation failed: {name}")
        if observer.observe_repository(repository).snapshot.snapshot_identity != result.snapshot_identity:
            raise RuntimeError(f"canonical control validator changed repository: {name}")
        changed = subprocess.check_output(
            ["git", "-C", str(repository), "diff", "--cached", "--name-only"], text=True
        ).splitlines()
        resulting = (repository / "src/message.py").read_bytes()
        return {
            "control": name,
            "patch_sha256": sha256(patch),
            "patch_bytes": len(patch),
            "applies": True,
            "changed_paths": changed,
            "resulting_source_sha256": sha256(resulting),
            "resulting_source": resulting.decode("utf-8"),
            "visible_validation": validations[0].status.value,
            "hidden_validation": validations[1].status.value,
            "containment_profiles": [
                item.containment_evidence["CONTAINMENT_PROFILE"] for item in validations
            ],
            "validator_effect": "UNCHANGED",
        }


def main() -> int:
    evidence = [inspect_evidence(dict(spec)) for spec in EVIDENCE]
    controls = [
        canonical_control(
            "task10k-create-message",
            "work-task10v-qwen25-32b-write-20260811T203928Z",
            None,
            AFTER,
        ),
        canonical_control(
            "task11a-existing-message",
            "work-task11a-qwen25-14b-positive-20260812T142051Z",
            BEFORE_EXISTING,
            AFTER,
        ),
    ]
    print(json.dumps({
        "checkpoint": "TASK11B-INTERACTIVE-PATCH-SERIALIZATION-FORENSICS",
        "evidence_binding": "PASS",
        "evidence": evidence,
        "canonical_controls": controls,
        "model_inference_count": 0,
        "production_behavior_changed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
