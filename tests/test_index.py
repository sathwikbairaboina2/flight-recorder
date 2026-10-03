"""Invariant 6: the index's parent links and next nodes equal LangGraph's own history."""

import datetime as dt
import sqlite3

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

from flight_recorder.index import SchemaError, check_schema, list_checkpoints, list_threads, uuid6_time
from flight_recorder.samples import build


def _history(db, thread_id):
    conn = sqlite3.connect(db, check_same_thread=False)
    app = build().compile(checkpointer=SqliteSaver(conn))
    out = {}
    for s in app.get_state_history({"configurable": {"thread_id": thread_id}}):
        parent = (s.parent_config or {}).get("configurable", {}).get("checkpoint_id")
        out[s.config["configurable"]["checkpoint_id"]] = (parent, sorted(s.next), s.created_at)
    conn.close()
    return out


@pytest.mark.parametrize("thread_id", ["lisbon-bug", "lisbon-branched"])
def test_parent_links_match_state_history(sample_db, thread_id):
    truth = _history(sample_db, thread_id)
    with sqlite3.connect(sample_db) as conn:
        rows = list_checkpoints(conn, thread_id)
    assert len(rows) == len(truth)
    for r in rows:
        parent, nxt, created = truth[r["checkpoint_id"]]
        assert r["parent_id"] == parent
        assert r["next"] == nxt
        gap = abs(dt.datetime.fromisoformat(r["created_at"]) - dt.datetime.fromisoformat(created))
        assert gap < dt.timedelta(milliseconds=5)


def test_rows_are_oldest_first_with_writers(sample_db):
    with sqlite3.connect(sample_db) as conn:
        rows = list_checkpoints(conn, "lisbon-bug")
    assert [r["step"] for r in rows] == [-1, 0, 1, 2, 3]
    assert [r["source"] for r in rows] == ["input", "loop", "loop", "loop", "loop"]
    assert [r["writes_from"] for r in rows] == [[], ["__start__"], ["plan"], ["tools"], ["answer"]]
    assert [r["next"] for r in rows] == [["__start__"], ["plan"], ["tools"], ["answer"], []]
    assert all(r["state_bytes"] > 0 for r in rows)


def test_branch_has_an_update_row(sample_db):
    with sqlite3.connect(sample_db) as conn:
        rows = list_checkpoints(conn, "lisbon-branched")
    update = next(r for r in rows if r["source"] == "update")
    assert update["next"] == ["answer"]
    assert update["writes_from"] == []
    parents = [r["parent_id"] for r in rows]
    assert parents.count(update["parent_id"]) == 2  # the branch point has two children


def test_threads_summary(sample_db):
    with sqlite3.connect(sample_db) as conn:
        threads = list_threads(conn)
    by_id = {t["thread_id"]: t for t in threads}
    assert by_id["lisbon-bug"]["checkpoint_count"] == 5
    assert by_id["lisbon-branched"]["namespaces"] == [""]
    assert threads[0]["last_at"] >= threads[1]["last_at"]


def test_uuid6_time_known_value():
    assert uuid6_time("1f1bf756-229e-6563-8003-d41065ca3b5a") == "2026-10-03T21:57:10.418774Z"


def test_check_schema_rejects_foreign_db(tmp_path):
    conn = sqlite3.connect(tmp_path / "x.sqlite")
    conn.execute("CREATE TABLE checkpoints (thread_id TEXT)")
    with pytest.raises(SchemaError, match="missing columns"):
        check_schema(conn)
    conn.close()


def test_unknown_thread_is_empty(sample_db):
    with sqlite3.connect(sample_db) as conn:
        assert list_checkpoints(conn, "nope") == []
