import sqlite3

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
