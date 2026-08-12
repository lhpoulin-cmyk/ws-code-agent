"""Prevent live coding-agent surfaces from regaining inherited runtime identity."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.live_tree_hygiene import (  # noqa: E402
    PILOT_MANIFEST,
    hygiene_violations,
    publication_paths,
    publication_tree_violations,
)


class LiveTreeHygieneTests(unittest.TestCase):
    def test_active_tracked_tree_excludes_inherited_doc_writer_runtime_identity(self) -> None:
        self.assertEqual((), publication_tree_violations(ROOT))

    def test_explicit_external_pilot_target_passes_but_runtime_inheritance_fails(self) -> None:
        self.assertEqual((), hygiene_violations(ROOT, PILOT_MANIFEST))
        source = json.loads((ROOT / PILOT_MANIFEST).read_text(encoding="utf-8"))
        external_identity = "ws-" + "doc" + "-writer"
        source["model_binding"]["runtime_backend"] = external_identity
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / PILOT_MANIFEST
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(source), encoding="utf-8")
            self.assertEqual((PILOT_MANIFEST,), hygiene_violations(root, PILOT_MANIFEST))

    def test_runtime_provider_executor_and_import_controls_remain_forbidden(self) -> None:
        external_identity = "ws-" + "doc" + "-writer"
        inherited_identity = "doc" + "writer"
        controls = (
            f'RUNTIME_BACKEND = "{external_identity}"',
            f'MODEL_PROVIDER = "{external_identity}"',
            f'EXECUTOR_DEPENDENCY = "{external_identity}"',
            f'PRODUCTION_WORKER_AUTHORITY = "{external_identity}"',
            f'import {inherited_identity}',
            f'INHERITED_APPLICATION_IMPLEMENTATION = "{inherited_identity}"',
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, control in enumerate(controls):
                relative = f"src/control_{index}.py"
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(control, encoding="utf-8")
                self.assertEqual((relative,), hygiene_violations(root, relative))

    def test_prepublication_tree_includes_untracked_candidate_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            tracked = root / "tracked.txt"
            tracked.write_text("bounded coding authority\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
            candidate = root / "candidate.txt"
            inherited_identity = "doc" + "writer"
            candidate.write_text(f'RUNTIME_BACKEND = "{inherited_identity}"\n', encoding="utf-8")
            self.assertIn("candidate.txt", publication_paths(root))
            self.assertEqual(("candidate.txt",), publication_tree_violations(root))


if __name__ == "__main__":
    unittest.main()
