from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.readonly_executor import ReadOnlyExecutor  # noqa: E402
from ws_code_agent.source_grounding import (  # noqa: E402
    POLICY_ID,
    SOURCE_GROUNDED,
    SOURCE_GROUNDING_NONCOMPLIANCE,
    SOURCE_READ_REQUIRED,
    grounded_paths_from_turns,
    record_successful_read,
    replay_precondition,
    valid_read_evidence,
)


class SourceGroundingTests(unittest.TestCase):
    def repository(self, root: Path):
        repository = root / "repository"
        (repository / "src").mkdir(parents=True)
        (repository / "src/message.py").write_text(
            'def message():\n    return "hi"\n', encoding="utf-8"
        )
        (repository / "src/other.py").write_text("OTHER = True\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repository), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(repository), "add", "src/message.py", "src/other.py"], check=True)
        environment = dict(os.environ)
        environment.update({
            "GIT_AUTHOR_NAME": "Task11E",
            "GIT_AUTHOR_EMAIL": "task11e@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
            "GIT_COMMITTER_NAME": "Task11E",
            "GIT_COMMITTER_EMAIL": "task11e@example.invalid",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
        })
        subprocess.run(
            ["git", "-C", str(repository), "commit", "-qm", "fixture"],
            check=True,
            env=environment,
        )
        observer = ReadOnlyExecutor()
        snapshot = observer.observe_repository(repository).snapshot
        return observer, snapshot

    def test_real_executor_read_records_complete_path_and_snapshot_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            observer, snapshot = self.repository(Path(temporary))
            evidence = record_successful_read(
                observer.read_file(snapshot, "src/message.py"), snapshot, turn=1
            )
            self.assertEqual(POLICY_ID, evidence["policy_id"])
            self.assertEqual(SOURCE_GROUNDED, evidence["status"])
            self.assertTrue(valid_read_evidence(
                evidence,
                path="src/message.py",
                source_snapshot_identity=snapshot.snapshot_identity,
                before_turn=2,
            ))
            self.assertFalse(valid_read_evidence(
                evidence,
                path="src/other.py",
                source_snapshot_identity=snapshot.snapshot_identity,
                before_turn=2,
            ))
            self.assertFalse(valid_read_evidence(
                evidence,
                path="src/message.py",
                source_snapshot_identity="0" * 64,
                before_turn=2,
            ))

    def test_only_evaluator_read_evidence_grounds_not_search_parent_or_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            observer, snapshot = self.repository(Path(temporary))
            evidence = record_successful_read(
                observer.read_file(snapshot, "src/message.py"), snapshot, turn=1
            )
            model_claim = {
                "request_type": "NO_CHANGE",
                "projection": {"summary": "I already read src/message.py"},
                "evaluator_evidence": {"source_grounding_read": evidence},
            }
            search = {"request_type": "SEARCH", "parsed_arguments": {"scope": "src"}}
            parent = {
                "request_type": "READ",
                "parsed_arguments": {"path": "src"},
                "evaluator_evidence": {"source_grounding_read": {**evidence, "path": "src"}},
            }
            grounded = grounded_paths_from_turns(
                [model_claim, search, parent],
                source_snapshot_identity=snapshot.snapshot_identity,
                before_turn=4,
            )
            self.assertEqual({}, grounded)

    def test_successful_read_of_other_file_does_not_ground_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            observer, snapshot = self.repository(Path(temporary))
            evidence = record_successful_read(
                observer.read_file(snapshot, "src/other.py"), snapshot, turn=1
            )
            replay = replay_precondition([
                {
                    "request_type": "READ",
                    "validation_outcome": "VALID",
                    "parsed_arguments": {"path": "src/other.py"},
                    "authority_outcome": "AUTHORIZED",
                    "executor_operation": "READ_FILE",
                    "projection": {"status": "OK", "path": "src/other.py"},
                    "evaluator_evidence": {"source_grounding_read": evidence},
                },
                {
                    "request_type": "PROPOSE_TEXT_REPLACEMENT",
                    "parsed_arguments": {"path": "src/message.py"},
                },
            ], source_snapshot_identity=snapshot.snapshot_identity)
            self.assertEqual(SOURCE_READ_REQUIRED, replay["events"][1]["result"])

    def test_prior_session_shape_and_old_snapshot_are_not_rebound(self):
        with tempfile.TemporaryDirectory() as temporary:
            observer, snapshot = self.repository(Path(temporary))
            evidence = record_successful_read(
                observer.read_file(snapshot, "src/message.py"), snapshot, turn=1
            )
            prior_session_turn = {
                "evaluator_evidence": {"source_grounding_read": evidence},
            }
            self.assertEqual({}, grounded_paths_from_turns(
                [],
                source_snapshot_identity=snapshot.snapshot_identity,
                before_turn=2,
            ))
            self.assertEqual({}, grounded_paths_from_turns(
                [prior_session_turn],
                source_snapshot_identity="f" * 64,
                before_turn=2,
            ))

    def test_replay_separates_grounded_and_repeated_ungrounded_sequences(self):
        with tempfile.TemporaryDirectory() as temporary:
            observer, snapshot = self.repository(Path(temporary))
            evidence = record_successful_read(
                observer.read_file(snapshot, "src/message.py"), snapshot, turn=1
            )
            grounded = replay_precondition([
                {
                    "request_type": "READ",
                    "validation_outcome": "VALID",
                    "parsed_arguments": {"path": "src/message.py"},
                    "authority_outcome": "AUTHORIZED",
                    "executor_operation": "READ_FILE",
                    "projection": {"status": "OK", "path": "src/message.py"},
                    "evaluator_evidence": {"source_grounding_read": evidence},
                },
                {
                    "request_type": "PROPOSE_TEXT_REPLACEMENT",
                    "parsed_arguments": {"path": "src/message.py"},
                },
            ], source_snapshot_identity=snapshot.snapshot_identity)
            self.assertEqual("PRECONDITION_PASS", grounded["events"][1]["result"])
            self.assertEqual("CONTINUE", grounded["disposition"])

            ungrounded = replay_precondition([
                {
                    "request_type": "PROPOSE_TEXT_REPLACEMENT",
                    "parsed_arguments": {"path": "src/message.py"},
                },
                {
                    "request_type": "PROPOSE_TEXT_REPLACEMENT",
                    "parsed_arguments": {"path": "src/message.py"},
                },
            ], source_snapshot_identity=snapshot.snapshot_identity)
            self.assertEqual(
                [SOURCE_READ_REQUIRED, SOURCE_READ_REQUIRED],
                [event["result"] for event in ungrounded["events"]],
            )
            self.assertEqual(SOURCE_GROUNDING_NONCOMPLIANCE, ungrounded["classification"])
            self.assertEqual("ESCALATION_REQUIRED", ungrounded["disposition"])


if __name__ == "__main__":
    unittest.main()
