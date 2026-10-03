"""Invariant 5: decode + bridge never drops a value, and from_json inverts to_json."""

import dataclasses
import datetime as dt
import decimal
import json
import math
import uuid

import pydantic
from hypothesis import given, settings
from hypothesis import strategies as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from flight_recorder.bridge import TAGS, from_json, to_json
from flight_recorder.decode import Ext, SafeSerializer, safe_ext_hook

REAL = JsonPlusSerializer()
SAFE = SafeSerializer()


@dataclasses.dataclass
class Box:
    label: str
    n: int


class Card(pydantic.BaseModel):
    title: str
    tags: list[str] = []


def roundtrip(value):
    """What the reader sees: stored with LangGraph's serializer, read with ours, bridged to JSON."""
    out = to_json(SAFE.loads_typed(REAL.dumps_typed(value)))
    json.dumps(out, allow_nan=False)  # strict JSON or this raises
    return out


def test_messages_become_tagged_and_keep_ids():
    ai = AIMessage(content="", id="ai-1", tool_calls=[{"name": "s", "args": {"q": 1}, "id": "c1"}])
    out = roundtrip([HumanMessage(content="hi", id="h-1"), ai, ToolMessage(content="r", tool_call_id="c1", id="t-1")])
    assert [m["__lc_message__"] for m in out] == ["human", "ai", "tool"]
    assert [m["id"] for m in out] == ["h-1", "ai-1", "t-1"]
    assert out[1]["tool_calls"][0]["args"] == {"q": 1}
    assert out[2]["tool_call_id"] == "c1"


def test_fixture_table():
    value = {
        "box": Box(label="x", n=2),
        "card": Card(title="t", tags=["a"]),
        "set": {3},
        "bytes": b"\x00\xff",
        "when": dt.datetime(2026, 10, 4, 9, 30, tzinfo=dt.UTC),
        "id": uuid.UUID(int=7),
        "money": decimal.Decimal("1.50"),
        "pair": (1, "a"),
        "nan": math.nan,
        "inf": -math.inf,
        "int_keys": {1: "one"},
        "reserved": {"__set__": "not a set"},
    }
    out = roundtrip(value)
    assert out["box"] == {"__object__": f"{__name__}.Box", "fields": {"label": "x", "n": 2}}
    assert out["card"] == {"__pydantic__": f"{__name__}.Card", "fields": {"title": "t", "tags": ["a"]}}
    assert out["set"] == {"__set__": [3]}
    assert out["bytes"] == {"__bytes__": "AP8="}
    assert out["when"] == {"__datetime__": "2026-10-04T09:30:00+00:00"}
    assert out["id"] == {"__uuid__": "00000000-0000-0000-0000-000000000007"}
    assert out["money"] == {"__decimal__": "1.50"}
    assert out["pair"] == [1, "a"]
    assert out["nan"] == {"__float__": "nan"}
    assert out["inf"] == {"__float__": "-inf"}
    assert out["int_keys"] == {"__map__": [[1, "one"]]}
    assert out["reserved"] == {"__map__": [["__set__", "not a set"]]}


def test_unknown_things_are_tagged_not_dropped():
    assert to_json(Ext(kind="numpy", type=None, data=[1, 2]))["__unrepresentable__"] == "numpy"
    assert to_json(object())["__unrepresentable__"] == "builtins.object"
    assert to_json(Ext(kind="ext42", type=None, data="x")) == {"__unrepresentable__": "ext42", "repr": "'x'"}
    assert safe_ext_hook(1, b"\xc1").kind == "corrupt"  # 0xc1 is never valid msgpack


def test_repr_is_capped():
    out = to_json(Ext(kind="numpy", type=None, data="y" * 10_000))
    assert len(out["repr"]) == 2000


def test_from_json_rebuilds_fork_values():
    value = {
        "messages": [AIMessage(content="", id="a", tool_calls=[{"name": "s", "args": {}, "id": "c"}])],
        "card": Card(title="t"),
        "box": Box(label="b", n=1),
        "when": dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        "set": {1, 2},
        "money": decimal.Decimal("2.5"),
        "id": uuid.UUID(int=1),
        "raw": b"ab",
        "keys": {2: "two"},
    }
    assert from_json(roundtrip(value)) == value


def test_from_json_refuses_unrepresentable():
    import pytest

    with pytest.raises(ValueError):
        from_json({"x": {"__unrepresentable__": "numpy", "repr": "array"}})


def test_tags_are_the_spec_table():
    assert {
        "__lc_message__", "__pydantic__", "__object__", "__set__", "__bytes__", "__datetime__", "__date__",
        "__time__", "__uuid__", "__decimal__", "__float__", "__map__", "__unrepresentable__",
    } == TAGS  # fmt: skip


scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**63), max_value=2**63 - 1),
    st.floats(allow_nan=False),
    st.text(max_size=8),
    st.binary(max_size=8),
    st.datetimes(timezones=st.just(dt.UTC)),
    st.uuids(),
    st.decimals(allow_nan=False, allow_infinity=False, places=3),
)
values = st.recursive(
    scalars,
    lambda inner: st.one_of(
        st.lists(inner, max_size=4),
        st.dictionaries(st.text(max_size=6), inner, max_size=4),
        st.frozensets(st.integers(min_value=-(2**63), max_value=2**63 - 1), max_size=4).map(set),
    ),
    max_leaves=20,
)


@settings(max_examples=300, deadline=None)
@given(values)
def test_roundtrip_property(value):
    assert from_json(roundtrip(value)) == value
