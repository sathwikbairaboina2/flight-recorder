"""ADR 0002: the read path decodes everything and imports nothing."""

import subprocess
import sys
import textwrap

from flight_recorder.reader import Reader
from flight_recorder.snapshot import Snapshot

CANARY = textwrap.dedent(
    """
    import pathlib, dataclasses, pydantic
    pathlib.Path(__file__).with_name("IMPORTED").write_text("canary module was imported")

    @dataclasses.dataclass
    class Box:
        label: str

    class Card(pydantic.BaseModel):
        n: int
    """
)
WRITER = textwrap.dedent(
    """
    import sqlite3, sys
    from typing import Any, TypedDict
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph
    import fr_canary_mod as m

    class S(TypedDict):
        v: Any

    b = StateGraph(S)
    b.add_node("n", lambda s: {"v": {"box": m.Box(label="x"), "card": m.Card(n=3)}})
    b.add_edge(START, "n")
    b.add_edge("n", END)
    conn = sqlite3.connect(sys.argv[1], check_same_thread=False)
    b.compile(checkpointer=SqliteSaver(conn)).invoke({"v": None}, {"configurable": {"thread_id": "t"}})
    conn.close()
    """
)


def _write_canary_db(tmp_path):
    mod_dir = tmp_path / "mod"
    mod_dir.mkdir()
    (mod_dir / "fr_canary_mod.py").write_text(CANARY)
    db = tmp_path / "db" / "c.sqlite"
    db.parent.mkdir()
    env_path = str(mod_dir)
    subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, {env_path!r}); exec({WRITER!r})", str(db)],
        check=True,
    )
    (mod_dir / "IMPORTED").unlink()  # the writer imported it; the reader must not
    return db, mod_dir


def test_reading_never_imports(tmp_path, monkeypatch):
    db, mod_dir = _write_canary_db(tmp_path)
    monkeypatch.syspath_prepend(str(mod_dir))  # importing would succeed, so only our decoder can prevent it
    snap = Snapshot(db)
    try:
        reader = Reader(snap)
        rows = reader.checkpoints("t")
        values = reader.state("t", rows[-1]["checkpoint_id"])["values"]
    finally:
        snap.close()
    assert not (mod_dir / "IMPORTED").exists()
    assert "fr_canary_mod" not in sys.modules
    assert values["v"]["box"] == {"__object__": "fr_canary_mod.Box", "fields": {"label": "x"}}
    assert values["v"]["card"] == {"__pydantic__": "fr_canary_mod.Card", "fields": {"n": 3}}


def test_dataclass_from_missing_module_is_not_dropped(tmp_path):
    db, mod_dir = _write_canary_db(tmp_path)
    (mod_dir / "fr_canary_mod.py").unlink()  # module gone entirely
    snap = Snapshot(db)
    try:
        reader = Reader(snap)
        rows = reader.checkpoints("t")
        values = reader.state("t", rows[-1]["checkpoint_id"])["values"]
    finally:
        snap.close()
    assert values["v"]["box"]["fields"] == {"label": "x"}
