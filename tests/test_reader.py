import pytest

from flight_recorder.reader import NotFound, Reader
from flight_recorder.snapshot import Snapshot


@pytest.fixture
def reader(sample_db):
    snap = Snapshot(sample_db)
    yield Reader(snap)
    snap.close()


def test_threads_have_origin(reader):
    threads = reader.threads()
    assert {t["thread_id"] for t in threads} == {"lisbon-bug", "lisbon-branched"}
    assert all(t["origin"] == "source" and t["fork_of"] is None for t in threads)


def test_state_is_bridged(reader):
    rows = reader.checkpoints("lisbon-bug")
    plan_row = next(r for r in rows if r["writes_from"] == ["plan"])
    st = reader.state("lisbon-bug", plan_row["checkpoint_id"])
    assert st["next"] == ["tools"]
    assert st["values"]["query"] == {
        "__pydantic__": "flight_recorder.samples.SearchQuery",
        "fields": {"destination": "Lisbon", "depart_after": None},
    }
    ai = st["values"]["messages"][-1]
    assert ai["__lc_message__"] == "ai"
    assert ai["tool_calls"][0]["args"]["depart_after"] is None
    assert st["metadata"]["source"] == "loop"


def test_pending_writes_are_listed(reader):
    first = reader.checkpoints("lisbon-bug")[0]
    st = reader.state("lisbon-bug", first["checkpoint_id"])
    assert {w["channel"] for w in st["pending_writes"]} >= {"messages"}


def test_not_found(reader):
    with pytest.raises(NotFound):
        reader.checkpoints("nope")
    with pytest.raises(NotFound):
        reader.state("lisbon-bug", "nope")


def test_index_is_cached_per_generation(reader):
    assert reader.checkpoints("lisbon-bug") is reader.checkpoints("lisbon-bug")
