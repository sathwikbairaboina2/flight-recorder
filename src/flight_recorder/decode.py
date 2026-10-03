"""Decode LangGraph checkpoints without importing any module named in the data (ADR 0002)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import ormsgpack
from langgraph.checkpoint.serde.jsonplus import (
    EXT_CONSTRUCTOR_KW_ARGS,
    EXT_CONSTRUCTOR_POS_ARGS,
    EXT_CONSTRUCTOR_SINGLE_ARG,
    EXT_DELTA_SNAPSHOT,
    EXT_METHOD_SINGLE_ARG,
    EXT_NUMPY_ARRAY,
    EXT_PYDANTIC_V1,
    EXT_PYDANTIC_V2,
    JsonPlusSerializer,
)

KINDS = {
    EXT_CONSTRUCTOR_SINGLE_ARG: "single",
    EXT_CONSTRUCTOR_POS_ARGS: "pos",
    EXT_CONSTRUCTOR_KW_ARGS: "kw",
    EXT_METHOD_SINGLE_ARG: "method",
    EXT_PYDANTIC_V1: "pydantic_v1",
    EXT_PYDANTIC_V2: "pydantic_v2",
    EXT_NUMPY_ARRAY: "numpy",
    EXT_DELTA_SNAPSHOT: "delta",
}
_TYPED = {
    EXT_CONSTRUCTOR_SINGLE_ARG,
    EXT_CONSTRUCTOR_POS_ARGS,
    EXT_CONSTRUCTOR_KW_ARGS,
    EXT_METHOD_SINGLE_ARG,
    EXT_PYDANTIC_V1,
    EXT_PYDANTIC_V2,
}


@dataclass(frozen=True)
class Ext:
    """An undecoded msgpack extension: kind, dotted type name, payload, optional method."""

    kind: str
    type: str | None
    data: Any
    method: str | None = None


def safe_ext_hook(code: int, data: bytes) -> Any:
    try:
        tup = ormsgpack.unpackb(data, ext_hook=safe_ext_hook, option=ormsgpack.OPT_NON_STR_KEYS)
    except Exception as exc:  # corrupt payload: keep it visible, never drop it
        return Ext(kind="corrupt", type=None, data=f"{type(exc).__name__}: {exc}")
    kind = KINDS.get(code, f"ext{code}")
    if code in _TYPED and isinstance(tup, (list, tuple)) and len(tup) >= 3:
        method = tup[3] if len(tup) > 3 and isinstance(tup[3], str) else None
        return Ext(kind=kind, type=f"{tup[0]}.{tup[1]}", data=tup[2], method=method)
    return Ext(kind=kind, type=None, data=tup)


class SafeSerializer(JsonPlusSerializer):
    """JsonPlusSerializer whose msgpack ext hook never imports."""

    def __init__(self) -> None:
        super().__init__(__unpack_ext_hook__=safe_ext_hook)


def shallow_ext_hook(code: int, data: bytes) -> None:
    """Skip every extension. Used by the index, which only needs top-level keys."""
    return None
