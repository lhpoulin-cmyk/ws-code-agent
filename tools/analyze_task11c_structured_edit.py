#!/usr/bin/env python3
"""Run Task 11C retrospective controls without model inference."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tools.analyze_task11b_patch_forensics import EVIDENCE, STORE, inspect_evidence  # noqa: E402
from ws_code_agent.contained_validation import SystemdContainedValidationRunner  # noqa: E402
from ws_code_agent.disposition_harness import parse_request  # noqa: E402
from ws_code_agent.readonly_executor import CompareStatus, ReadOnlyExecutor  # noqa: E402
from ws_code_agent.request_protocol import STRUCTURED_EDIT_PROTOCOL  # noqa: E402
from ws_code_agent.response_normalization import normalize_single_markdown_json_fence  # noqa: E402
from ws_code_agent.structured_edit import (  # noqa: E402
    StructuredTextReplacement,
    StructuredTextReplacementExecutor,
    TextReplacementStatus,
)
from ws_code_agent.supervised_validation import WRITE_VALIDATION_IDS, validation_registry  # noqa: E402
from ws_code_agent.supervised_work import _initialize_task11a_fixture  # noqa: E402
from ws_code_agent.validation import DescriptorValidationExecutor, ValidationStatus  # noqa: E402


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def historical_request(spec: dict[str, object]) -> tuple[bytes, object]:
    turn = (
        STORE
        / str(spec["session"])
        / "cases"
        / "WORK"
        / "turns"
        / f"{int(spec['turn']):04d}"
    )
    raw = (turn / "raw-response.txt").read_bytes()
    normalized_path = turn / "normalized-parser-input.txt"
    normalized = (
        normalized_path.read_bytes()
        if normalized_path.exists()
        else normalize_single_markdown_json_fence(raw).normalized_parser_input
    )
    return raw, parse_request(normalized.decode("utf-8"))


def structured_task11a_control(
    spec: dict[str, object], structure: dict[str, object], workspace: Path
) -> dict[str, object]:
    hunk = structure["hunks"][0]
    removed = hunk["removed_lines"]
    added = hunk["added_lines"]
    if tuple(removed) != ('    return "hi"',) or tuple(added) != ('    return "hello"',):
        return {
            "classification": "SEMANTIC_EXTRACTION_NOT_UNIQUE",
            "reason": "preserved patch does not select exactly one old and new semantic line",
        }

    # Task 11B established that the omitted terminal LF was transport damage.
    # The semantic selection is the exact current source line and its exact
    # replacement while retaining the source line boundary.
    old_text = removed[0] + "\n"
    new_text = added[0] + "\n"
    repository, _objective, _reads, allowed_paths, fixture_id = _initialize_task11a_fixture(
        workspace, f"task11c-{int(spec['turn'])}"
    )
    observer = ReadOnlyExecutor()
    source = observer.observe_repository(repository).snapshot
    source_identity = source.snapshot_identity
    request_document = json.dumps(
        {
            "request_type": "PROPOSE_TEXT_REPLACEMENT",
            "arguments": {
                "path": "src/message.py",
                "old_text": old_text,
                "new_text": new_text,
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    parsed = parse_request(request_document, protocol=STRUCTURED_EDIT_PROTOCOL)
    proposal = StructuredTextReplacement.create(
        source,
        raw_request_sha256=sha256(request_document.encode("utf-8")),
        **parsed.arguments,
    )
    executor = StructuredTextReplacementExecutor(observer)
    context = executor.build_isolated_copy(source)
    try:
        result = executor.apply_text_replacement_isolated(context, proposal, allowed_paths)
        if result.status is not TextReplacementStatus.STRUCTURED_EDIT_ACCEPTED:
            return {
                "classification": "STRUCTURED_REPLAY_MATCH_FAILED",
                "fixture_id": fixture_id,
                "structured_request_identity": proposal.structured_request_sha256,
                "match_count": result.exact_match_count,
                "executor_result": result.status.value,
            }
        validator = DescriptorValidationExecutor(
            validation_registry(), observer, SystemdContainedValidationRunner()
        )
        validations = [
            validator.run_validation(
                context, result.result_snapshot, descriptor_id, WRITE_VALIDATION_IDS
            )
            for descriptor_id in WRITE_VALIDATION_IDS
        ]
        if observer.compare_snapshot(source).status is not CompareStatus.MATCH:
            raise RuntimeError("Task 11C control changed the authoritative fixture")
        if observer.observe_repository(context.isolated_root).snapshot.snapshot_identity != result.result_snapshot.snapshot_identity:
            raise RuntimeError("Task 11C validation changed the candidate")
        return {
            "classification": "STRUCTURED_REPLAY_APPLIES",
            "fixture_id": fixture_id,
            "source_snapshot_identity": source_identity,
            "semantic_extraction": {
                "path": "exact proposed_paths value",
                "old_text": "exact removed line plus source-retained LF",
                "new_text": "exact added line plus source-retained LF",
                "historical_patch_sha256": spec["patch"],
            },
            "structured_request_identity": proposal.structured_request_sha256,
            "structured_request_sha256": proposal.structured_request_sha256,
            "old_text_sha256": proposal.old_text_sha256,
            "new_text_sha256": proposal.new_text_sha256,
            "match_count": result.exact_match_count,
            "executor_result": result.status.value,
            "candidate_identity": result.candidate_identity,
            "candidate_snapshot_identity": result.result_snapshot.snapshot_identity,
            "changed_paths": list(result.actual_changed_paths),
            "before_file_sha256": result.before_file_sha256,
            "after_file_sha256": result.after_file_sha256,
            "canonical_diff_sha256": result.canonical_diff_sha256,
            "canonical_diff_origin": result.fact.observed_result["canonical_diff_origin"],
            "resulting_source_sha256": sha256(
                (Path(context.isolated_root) / "src/message.py").read_bytes()
            ),
            "visible_validation": validations[0].status.value,
            "hidden_validation": validations[1].status.value,
            "technical_correctness": (
                "VALIDATED"
                if all(run.status is ValidationStatus.VALIDATION_PASS for run in validations)
                else "FAILED"
            ),
            "containment_profiles": [
                run.containment_evidence["CONTAINMENT_PROFILE"] for run in validations
            ],
            "source_snapshot_preserved": "MATCH",
            "validator_effect": "UNCHANGED",
        }
    finally:
        executor.cleanup(context)


def main() -> int:
    controls: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="task11c-retrospective-") as temporary:
        workspace = Path(temporary)
        for spec_value in EVIDENCE:
            spec = dict(spec_value)
            if not str(spec["experiment"]).startswith("TASK10") and spec["experiment"] != "TASK11A_14B_WRITE":
                continue
            if spec["experiment"] == "TASK10V_32B_WRITE":
                continue
            bound = inspect_evidence(spec)
            raw, request = historical_request(spec)
            base = {
                "experiment": spec["experiment"],
                "session": spec["session"],
                "turn": spec["turn"],
                "historical_raw_sha256": sha256(raw),
                "historical_patch_sha256": spec["patch"],
                "semantic_classification": bound["semantic_classification"],
                "semantic_extraction_source": "exact parsed historical PROPOSE_PATCH hunk",
                "model_selected_path": request.arguments["proposed_paths"][0],
            }
            if spec["fixture"] == "new":
                base.update({
                    "classification": "STRUCTURED_REPLAY_MATCH_FAILED",
                    "reason": "V3 is existing-file replacement only; the historical target is absent and supplies no old_text",
                    "structured_request_identity": None,
                    "match_count": 0,
                    "candidate_result": "NONE",
                    "changed_paths": [],
                    "visible_validation": "NOT_EVALUATED",
                    "hidden_validation": "NOT_EVALUATED",
                })
            else:
                base.update(structured_task11a_control(spec, bound["structure"], workspace))
            controls.append(base)

    task11a = [
        item for item in controls
        if item["experiment"] == "TASK11A_14B_WRITE"
    ]
    if not task11a or any(
        item.get("classification") != "STRUCTURED_REPLAY_APPLIES"
        or item.get("visible_validation") != "VALIDATION_PASS"
        or item.get("hidden_validation") != "VALIDATION_PASS"
        for item in task11a
    ):
        raise RuntimeError("Task 11A semantic control did not validate")
    print(json.dumps({
        "checkpoint": "TASK11C-DESIGN-DETERMINISTIC-STRUCTURED-EDIT-TRANSPORT",
        "evidence_binding": "PASS",
        "retrospective_controls": controls,
        "task11a_control": "STRUCTURED_REPLAY_APPLIES",
        "model_inference_count": 0,
        "historical_dispositions_changed": False,
        "live_protocol_changed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
