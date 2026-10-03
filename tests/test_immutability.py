"""Invariant 1: reads and forks never change a byte in the source directory (ADR 0001)."""

import sqlite3
from typing import TypedDict

from conftest import dir_fingerprint
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from flight_recorder.fork import ForkEngine
from flight_recorder.graph_loader import load_builder
from flight_recorder.reader import Reader
from flight_recorder.scratch import ScratchStore
from flight_recorder.snapshot import Snapshot


def test_source_db_unchanged(sample_db, tmp_path):
    before = dir_fingerprint(sample_db.parent)
    snap = Snapshot(sample_db)
    store = ScratchStore(tmp_path / "scratch.sqlite")
    reader = Reader(snap, store)
    engine = ForkEngine(load_builder("flight_recorder.samples:graph"), store, snap.source_sha256())
    for t in reader.threads():
        for row in reader.checkpoints(t["thread_id"]):
            reader.state(t["thread_id"], row["checkpoint_id"])
    plan_row = next(r for r in reader.checkpoints("lisbon-bug") if r["writes_from"] == ["plan"])
    for _ in range(5):
        res = engine.fork(snap.path, "lisbon-bug", plan_row["checkpoint_id"], {}, "plan", set())
        assert res["status"] == "done"
    store.close()
    snap.close()
    assert dir_fingerprint(sample_db.parent) == before


class S(TypedDict):
    x: int


def test_live_writer_with_uncheckpointed_wal(tmp_path):
    src = tmp_path / "live"
    src.mkdir()
    db = src / "live.sqlite"
    b = StateGraph(S)
    b.add_node("n", lambda s: {"x": s["x"] + 1})
    b.add_edge(START, "n")
    b.add_edge("n", END)
    writer = sqlite3.connect(db, check_same_thread=False)
    b.compile(checkpointer=SqliteSaver(writer)).invoke({"x": 0}, {"configurable": {"thread_id": "live"}})
    try:
        assert (src / "live.sqlite-wal").exists()  # the writer is still open, so the WAL holds the data
        before = dir_fingerprint(src)
        snap = Snapshot(db)
        reader = Reader(snap)
        assert reader.threads()[0]["checkpoint_count"] == 3
        snap.close()
        assert dir_fingerprint(src) == before
    finally:
        writer.close()
