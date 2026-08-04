import sqlite3

from docwriter_web.recovery_guidance import guidance_for
from test_web_app import app


def test_reconciliation_schema_is_additive_and_immutable(tmp_path):
    app(tmp_path)
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        columns = [row[1] for row in db.execute("PRAGMA table_info(generation_attempt_reconciliations)")]
        assert columns[:6] == ["reconciliation_id", "trial_id", "adaptation_id", "profile_id", "baseline_id", "original_attempt_id"]
        trigger_names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'generation_attempt_reconciliations_%'")}
        assert trigger_names == {
            "generation_attempt_reconciliations_no_update",
            "generation_attempt_reconciliations_no_delete",
            "generation_attempt_reconciliations_validate_insert",
        }
        assert db.execute("SELECT count(*) FROM generation_attempt_reconciliations").fetchone()[0] == 0


def test_reconciliation_immutability_triggers_are_database_owned(tmp_path):
    app(tmp_path)
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        sql = " ".join(row[0] for row in db.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'generation_attempt_reconciliations_no_%'"))
        assert "BEFORE UPDATE" in sql and "BEFORE DELETE" in sql and "immutable" in sql


def test_reconciled_failure_guidance_points_to_corrected_attempt_and_comparison():
    guidance = guidance_for(
        {"trial_id": "trial-x", "lifecycle_state": "ACTIVE", "review_status": "REVIEW_REQUIRED"},
        [{"kind": "AUDIENCE", "status": "RESPONSE_SCHEMA_INVALID", "canonical_failure_class": "RESPONSE_SCHEMA_INVALID", "attempt_id": "generation-v1", "reconciliation_id": "reconciliation-x", "replacement_attempt_id": "generation-v2"}],
    )
    assert guidance.guidance_id == "AUDIENCE_FAILURE_RECONCILED"
    assert guidance.primary_action_url.endswith("/attempt/generation-v2")
    assert guidance.secondary_action_url.endswith("/audience-reconciliation/reconciliation-x")
    assert "user" not in (guidance.title + guidance.explanation).lower()
