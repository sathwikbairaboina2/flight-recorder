import sqlite3

import pytest

from flight_recorder.samples import USER_ASK, make_sample_db, search_flights


def _counts(db) -> dict[str, int]:
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT thread_id, COUNT(*) FROM checkpoints GROUP BY thread_id").fetchall()
    return dict(rows)


def test_sample_threads(sample_db):
    assert _counts(sample_db) == {"lisbon-bug": 5, "lisbon-branched": 7}


def test_long_thread_has_exact_count(tmp_path):
    db = make_sample_db(tmp_path / "c.sqlite", long_checkpoints=40)
    assert _counts(db)["long-40"] == 40


def test_long_thread_rejects_tiny_counts(tmp_path):
    with pytest.raises(ValueError):
        make_sample_db(tmp_path / "c.sqlite", long_checkpoints=2)


def test_the_bug_and_the_fix():
    assert "2026-11-01" in USER_ASK
    assert search_flights("Lisbon", None)[0]["date"] == "2026-10-28"
    assert search_flights("Lisbon", "2026-11-01")[0]["flight"] == "TP1363"


def test_regenerating_replaces_the_file(sample_db):
    make_sample_db(sample_db)
    assert _counts(sample_db) == {"lisbon-bug": 5, "lisbon-branched": 7}


def test_generating_samples_logs_no_unregistered_type_warning(tmp_path, caplog, monkeypatch):
    from langgraph.checkpoint.serde import jsonplus

    monkeypatch.setattr(jsonplus, "_warned_unregistered_types", set())  # LangGraph warns once per process
    with caplog.at_level("WARNING"):
        make_sample_db(tmp_path / "s.sqlite")
    assert "unregistered type" not in caplog.text
