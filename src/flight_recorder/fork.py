"""Fork a source thread into the scratch database and run it (ADR 0004, ADR 0005)."""

from __future__ import annotations

import datetime as _dt
import json
import sqlite3
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

from .bridge import from_json, to_json
from .decode import SafeSerializer
from .scratch import ScratchStore

FORK_PREFIX = "fork:"
RECURSION_LIMIT = 100


class ForkError(ValueError):
    pass


class CheckpointNotFound(LookupError):
    pass


def new_fork_thread_id(taken: set[str], make_id: Callable[[], str] = lambda: uuid.uuid4().hex) -> tuple[str, str]:
    """Return (fork_id, thread_id) whose thread_id is not in `taken`."""
    while True:
        fork_id = make_id()
        thread_id = FORK_PREFIX + fork_id
        if thread_id not in taken:
            return fork_id, thread_id


def _cfg(thread_id: str, checkpoint_id: str | None = None, ns: str = "") -> dict:
    c: dict[str, Any] = {"thread_id": thread_id, "checkpoint_ns": ns}
    if checkpoint_id is not None:
        c["checkpoint_id"] = checkpoint_id
    return {"configurable": c}


class ForkEngine:
    def __init__(self, builder: StateGraph, scratch: ScratchStore, source_sha256: str) -> None:
        self.scratch = scratch
        self.graph = builder.compile(checkpointer=scratch.saver)
        self._source_sha256 = source_sha256
        self._real = JsonPlusSerializer()
        self._safe = SafeSerializer()

    def _ancestors(self, src: SqliteSaver, thread_id: str, checkpoint_id: str) -> list:
        chain = []
        cid: str | None = checkpoint_id
        while cid is not None:
            tup = src.get_tuple(_cfg(thread_id, cid))
            if tup is None:
                raise CheckpointNotFound(f"checkpoint {cid} not found in thread {thread_id}")
            chain.append(tup)
            cid = (tup.parent_config or {}).get("configurable", {}).get("checkpoint_id")
        chain.reverse()
        return chain

    def fork(
        self, db: Path, thread_id: str, checkpoint_id: str, values: dict, as_node: str | None, taken: set[str]
    ) -> dict:
        """Fork `thread_id` at `checkpoint_id`, reading the chain from `db` (snapshot or scratch path)."""
        if not isinstance(values, dict):
            raise ForkError("values must be a JSON object of top-level channels")
        try:
            update = from_json(values)
        except (ValueError, TypeError, ImportError, AttributeError) as exc:
            raise ForkError(f"cannot rebuild values: {exc}") from exc
        started = time.perf_counter()
        src_conn = sqlite3.connect(str(db), check_same_thread=False)
        try:
            chain = self._ancestors(SqliteSaver(src_conn), thread_id, checkpoint_id)
        finally:
            src_conn.close()
        fork_id, fork_tid = new_fork_thread_id(taken | self.scratch.thread_ids())
        with self.scratch.lock:
            for tup in chain:
                parent_id = (tup.parent_config or {}).get("configurable", {}).get("checkpoint_id")
                own_id = tup.config["configurable"]["checkpoint_id"]
                self.scratch.saver.put(
                    _cfg(fork_tid, parent_id), tup.checkpoint, tup.metadata, tup.checkpoint.get("channel_versions", {})
                )
                by_task: dict[str, list] = {}
                for task_id, channel, value in tup.pending_writes or []:
                    by_task.setdefault(task_id, []).append((channel, value))
                for task_id, writes in by_task.items():
                    self.scratch.saver.put_writes(_cfg(fork_tid, own_id), writes, task_id)
            self.scratch.conn.execute(
                "INSERT INTO fr_forks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    fork_id,
                    self._source_sha256,
                    thread_id,
                    checkpoint_id,
                    fork_tid,
                    as_node,
                    json.dumps(values),
                    _dt.datetime.now(_dt.UTC).isoformat(),
                ),
            )
            self.scratch.conn.commit()
            base = _cfg(fork_tid, checkpoint_id)
            events: list[dict] = []
            status, error = "done", None
            try:
                cfg = self.graph.update_state(base, update, as_node=as_node)
                for chunk in self.graph.stream(
                    None, {**cfg, "recursion_limit": RECURSION_LIMIT}, stream_mode="updates"
                ):
                    for node, upd in chunk.items():
                        events.append(
                            {"node": node, "update": to_json(self._safe.loads_typed(self._real.dumps_typed(upd)))}
                        )
                head = self.graph.get_state(_cfg(fork_tid))
                if head.next:
                    status = "interrupted"
            except Exception as exc:  # the partial fork stays visible
                status, error = "error", f"{type(exc).__name__}: {exc}"
                head = self.graph.get_state(_cfg(fork_tid))
        return {
            "fork_id": fork_id,
            "thread_id": fork_tid,
            "base_checkpoint_id": checkpoint_id,
            "head_checkpoint_id": head.config["configurable"]["checkpoint_id"],
            "status": status,
            "events": events,
            "error": error,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        }
