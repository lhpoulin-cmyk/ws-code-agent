from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.production_envelope import (  # noqa: E402
    ENVELOPE_ID,
    ENVELOPE_STATUS,
    PROTOCOL_RENDER_SHA256,
    TASK11J_PILOT_INSTANCE_ID,
    TASK11J_README_SHA256,
    TASK11J_TARGET_BRANCH,
    TASK11J_TARGET_HEAD,
    TASK11J_TARGET_ORIGIN,
    TASK11J_TARGET_PATH,
    TASK11L_PILOT_INSTANCE_ID,
    task11j_pilot_instance,
    task11l_pilot_instance,
)
from ws_code_agent.request_protocol import STRUCTURED_EDIT_PROTOCOL  # noqa: E402
from ws_code_agent.supervised_validation import (  # noqa: E402
    TASK11J_HIDDEN_SOURCE,
    TASK11J_VALIDATION_IDS,
    TASK11J_VISIBLE_SOURCE,
    bind_validation_ids,
    bound_descriptor_ids_by_role,
)


ORIGINAL = (
    "# Application boundary\n\n"
    "Implementation is intentionally absent in the foundation phase. Future code\n"
    "may normalize sources, invoke approved model adapters, validate candidates, and\n"
    "export accepted documents. It must not execute infrastructure commands.\n"
)
EXPECTED = (
    "# Application boundary\n\n"
    "The `src/docwriter_web` package contains the Doc Writer application\n"
    "implementation. It must not execute infrastructure commands.\n"
)


class Task11JRealRepositoryPilotTests(unittest.TestCase):
    def test_durable_instance_binds_exact_selected_source_and_envelope(self):
        instance = task11j_pilot_instance(ROOT)
        self.assertEqual(TASK11J_PILOT_INSTANCE_ID, instance["pilot_instance_id"])
        source = instance["source_binding"]
        self.assertEqual((TASK11J_TARGET_PATH, TASK11J_TARGET_ORIGIN, TASK11J_TARGET_BRANCH), (
            source["canonical_path"], source["origin"], source["branch"],
        ))
        pilot = instance["pilot_manifest"]
        self.assertEqual(TASK11J_TARGET_HEAD, pilot["repository"]["head"])
        self.assertEqual(["src/README.md"], pilot["read_scopes"])
        self.assertEqual(["src/README.md"], pilot["patch_paths"])
        self.assertEqual(ENVELOPE_ID, pilot["worker_envelope_id"])
        self.assertEqual(PROTOCOL_RENDER_SHA256, pilot["protocol"]["render_sha256"])
        self.assertEqual("COMPLETE", instance["validation_result"]["manifest_status"])

    def test_protocol_and_model_visible_objective_do_not_expose_old_text(self):
        instance = task11j_pilot_instance(ROOT)
        objective = instance["pilot_manifest"]["objective"]
        self.assertNotIn("Implementation is intentionally absent", objective)
        self.assertNotIn("Future code", objective)
        self.assertEqual(PROTOCOL_RENDER_SHA256, hashlib.sha256(
            STRUCTURED_EDIT_PROTOCOL.render().encode()
        ).hexdigest())
        self.assertNotIn("Implementation is intentionally absent", STRUCTURED_EDIT_PROTOCOL.render())

    def test_registry_binds_independent_contained_task11j_descriptors(self):
        contract = bind_validation_ids(TASK11J_VALIDATION_IDS)
        self.assertEqual(list(TASK11J_VALIDATION_IDS), contract["authorized_validation_ids"])
        visible, hidden = contract["descriptors"]
        self.assertEqual(("VISIBLE", "HIDDEN_ORACLE"), (visible["role"], hidden["role"]))
        self.assertNotEqual(visible["source_sha256"], hidden["source_sha256"])
        for descriptor in contract["descriptors"]:
            self.assertTrue(descriptor["containment_required"])
            self.assertFalse(descriptor["repository_writes_allowed"])
            self.assertTrue(descriptor["model_visible_by_id_only"])

    def test_validator_contract_accepts_only_the_exact_single_path_result(self):
        cases = (
            (EXPECTED, False, 0),
            (ORIGINAL, False, 1),
            (EXPECTED.replace("src/docwriter_web", "src/doc_writer"), False, 1),
            (EXPECTED.replace(" It must not execute infrastructure commands.", ""), False, 1),
            (EXPECTED + "\nUnrelated.\n", False, 1),
            (EXPECTED.replace("# Application boundary", "# Boundary"), False, 1),
            (EXPECTED + "Future code remains pending.\n", False, 1),
            (EXPECTED, True, 1),
        )
        for source, second_change, expected_code in cases:
            with self.subTest(source=source, second_change=second_change):
                with tempfile.TemporaryDirectory() as temporary:
                    repository = Path(temporary)
                    (repository / "src").mkdir()
                    (repository / "src/README.md").write_text(ORIGINAL, encoding="utf-8")
                    (repository / "README.md").write_text("# Doc Writer\n", encoding="utf-8")
                    subprocess.run(["git", "-C", temporary, "init", "-q"], check=True)
                    subprocess.run(["git", "-C", temporary, "add", "."], check=True)
                    subprocess.run([
                        "git", "-C", temporary, "-c", "user.name=Test", "-c",
                        "user.email=test@example.invalid", "commit", "-qm", "source",
                    ], check=True)
                    (repository / "src/README.md").write_text(source, encoding="utf-8")
                    if second_change:
                        (repository / "README.md").write_text("# Changed\n", encoding="utf-8")
                    for asset in (TASK11J_VISIBLE_SOURCE, TASK11J_HIDDEN_SOURCE):
                        process = subprocess.run(
                            [sys.executable, "-B", str(asset)], cwd=repository,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                        )
                        self.assertEqual(expected_code, process.returncode, (asset, process.stderr))

    def test_selector_is_explicit_and_historical_default_is_unchanged(self):
        cli = (ROOT / "tools/run_supervised_work.py").read_text(encoding="utf-8")
        controller = (ROOT / "src/ws_code_agent/supervised_work.py").read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("start-task11j-real-local-pilot")', cli)
        self.assertIn("start_task11j_real_repository_pilot", cli)
        self.assertIn("TASK11J_REAL_REPOSITORY_SESSION_KIND", controller)
        self.assertIn('"live_default": False', controller)
        self.assertEqual(ENVELOPE_STATUS, "FROZEN")

    def test_task11l_is_a_fresh_exact_instance_with_unchanged_objective_and_validators(self):
        task11j = task11j_pilot_instance(ROOT)
        task11l = task11l_pilot_instance(ROOT)
        self.assertEqual(TASK11L_PILOT_INSTANCE_ID, task11l["pilot_instance_id"])
        self.assertNotEqual(task11j["pilot_instance_id"], task11l["pilot_instance_id"])
        self.assertEqual(task11j["source_binding"], task11l["source_binding"])
        self.assertEqual(task11j["model_binding"], task11l["model_binding"])
        self.assertEqual(
            task11j["pilot_manifest"]["objective"],
            task11l["pilot_manifest"]["objective"],
        )
        self.assertEqual(
            task11j["pilot_manifest"]["validation"],
            task11l["pilot_manifest"]["validation"],
        )
        self.assertEqual("COMPLETE", task11l["validation_result"]["manifest_status"])

    def test_task11l_session_contract_resolves_only_the_exact_task11j_validators(self):
        contract = task11l_pilot_instance(ROOT)["pilot_manifest"]["validation"]
        roles = bound_descriptor_ids_by_role(contract)
        self.assertEqual(
            {
                "VISIBLE": "task11j-ws-doc-writer-src-readme-visible-v1",
                "HIDDEN_ORACLE": "task11j-ws-doc-writer-src-readme-hidden-v1",
            },
            {role.value: descriptor_id for role, descriptor_id in roles.items()},
        )
        self.assertNotIn("task10k-c-write-visible-v1", roles.values())

    def test_task11l_selector_is_explicit_and_does_not_replace_task11j(self):
        cli = (ROOT / "tools/run_supervised_work.py").read_text(encoding="utf-8")
        controller = (ROOT / "src/ws_code_agent/supervised_work.py").read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("start-task11j-real-local-pilot")', cli)
        self.assertIn('sub.add_parser("start-task11l-real-local-pilot")', cli)
        self.assertIn("start_task11j_real_repository_pilot", controller)
        self.assertIn("start_task11l_real_repository_pilot", controller)


if __name__ == "__main__":
    unittest.main()
