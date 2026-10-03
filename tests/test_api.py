import pytest
from fastapi.testclient import TestClient

from flight_recorder.api import create_app
from flight_recorder.fork import ForkEngine
from flight_recorder.graph_loader import load_builder, topology
from flight_recorder.reader import Reader
from flight_recorder.scratch import ScratchStore
from flight_recorder.snapshot import Snapshot


@pytest.fixture
def client(sample_db, tmp_path):
    snap = Snapshot(sample_db)
    store = ScratchStore(tmp_path / "scratch.sqlite")
    builder = load_builder("flight_recorder.samples:graph")
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>flight-recorder</title>")
    app = create_app(Reader(snap, store), ForkEngine(builder, store, snap.source_sha256()), topology(builder), static)
    yield TestClient(app)
    store.close()
    snap.close()


@pytest.fixture
def read_only_client(sample_db):
    snap = Snapshot(sample_db)
    yield TestClient(create_app(Reader(snap)))
    snap.close()


def test_health(client):
    assert client.get("/api/health").json() == {
        "ok": True, "version": "0.1.0", "graph": True, "source": "checkpoints.sqlite",
    }  # fmt: skip


def test_read_endpoints(client):
    threads = client.get("/api/threads").json()
    assert {t["thread_id"] for t in threads} == {"lisbon-bug", "lisbon-branched"}
    rows = client.get("/api/threads/lisbon-bug/checkpoints").json()
    assert len(rows) == 5 and rows[0]["origin"] == "source"
    st = client.get(f"/api/threads/lisbon-bug/checkpoints/{rows[-1]['checkpoint_id']}").json()
    assert st["values"]["messages"][-1]["content"] == "Cheapest: TP1351 on 2026-10-28 for EUR 89."


def test_static_ui_is_served(client):
    assert "flight-recorder" in client.get("/").text


def test_fork_endpoint(client):
    rows = client.get("/api/threads/lisbon-bug/checkpoints").json()
    plan = next(r for r in rows if r["writes_from"] == ["plan"])
    values = client.get(f"/api/threads/lisbon-bug/checkpoints/{plan['checkpoint_id']}").json()["values"]
    values["messages"][-1]["tool_calls"][0]["args"]["depart_after"] = "2026-11-01"
    body = {
        "thread_id": "lisbon-bug",
        "checkpoint_id": plan["checkpoint_id"],
        "values": {"messages": values["messages"]},
        "as_node": "plan",
    }
    res = client.post("/api/forks", json=body).json()
    assert res["status"] == "done"
    head = client.get(f"/api/threads/{res['thread_id']}/checkpoints/{res['head_checkpoint_id']}").json()
    assert head["values"]["messages"][-1]["content"] == "Cheapest: TP1363 on 2026-11-03 for EUR 142."
    again = client.post("/api/forks", json={**body, "thread_id": res["thread_id"], "values": {}}).json()
    assert again["status"] == "done"  # forking a fork reads from the scratch database


def test_error_codes(client, read_only_client):
    rows = client.get("/api/threads/lisbon-bug/checkpoints").json()
    cid = rows[1]["checkpoint_id"]
    assert client.get("/api/threads/nope/checkpoints").status_code == 404
    assert client.get("/api/threads/lisbon-bug/checkpoints/nope").status_code == 404
    assert client.post("/api/forks", json={"thread_id": "nope", "checkpoint_id": cid, "values": {}}).status_code == 404
    assert (
        client.post("/api/forks", json={"thread_id": "lisbon-bug", "checkpoint_id": "x", "values": {}}).status_code
        == 404
    )
    bad = {"thread_id": "lisbon-bug", "checkpoint_id": cid, "values": {"x": {"__unrepresentable__": "a", "repr": "b"}}}
    assert client.post("/api/forks", json=bad).status_code == 422
    assert (
        read_only_client.post(
            "/api/forks", json={"thread_id": "lisbon-bug", "checkpoint_id": cid, "values": {}}
        ).status_code
        == 400
    )
    assert read_only_client.get("/api/graph").status_code == 404
    assert client.get("/api/graph").json()["nodes"][1] == "plan"
