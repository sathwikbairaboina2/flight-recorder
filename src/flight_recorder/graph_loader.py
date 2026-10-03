"""Import the user's graph by `module:attr` (same convention as langgraph.json)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

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
