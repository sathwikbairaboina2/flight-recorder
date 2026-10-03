"""Read threads, checkpoint indexes and full states from the snapshot and the scratch database."""

from __future__ import annotations

import sqlite3
import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from .bridge import to_json
from .decode import SafeSerializer
from .index import check_schema, list_checkpoints, list_threads
from .scratch import ScratchStore
from .snapshot import Snapshot

CACHE_SIZE = 16


class NotFound(LookupError):
    pass


class Reader:
    def __init__(self, snapshot: Snapshot, scratch: ScratchStore | None = None) -> None:
        self.snapshot = snapshot
        self.scratch = scratch
        self._cache: OrderedDict[tuple, list[dict]] = OrderedDict()
        self._lock = threading.Lock()
        with self._connect(snapshot.path) as conn:
            check_schema(conn)

    @staticmethod
    @contextmanager
    def _connect(path: Path) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(path), check_same_thread=False)
        try:
            yield conn
        finally:
            conn.close()

    def db_for(self, thread_id: str) -> tuple[Path, str]:
        if self.scratch is not None and thread_id in self.scratch.thread_ids():
            return self.scratch.path, "scratch"
        return self.snapshot.path, "source"

    def threads(self) -> list[dict]:
        self.snapshot.refresh()
        with self._connect(self.snapshot.path) as conn:
            out = [{**t, "origin": "source", "fork_of": None} for t in list_threads(conn)]
        if self.scratch is not None:
            forks = {f["scratch_thread_id"]: f for f in self.scratch.forks()}
            with self.scratch.lock, self._connect(self.scratch.path) as conn:
                scratch_threads = list_threads(conn)
            for t in scratch_threads:
                f = forks.get(t["thread_id"])
                if f is None:
                    continue
                fork_of = {"thread_id": f["source_thread_id"], "checkpoint_id": f["source_checkpoint_id"]}
                out.append({**t, "origin": "scratch", "fork_of": fork_of})
        out.sort(key=lambda t: t["last_at"] or "", reverse=True)
        return out

    def checkpoints(self, thread_id: str, ns: str = "") -> list[dict]:
        path, origin = self.db_for(thread_id)
        key = (str(path), self.snapshot.generation if origin == "source" else None, thread_id, ns)
        with self._lock:
            if origin == "source" and key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        if origin == "scratch":
            with self.scratch.lock, self._connect(path) as conn:
                rows = [{**r, "origin": "scratch"} for r in list_checkpoints(conn, thread_id, ns)]
            self._mark_copied(thread_id, rows)
        else:
            with self._connect(path) as conn:
                rows = [{**r, "origin": "source"} for r in list_checkpoints(conn, thread_id, ns)]
        if not rows:
            raise NotFound(f"thread {thread_id!r} (ns {ns!r}) has no checkpoints")
        if origin == "source":
            with self._lock:
                self._cache[key] = rows
                while len(self._cache) > CACHE_SIZE:
                    self._cache.popitem(last=False)
        return rows

    def _mark_copied(self, thread_id: str, rows: list[dict]) -> None:
        """Rows copied from the source thread (the fork base and its ancestors) get origin "source"."""
        fork = next((f for f in self.scratch.forks() if f["scratch_thread_id"] == thread_id), None)
        if fork is None:
            return
        parent = {r["checkpoint_id"]: r["parent_id"] for r in rows}
        copied: set[str] = set()
        cid = fork["source_checkpoint_id"]
        while cid is not None and cid in parent and cid not in copied:
            copied.add(cid)
            cid = parent[cid]
        for r in rows:
            if r["checkpoint_id"] in copied:
                r["origin"] = "source"

    def state(self, thread_id: str, checkpoint_id: str, ns: str = "") -> dict:
        row = next((r for r in self.checkpoints(thread_id, ns) if r["checkpoint_id"] == checkpoint_id), None)
        if row is None:
            raise NotFound(f"checkpoint {checkpoint_id!r} not in thread {thread_id!r}")
        path, _ = self.db_for(thread_id)
        with self._connect(path) as conn:
            saver = SqliteSaver(conn, serde=SafeSerializer())
            cfg = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ns, "checkpoint_id": checkpoint_id}}
            tup = saver.get_tuple(cfg)
        if tup is None:
            raise NotFound(f"checkpoint {checkpoint_id!r} not in thread {thread_id!r}")
        return {
            "checkpoint_id": checkpoint_id,
            "values": to_json(tup.checkpoint.get("channel_values", {})),
            "next": row["next"],
            "pending_writes": [
                {"task_id": task_id, "channel": channel, "value": to_json(value)}
                for task_id, channel, value in (tup.pending_writes or [])
            ],
            "metadata": to_json(dict(tup.metadata or {})),
        }
