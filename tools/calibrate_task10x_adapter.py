#!/usr/bin/env python3
"""Replay preserved responses through the disabled Task 10X adapter candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.contained_validation import SystemdContainedValidationRunner  # noqa: E402
from ws_code_agent.disposition_harness import ModelRequest, RequestParseError, RequestType, parse_request  # noqa: E402
from ws_code_agent.isolated_patch import ApplicationStatus, IsolatedPatchExecutor, PatchProposal  # noqa: E402
from ws_code_agent.readonly_executor import CompareStatus, ReadOnlyExecutor  # noqa: E402
from ws_code_agent.response_normalization import normalize_single_markdown_json_fence  # noqa: E402
from ws_code_agent.supervised_validation import WRITE_VALIDATION_IDS, validation_registry  # noqa: E402
from ws_code_agent.supervised_work import (  # noqa: E402
    SYNTHETIC_V2_WRITE,
    _WRITE_OBJECTIVE,
    _WRITE_README,
    _initialize_synthetic_v2_fixture,
)
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationStatus  # noqa: E402


WORK_ROOT = Path.home() / ".local/share/ws-code-agent/work"
PRESERVED = {
    "qwen25_14b_write": (
        "work-task10r-restart-qwen25-write-20260811T191242Z",
        1,
        "05b465998a33116f2d27af3d1598992a6d4b3d5721da5e2b316a24030ac36a76",
        RequestType.PROPOSE_PATCH,
    ),
    "qwen25_14b_clarification": (
        "work-task10r-restart-qwen25-clarification-20260811T191417Z",
        1,
        "c71974d0782e966e6ad9481150346d15d6058c8e7b9cc1bc7ef6bf0eb2488ead",
        RequestType.NO_CHANGE,
    ),
    "qwen25_32b_write": (
        "work-task10v-qwen25-32b-write-20260811T203928Z",
        2,
        "7664074a04d9d18008d9eae6452c85c3ea87777feb6a9dfe2ee21fbcb129d7d7",
        RequestType.PROPOSE_PATCH,
    ),
    "qwen25_32b_clarification": (
        "work-task10v-qwen25-32b-clarification-20260811T204600Z",
        1,
        "55ccaa45aa97da74467abab4345271e786b09327aad71103782f029ce5e95813",
        RequestType.REQUEST_CLARIFICATION,
    ),
}
WRITE_FIXTURE_IDENTITY = "db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6"


def preserved_raw(key: str) -> bytes:
    session, turn, expected_sha, _ = PRESERVED[key]
    path = WORK_ROOT / session / "cases/WORK/turns" / f"{turn:04d}" / "raw-response.txt"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise RuntimeError(f"{key}: PRESERVED_RAW_IDENTITY_MISMATCH")
    return raw


def normalize_and_parse(key: str) -> tuple[dict[str, object], ModelRequest]:
    raw = preserved_raw(key)
    normalized = normalize_single_markdown_json_fence(raw)
    try:
        parser_input = normalized.normalized_parser_input.decode("utf-8")
        parsed = parse_request(parser_input)
    except (UnicodeDecodeError, RequestParseError) as error:
        raise RuntimeError(f"{key}: parser rejected calibrated input") from error
    expected_type = PRESERVED[key][3]
    if parsed.request_type is not expected_type:
        raise RuntimeError(f"{key}: SEMANTIC_REQUEST_CHANGED")
    result = {
        **normalized.evidence(),
        "preserved_response_identity": "MATCH",
        "parser_result": "VALID",
        "parser_request_type": parsed.request_type.value,
    }
    return result, parsed


def fixture_identity() -> str:
    payload = json.dumps(
        [
            _WRITE_OBJECTIVE,
            _WRITE_README,
            "",
            "task10k-c-write/synthetic-v1",
            (".",),
            ("src/message.py",),
        ],
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def replay_write(parsed: ModelRequest) -> dict[str, object]:
    if fixture_identity() != WRITE_FIXTURE_IDENTITY:
        raise RuntimeError("FROZEN_WRITE_FIXTURE_IDENTITY_MISMATCH")
    observer = ReadOnlyExecutor()
    patcher = IsolatedPatchExecutor(observer)
    with tempfile.TemporaryDirectory(prefix="task10x-write-replay-") as temporary:
        store = Path(temporary) / "store"
        repository, _, read_scopes, patch_paths, identity = _initialize_synthetic_v2_fixture(
            store, "task10x-retrospective-write", SYNTHETIC_V2_WRITE
        )
        if identity != "task10k-c-write/synthetic-v1" or read_scopes != (".",):
            raise RuntimeError("FROZEN_WRITE_FIXTURE_BINDING_MISMATCH")
        snapshot = observer.observe_repository(repository).snapshot
        context = patcher.build_isolated_copy(snapshot)
        try:
            proposal = PatchProposal.create(
                snapshot,
                parsed.arguments["patch"].encode(),
                tuple(parsed.arguments["proposed_paths"]),
            )
            application = patcher.apply_patch_isolated(context, proposal, patch_paths)
            classification = {
                ApplicationStatus.SUCCESS: "PATCH_ACCEPTED",
                ApplicationStatus.PATCH_REJECTED: "PATCH_REJECTED",
            }.get(application.status, "AUTHORITY_REJECTED")
            result: dict[str, object] = {
                "fixture_identity": WRITE_FIXTURE_IDENTITY,
                "source_snapshot_before": snapshot.snapshot_identity,
                "executor_result": classification,
                "executor_status": application.status.value,
                "executor_detail": application.fact.observed_result,
                "changed_paths": list(application.actual_changed_paths),
                "candidate_identity": None,
                "visible_validation": "NOT_EVALUATED",
                "hidden_validation": "NOT_EVALUATED",
                "technical_correctness": "NOT_EVALUATED",
            }
            if application.status is ApplicationStatus.SUCCESS and application.result_snapshot is not None:
                result["candidate_identity"] = application.result_snapshot.snapshot_identity
                validator = DescriptorValidationExecutor(
                    validation_registry(), observer, SystemdContainedValidationRunner()
                )
                runs = [
                    validator.run_validation(
                        context, application.result_snapshot, descriptor_id, WRITE_VALIDATION_IDS
                    )
                    for descriptor_id in WRITE_VALIDATION_IDS
                ]
                result["visible_validation"] = runs[0].status.value
                result["hidden_validation"] = runs[1].status.value
                result["technical_correctness"] = (
                    "VALIDATED"
                    if all(run.status is ValidationStatus.VALIDATION_PASS for run in runs)
                    else "FAILED"
                )
                result["candidate_snapshot_after_validation"] = observer.observe_repository(
                    context.isolated_root
                ).snapshot.snapshot_identity
            result["source_snapshot_after"] = observer.observe_repository(repository).snapshot.snapshot_identity
            result["source_snapshot_preserved"] = (
                observer.compare_snapshot(snapshot).status is CompareStatus.MATCH
            )
            return result
        finally:
            patcher.cleanup(context)


def main() -> int:
    write, write_request = normalize_and_parse("qwen25_14b_write")
    clarification, _ = normalize_and_parse("qwen25_14b_clarification")
    if not write["transformation_applied"] or not clarification["transformation_applied"]:
        raise RuntimeError("historical 14B wrapper was not normalized")
    pass_through = {}
    for key in ("qwen25_32b_write", "qwen25_32b_clarification"):
        evidence, _ = normalize_and_parse(key)
        if evidence["transformation_applied"] or evidence["raw_sha256"] != evidence["normalized_sha256"]:
            raise RuntimeError(f"{key}: BARE_RESPONSE_NOT_IDENTITY")
        pass_through[key] = evidence
    replay = replay_write(write_request)
    if (
        replay["executor_result"] != "PATCH_REJECTED"
        or replay["candidate_identity"] is not None
        or not replay["source_snapshot_preserved"]
    ):
        raise RuntimeError("historical 14B executor replay changed disposition")
    result = {
        "adapter_mode": "NORMALIZATION_CANDIDATE",
        "historical_14b_write": {**write, **replay},
        "historical_14b_clarification": {
            **clarification,
            "semantic_judgment": "NO_CHANGE",
            "disposition": "PRESENTATION_NORMALIZATION_DOES_NOT_FIX_CLARIFICATION_JUDGMENT",
        },
        "preserved_32b_pass_through": pass_through,
        "model_inference_count": 0,
        "status": "FENCE_NORMALIZATION_JUSTIFIED",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
