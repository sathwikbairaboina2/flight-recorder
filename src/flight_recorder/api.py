"""FastAPI app: REST for reads and forks, plus the built UI as static files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .fork import CheckpointNotFound, ForkEngine, ForkError
from .reader import NotFound, Reader


class ForkRequest(BaseModel):
    thread_id: str
    checkpoint_id: str
    values: dict[str, Any]
    as_node: str | None = None


def create_app(
    reader: Reader,
    engine: ForkEngine | None = None,
    topology: dict | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="flight-recorder", version=__version__)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "version": __version__, "graph": engine is not None, "source": reader.snapshot.source.name}

    @app.get("/api/threads")
    def threads() -> list[dict]:
        return reader.threads()

    @app.get("/api/threads/{thread_id:path}/checkpoints")
    def checkpoints(thread_id: str, ns: str = "") -> list[dict]:
        try:
            return reader.checkpoints(thread_id, ns)
        except NotFound as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/threads/{thread_id:path}/checkpoints/{checkpoint_id}")
    def state(thread_id: str, checkpoint_id: str, ns: str = "") -> dict:
        try:
            return reader.state(thread_id, checkpoint_id, ns)
        except NotFound as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/graph")
    def graph() -> dict:
        if topology is None:
            raise HTTPException(404, "no graph loaded; start with --graph module:attr")
        return topology

    @app.post("/api/forks")
    def fork(req: ForkRequest) -> dict:
        if engine is None:
            raise HTTPException(400, "forking needs the graph; start with --graph module:attr")
        try:
            reader.checkpoints(req.thread_id)
        except NotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        taken = {t["thread_id"] for t in reader.threads()}
        try:
            db, _origin = reader.db_for(req.thread_id)
            return engine.fork(db, req.thread_id, req.checkpoint_id, req.values, req.as_node, taken)
        except CheckpointNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except ForkError as exc:
            raise HTTPException(422, str(exc)) from exc

    if static_dir is not None and (static_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")
    return app
