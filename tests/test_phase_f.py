import sqlite3
import pytest

from docwriter_web.audience import derived_state, profile_contract
from test_generation import make_app


def test_three_seeded_profiles_are_repository_owned(tmp_path):
    make_app(tmp_path)
    with sqlite3.connect(tmp_path / "state" / "docwriter.sqlite3") as db:
        rows = db.execute("select slug,contract_version,active,contract_sha256 from audience_profiles order by slug").fetchall()
    assert [row[0] for row in rows] == ["executive", "public", "technical-peer"]
    assert all(row[1] == "audience-adaptation-v1" and row[2] == 1 and len(row[3]) == 64 for row in rows)


def test_audience_states_are_independent():
    assert derived_state({}, [], []) == "AUDIENCE_GENERATION_REQUIRED"
    assert derived_state({}, [{"status": "RUNNING", "started_at": "1", "attempt_id": "a"}], []) == "AUDIENCE_GENERATION_RUNNING"
    assert derived_state({}, [{"status": "COMPLETED", "started_at": "1", "attempt_id": "a", "normalized_proposal": "x"}], []) == "AUDIENCE_REVIEW_TARGET_REQUIRED"


def test_unknown_profile_contract_fails_closed():
    with pytest.raises(ValueError): profile_contract("unknown")
