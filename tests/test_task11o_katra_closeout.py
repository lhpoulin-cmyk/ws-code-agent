"""Task 11O closes Katra characterization without changing frozen authority."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.production_envelope import PROTOCOL_RENDER_SHA256  # noqa: E402


class Task11OKatraCloseoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = yaml.safe_load(
            (ROOT / "docs/work/katra-ws-code-agent-characterization-closeout-v1.yaml")
            .read_text(encoding="utf-8")
        )

    def test_closeout_status_is_exact_and_matrix_is_not_started(self) -> None:
        status = self.record["status"]
        self.assertEqual("COMPLETE", status["katra_characterization"])
        self.assertEqual("RETIRED_AFTER_TASK11N", status["katra_ws_code_agent_execution"])
        self.assertEqual("FROZEN", status["katra_benchmark_baseline"])
        self.assertEqual("CONTINUES", status["ws_doc_writer_on_cuda_compute"])
        self.assertEqual("HV_MATRIX_VM320", status["next_ws_code_agent_platform"])
        self.assertEqual("NOT_STARTED", status["matrix_migration"])
        self.assertEqual(0, status["model_inference_count"])
        self.assertEqual("BELAYED", self.record["matrix_handoff"]["action_in_task11o"])

    def test_frozen_envelope_and_historical_dispositions_are_not_rescored(self) -> None:
        self.assertEqual(
            "INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1",
            self.record["production"]["envelope"],
        )
        self.assertEqual("FROZEN", self.record["production"]["envelope_status"])
        self.assertEqual("NOT_YET_GRANTED", self.record["production"]["general_production_use"])
        self.assertEqual(
            "d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993",
            PROTOCOL_RENDER_SHA256,
        )
        history = self.record["historical_dispositions"]
        self.assertEqual(
            "FIRST_REAL_LOCAL_REPOSITORY_INTERACTIVE_PILOT_ESCALATED",
            history["task11l"]["disposition"],
        )
        self.assertEqual("VALIDATION_FAILED", history["task11l"]["reason"])
        self.assertEqual("DISTINCT_REAL_MIDFILE_INTERACTIVE_PILOT_PASS", history["task11m"])
        self.assertEqual(
            "DISTINCT_REAL_CODE_INTERACTIVE_PILOT_ESCALATED",
            history["task11n"]["disposition"],
        )
        self.assertEqual("VALIDATION_FAILED", history["task11n"]["reason"])

    def test_sessions_and_candidates_are_retired_without_evidence_deletion(self) -> None:
        retirement = self.record["retirement"]
        self.assertEqual("CLOSED_HISTORICAL", retirement["state"])
        self.assertFalse(retirement["raw_session_state_rewritten"])
        self.assertEqual("PRESERVE", retirement["canonical_store_action"])
        self.assertEqual(23, len(retirement["sessions"]))
        self.assertEqual(6, len(retirement["candidates"]))
        self.assertTrue(
            all(value == "HISTORICAL_EVIDENCE_NOT_PROMOTED" for value in retirement["candidates"].values())
        )

    def test_baseline_and_handoff_are_durable_and_non_executing(self) -> None:
        baseline = (
            ROOT / "docs/baselines/rtx-5070-ti-katra-ws-code-agent-baseline-v1.md"
        ).read_text(encoding="utf-8")
        self.assertIn("RTX_5070_TI_KATRA_WS_CODE_AGENT_BASELINE_V1", baseline)
        self.assertIn("70.41–75.11 tokens/second", baseline)
        self.assertIn("71% GPU / 29% CPU", baseline)
        handoff = (
            ROOT / "docs/handoffs/hv-matrix-vm320-ws-code-agent-comparison.md"
        ).read_text(encoding="utf-8")
        self.assertIn("MIGRATION_NOT_STARTED", handoff)
        self.assertIn("new VM 320", handoff)
        self.assertIn("No VM, host, GPU, service, repository, network, storage, or runtime mutation", handoff)


if __name__ == "__main__":
    unittest.main()
