"""Turn decoded checkpoint values into JSON-safe trees with type tags, and back (spec: Bridged JSON)."""

from __future__ import annotations

import base64
import datetime as _dt
import decimal
import importlib
import math
import uuid
from typing import Any

from .decode import Ext

TAGS = frozenset(
    {
        "__lc_message__",
        "__pydantic__",
        "__object__",
        "__set__",
        "__bytes__",
        "__datetime__",
        "__date__",
        "__time__",
        "__uuid__",
        "__decimal__",
        "__float__",
        "__map__",
        "__unrepresentable__",
    }
)
REPR_LIMIT = 2000
_LC_PREFIX = "langchain_core.messages."


def _unrep(kind: str, value: Any) -> dict:
    return {"__unrepresentable__": kind, "repr": repr(value)[:REPR_LIMIT]}


def _ext_to_json(e: Ext) -> Any:
    t = e.type or ""
    if e.kind in ("pydantic_v1", "pydantic_v2") and isinstance(e.data, dict):
        fields = {str(k): to_json(v) for k, v in e.data.items()}
        if t.startswith(_LC_PREFIX):
            msg_type = e.data.get("type") or t.rsplit(".", 1)[-1]
            return {"__lc_message__": msg_type, **{k: v for k, v in fields.items() if k != "type"}}
        return {"__pydantic__": t, "fields": fields}
    if e.kind == "method" and t in ("datetime.datetime", "datetime.date", "datetime.time"):
        return {f"__{t.rsplit('.', 1)[-1]}__": str(e.data)}
    if e.kind == "single":
        if t in ("builtins.set", "builtins.frozenset"):
            return {"__set__": [to_json(v) for v in e.data]}
        if t == "uuid.UUID":
            return {"__uuid__": str(uuid.UUID(hex=str(e.data)))}
        if t == "decimal.Decimal":
            return {"__decimal__": str(e.data)}
        return {"__object__": t, "args": [to_json(e.data)]}
    if e.kind == "kw" and isinstance(e.data, dict):
        return {"__object__": t, "fields": {str(k): to_json(v) for k, v in e.data.items()}}
    if e.kind == "pos" and isinstance(e.data, (list, tuple)):
        return {"__object__": t, "args": [to_json(v) for v in e.data]}
    if e.kind == "method":
        return {"__object__": t, "method": e.method, "args": [to_json(e.data)]}
    return _unrep(t or e.kind, e.data)


def to_json(value: Any) -> Any:
    """Total mapping to JSON-safe values. Never returns None for a non-None input."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return {"__float__": "nan"}
        if math.isinf(value):
            return {"__float__": "inf" if value > 0 else "-inf"}
        return value
    if isinstance(value, Ext):
        return _ext_to_json(value)
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    if isinstance(value, dict):
        if all(isinstance(k, str) for k in value) and not (TAGS & value.keys()):
            return {k: to_json(v) for k, v in value.items()}
        return {"__map__": [[to_json(k), to_json(v)] for k, v in value.items()]}
    if isinstance(value, (bytes, bytearray)):
        return {"__bytes__": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, (set, frozenset)):
        return {"__set__": [to_json(v) for v in value]}
    return _unrep(f"{type(value).__module__}.{type(value).__qualname__}", value)


def _import(dotted: str) -> Any:
    module, _, name = dotted.rpartition(".")
    return getattr(importlib.import_module(module), name)


def from_json(value: Any) -> Any:
    """Inverse of to_json for the fork editor. Imports classes, so only use where user code is trusted."""
    if isinstance(value, list):
        return [from_json(v) for v in value]
    if not isinstance(value, dict):
        return value
    tag = next((k for k in value if k in TAGS), None)
    if tag is None:
        return {k: from_json(v) for k, v in value.items()}
    body = value[tag]
    if tag == "__lc_message__":
        from langchain_core.messages import messages_from_dict

        fields = {k: from_json(v) for k, v in value.items() if k != tag}
        return messages_from_dict([{"type": body, "data": {"type": body, **fields}}])[0]
    if tag == "__pydantic__":
        return _import(body).model_validate(from_json(value["fields"]))
    if tag == "__object__":
        cls = _import(body)
        if "fields" in value:
            return cls(**from_json(value["fields"]))
        args = from_json(value.get("args", []))
        if value.get("method"):
            return getattr(cls, value["method"])(*args)
        return cls(*args)
    if tag == "__set__":
        return set(from_json(body))
    if tag == "__bytes__":
        return base64.b64decode(body)
    if tag == "__datetime__":
        return _dt.datetime.fromisoformat(body)
    if tag == "__date__":
        return _dt.date.fromisoformat(body)
    if tag == "__time__":
        return _dt.time.fromisoformat(body)
    if tag == "__uuid__":
        return uuid.UUID(body)
    if tag == "__decimal__":
        return decimal.Decimal(body)
    if tag == "__float__":
        return float(body)
    if tag == "__map__":
        return {from_json(k): from_json(v) for k, v in body}
    raise ValueError(f"cannot rebuild an unrepresentable value of type {body!r}")
