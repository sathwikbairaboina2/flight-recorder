"""Metadata-only index over the SqliteSaver tables (ADR 0003)."""

from __future__ import annotations

import datetime as _dt
import json
import sqlite3
import uuid

import ormsgpack

from .decode import shallow_ext_hook

_UUID_EPOCH = _dt.datetime(1582, 10, 15, tzinfo=_dt.UTC)
REQUIRED = {
    "checkpoints": {
        "thread_id",
        "checkpoint_ns",
        "checkpoint_id",
        "parent_checkpoint_id",
        "type",
        "checkpoint",
        "metadata",
    },
    "writes": {"thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "channel", "value"},
}


class SchemaError(RuntimeError):
    pass


def uuid6_time(checkpoint_id: str) -> str:
    """ISO-8601 UTC time encoded in a LangGraph uuid6 checkpoint id."""
    n = uuid.UUID(checkpoint_id).int
    ticks = ((n >> 80) << 12) | ((n >> 64) & 0x0FFF)
    return (_UUID_EPOCH + _dt.timedelta(microseconds=ticks // 10)).isoformat().replace("+00:00", "Z")


def check_schema(conn: sqlite3.Connection) -> None:
    for table, cols in REQUIRED.items():
        found = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        missing = cols - found
        if missing:
            raise SchemaError(
                f"table {table!r} is missing columns {sorted(missing)}; found {sorted(found)}. "
                "Is this a LangGraph SqliteSaver database?"
            )


_HIDDEN_WRITERS = {"__input__", "__interrupt__"}


def _shallow(blob: bytes | None, type_: str | None) -> dict:
    if not blob or type_ != "msgpack":
        return {}
    try:
        ck = ormsgpack.unpackb(blob, ext_hook=shallow_ext_hook, option=ormsgpack.OPT_NON_STR_KEYS)
    except Exception:
        return {}
    return ck if isinstance(ck, dict) else {}


def _next_nodes(ck: dict, parent: dict | None) -> list[str]:
    """Nodes triggered by this checkpoint: `branch:to:<node>` channels it updated (plus __start__)."""
    chans = ck.get("updated_channels")
    if chans is None:  # update_state checkpoints do not record updated_channels; diff versions instead
        cv = ck.get("channel_versions") or {}
        pcv = (parent or {}).get("channel_versions") or {}
        chans = [ch for ch, v in cv.items() if pcv.get(ch) != v]
    nodes = {c[len("branch:to:") :] for c in chans if isinstance(c, str) and c.startswith("branch:to:")}
    if "__start__" in chans:
        nodes.add("__start__")
    return sorted(nodes)


def _writers(ck: dict, parent: dict | None) -> list[str]:
    """Nodes that ran to produce this checkpoint: their versions_seen changed since the parent."""
    vs = ck.get("versions_seen") or {}
    pvs = (parent or {}).get("versions_seen") or {}
    return sorted(n for n in vs if vs[n] != pvs.get(n) and n not in _HIDDEN_WRITERS)


def list_threads(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT thread_id, checkpoint_ns, COUNT(*), MIN(checkpoint_id), MAX(checkpoint_id) "
        "FROM checkpoints GROUP BY thread_id, checkpoint_ns"
    ).fetchall()
    threads: dict[str, dict] = {}
    for tid, ns, count, first, last in rows:
        t = threads.setdefault(
            tid,
            {"thread_id": tid, "checkpoint_count": 0, "first_at": None, "last_at": None, "namespaces": []},
        )
        t["namespaces"].append(ns)
        if ns == "":
            t["checkpoint_count"] = count
            t["first_at"] = uuid6_time(first)
            t["last_at"] = uuid6_time(last)
    out = list(threads.values())
    for t in out:
        t["namespaces"].sort()
    out.sort(key=lambda t: t["last_at"] or "", reverse=True)
    return out


def list_checkpoints(conn: sqlite3.Connection, thread_id: str, ns: str = "") -> list[dict]:
    rows = conn.execute(
        "SELECT checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata, length(checkpoint) "
        "FROM checkpoints WHERE thread_id = ? AND checkpoint_ns = ? ORDER BY checkpoint_id",
        (thread_id, ns),
    ).fetchall()
    out: list[dict] = []
    shallow: dict[str, dict] = {}
    for cid, parent, type_, blob, meta_raw, size in rows:
        ck = _shallow(blob, type_)
        shallow[cid] = ck
        parent_ck = shallow.get(parent) if parent else None
        try:
            meta = json.loads(meta_raw) if meta_raw else {}
        except (TypeError, ValueError):
            meta = {}
        out.append(
            {
                "checkpoint_id": cid,
                "parent_id": parent,
                "step": meta.get("step"),
                "source": meta.get("source"),
                "next": _next_nodes(ck, parent_ck),
                "writes_from": _writers(ck, parent_ck) if parent_ck is not None else [],
                "created_at": uuid6_time(cid),
                "state_bytes": size or 0,
            }
        )
    return out
