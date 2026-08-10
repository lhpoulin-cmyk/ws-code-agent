"""Prevent live coding-agent surfaces from regaining inherited runtime identity."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_RECORDS = {"docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md"}
FORBIDDEN = ("docwriter", "/srv/ws-doc-writer")


class LiveTreeHygieneTests(unittest.TestCase):
    def test_active_tracked_tree_excludes_inherited_doc_writer_runtime_identity(self) -> None:
        paths = subprocess.check_output(["git", "-C", str(ROOT), "ls-files"], text=True).splitlines()
        for relative in paths:
            if relative.startswith("lineage/") or relative in HISTORICAL_RECORDS:
                continue
            content = (ROOT / relative).read_text(encoding="utf-8", errors="replace").lower()
            for marker in FORBIDDEN:
                self.assertNotIn(marker, content, relative)


if __name__ == "__main__":
    unittest.main()
