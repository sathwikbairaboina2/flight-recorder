"""Dump real API responses for the sample threads into ui/src/test/fixtures/lisbon.json (UI tests)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from flight_recorder.cli import build_app
from flight_recorder.samples import make_sample_db

OUT = Path(__file__).resolve().parents[1] / "ui" / "src" / "test" / "fixtures" / "lisbon.json"


def main() -> None:
    db = make_sample_db(Path(tempfile.mkdtemp(prefix="fr-fixtures-")) / "checkpoints.sqlite")
    app, closers = build_app(str(db), "flight_recorder.samples:graph", None)
    try:
        c = TestClient(app)
        data: dict = {"health": c.get("/api/health").json(), "graph": c.get("/api/graph").json()}
        data["threads"] = c.get("/api/threads").json()
        data["checkpoints"], data["states"] = {}, {}
        for t in data["threads"]:
            rows = c.get(f"/api/threads/{t['thread_id']}/checkpoints").json()
            data["checkpoints"][t["thread_id"]] = rows
            for r in rows:
                url = f"/api/threads/{t['thread_id']}/checkpoints/{r['checkpoint_id']}"
                data["states"][r["checkpoint_id"]] = c.get(url).json()
    finally:
        for close in closers:
            close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
