"""Import the user's graph by `module:attr` (same convention as langgraph.json)."""

from __future__ import annotations

import importlib
import sys
from inspect import isclass
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import StateGraph


class GraphLoadError(RuntimeError):
    pass


def load_builder(spec: str, cwd: str | Path | None = None) -> StateGraph:
    """Return the uncompiled StateGraph behind `module:attr`."""
    if ":" not in spec:
        raise GraphLoadError(f"expected module:attr, got {spec!r}")
    module_name, attr = spec.split(":", 1)
    root = str(Path(cwd or Path.cwd()).resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        obj: Any = getattr(importlib.import_module(module_name), attr)
    except (ImportError, AttributeError) as exc:
        raise GraphLoadError(f"cannot load {spec!r}: {exc}") from exc
    if isinstance(obj, StateGraph):
        return obj
    builder = getattr(obj, "builder", None)
    if isinstance(builder, StateGraph):
        return builder
    raise GraphLoadError(f"{spec!r} is a {type(obj).__name__}, not a StateGraph or compiled StateGraph")


def topology(builder: StateGraph) -> dict:
    g = builder.compile().get_graph()
    return {
        "nodes": list(g.nodes.keys()),
        "edges": [{"source": e.source, "target": e.target, "conditional": bool(e.conditional)} for e in g.edges],
    }


def _state_classes(tp: Any, seen: set) -> None:
    """Collect user-defined classes reachable from a state schema's type hints."""
    if tp in seen:
        return
    seen.add(tp)
    for arg in get_args(tp):
        _state_classes(arg, seen)
    origin = get_origin(tp)
    if origin is not None:
        _state_classes(origin, seen)
    if isclass(tp):
        try:
            hints = get_type_hints(tp, include_extras=True)
        except Exception:  # unresolved forward references: skip, the class itself is still allowed
            hints = {}
        for hint in hints.values():
            _state_classes(hint, seen)


def fork_serde(builder: StateGraph) -> JsonPlusSerializer:
    """A serializer that allows the graph's own state types, so strict msgpack mode still works (ADR 0002)."""
    seen: set = set()
    for schema in {builder.state_schema, builder.input_schema, builder.output_schema}:
        _state_classes(schema, seen)
    allowed = [(c.__module__, c.__name__) for c in seen if isclass(c) and c.__module__ != "builtins"]
    return JsonPlusSerializer(allowed_msgpack_modules=allowed)
