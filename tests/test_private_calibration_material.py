"""Current calibration projections exclude evaluator-private answer material."""

from __future__ import annotations

import hashlib
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = Path("/home/louis/.local/share/ws-code-agent/alpha-private")
MANIFEST = REPOSITORY_ROOT / "benchmarks/alpha-calibration/PRIVATE_MATERIAL.md"


class PrivateCalibrationMaterialTests(unittest.TestCase):
    def test_private_artifacts_are_external_and_match_non_secret_manifest(self) -> None:
        self.assertTrue(PRIVATE_ROOT.is_dir())
        self.assertNotIn(REPOSITORY_ROOT.resolve(), PRIVATE_ROOT.resolve().parents)
        manifest = MANIFEST.read_text(encoding="utf-8")
        for artifact in (
            "C01-oracle.py",
            "CALIBRATION_REVIEW.md",
            "C03-evaluator-notes.md",
            "C04-evaluator-notes.md",
            "C05-evaluator-notes.md",
        ):
            content = (PRIVATE_ROOT / artifact).read_bytes()
            self.assertIn(hashlib.sha256(content).hexdigest(), manifest)

    def test_tracked_projection_has_no_private_oracle_or_case_answer_sections(self) -> None:
        calibration = REPOSITORY_ROOT / "benchmarks/alpha-calibration"
        self.assertFalse(any((calibration / "oracles").rglob("*.py")))
        self.assertFalse((calibration / "CALIBRATION_REVIEW.md").exists())
        for case in ("C01-simple-patch", "C02-clarification", "C03-dirty-tree", "C04-stale-state", "C05-boundary-variant"):
            content = (calibration / "cases" / case / "CASE.md").read_text(encoding="utf-8").lower()
            self.assertNotIn("## intended disposition", content)
            self.assertNotIn("## evaluator answer key", content)


if __name__ == "__main__":
    unittest.main()
