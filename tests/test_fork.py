import sqlite3

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from flight_recorder.fork import FORK_PREFIX, ForkEngine, ForkError, new_fork_thread_id
from flight_recorder.graph_loader import load_builder
from flight_recorder.reader import Reader
from flight_recorder.scratch import ScratchStore
from flight_recorder.snapshot import Snapshot


@pytest.fixture
def env(sample_db, tmp_path):
    snap = Snapshot(sample_db)
    store = ScratchStore(tmp_path / "scratch" / "scratch.sqlite")
    engine = ForkEngine(load_builder("flight_recorder.samples:graph"), store, snap.source_sha256())
    reader = Reader(snap, store)
    yield snap, store, engine, reader
    store.close()
    snap.close()


def _plan_step(reader):
    rows = reader.checkpoints("lisbon-bug")
    row = next(r for r in rows if r["writes_from"] == ["plan"])
    return row, reader.state("lisbon-bug", row["checkpoint_id"])["values"]


def _fixed_messages(values):
    msgs = values["messages"]
    msgs[-1]["tool_calls"][0]["args"]["depart_after"] = "2026-11-01"
    return msgs


def test_fork_with_the_date_restored_finds_the_november_flight(env):
    snap, store, engine, reader = env
    row, values = _plan_step(reader)
    res = engine.fork(
        snap.path, "lisbon-bug", row["checkpoint_id"], {"messages": _fixed_messages(values)}, "plan", set()
    )
    assert res["status"] == "done", res["error"]
    assert res["thread_id"].startswith(FORK_PREFIX)
    assert [e["node"] for e in res["events"]] == ["tools", "answer"]
    assert res["events"][-1]["update"]["messages"][0]["content"] == "Cheapest: TP1363 on 2026-11-03 for EUR 142."
    assert res["elapsed_ms"] > 0


def test_fork_thread_is_listed_with_copied_rows_marked(env):
    snap, store, engine, reader = env
    row, values = _plan_step(reader)
    res = engine.fork(
        snap.path, "lisbon-bug", row["checkpoint_id"], {"messages": _fixed_messages(values)}, "plan", set()
    )
    forked = next(t for t in reader.threads() if t["thread_id"] == res["thread_id"])
    assert forked["origin"] == "scratch"
    assert forked["fork_of"] == {"thread_id": "lisbon-bug", "checkpoint_id": row["checkpoint_id"]}
    rows = reader.checkpoints(res["thread_id"])
    assert [(r["step"], r["origin"]) for r in rows] == [
        (-1, "source"), (0, "source"), (1, "source"), (2, "scratch"), (3, "scratch"), (4, "scratch"),
    ]  # fmt: skip
    assert rows[-1]["checkpoint_id"] == res["head_checkpoint_id"]


def test_provenance_row(env):
    snap, store, engine, reader = env
    row, values = _plan_step(reader)
    res = engine.fork(snap.path, "lisbon-bug", row["checkpoint_id"], {}, "plan", set())
    with sqlite3.connect(store.path) as conn:
        rec = conn.execute(
            "SELECT source_db_sha256, source_thread_id, source_checkpoint_id, as_node FROM fr_forks WHERE fork_id = ?",
            (res["fork_id"],),
        ).fetchone()
    assert rec == (snap.source_sha256(), "lisbon-bug", row["checkpoint_id"], "plan")


def test_a_failing_node_gives_status_error_and_keeps_the_fork(env):
    snap, store, engine, reader = env
    row, values = _plan_step(reader)
    broken = values["messages"]
    broken[-1]["tool_calls"] = []  # tools node will index an empty list
    res = engine.fork(snap.path, "lisbon-bug", row["checkpoint_id"], {"messages": broken}, "plan", set())
    assert res["status"] == "error"
    assert "IndexError" in res["error"]
    assert res["thread_id"] in {t["thread_id"] for t in reader.threads()}


def test_bad_values(env):
    snap, store, engine, reader = env
    row, _ = _plan_step(reader)
    with pytest.raises(ForkError):
        engine.fork(
            snap.path, "lisbon-bug", row["checkpoint_id"], {"x": {"__unrepresentable__": "a", "repr": "b"}}, None, set()
        )
    with pytest.raises(ForkError):
        engine.fork(snap.path, "lisbon-bug", row["checkpoint_id"], ["not", "a", "dict"], None, set())  # type: ignore[arg-type]


@settings(max_examples=200, deadline=None)
@given(st.sets(st.one_of(st.text(max_size=12), st.text(max_size=8).map(lambda s: FORK_PREFIX + s)), max_size=20))
def test_fork_thread_namespace(source_ids):
    _, thread_id = new_fork_thread_id(source_ids)
    assert thread_id not in source_ids
    assert thread_id.startswith(FORK_PREFIX)


def test_forced_clash_is_regenerated():
    ids = iter(["aaa", "aaa", "bbb"])
    fork_id, thread_id = new_fork_thread_id({"fork:aaa"}, make_id=lambda: next(ids))
    assert (fork_id, thread_id) == ("bbb", "fork:bbb")
