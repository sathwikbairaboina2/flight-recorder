"""A deterministic sample agent with a real bug, and the generator for sample databases.

The "flight search" agent is asked for flights to Lisbon departing after 2026-11-01. Its fake model
drops the date filter when it writes the tool call, so the answer recommends an October flight.
Forking from the plan step with the date restored gives the right answer. No network, no LLM.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

USER_ASK = "Find me the cheapest flight to Lisbon departing after 2026-11-01."
FLIGHTS = [
    {"flight": "TP1351", "destination": "Lisbon", "date": "2026-10-28", "price_eur": 89},
    {"flight": "FR8342", "destination": "Lisbon", "date": "2026-10-30", "price_eur": 104},
    {"flight": "TP1363", "destination": "Lisbon", "date": "2026-11-03", "price_eur": 142},
    {"flight": "U27701", "destination": "Lisbon", "date": "2026-11-05", "price_eur": 157},
    {"flight": "LH1166", "destination": "Porto", "date": "2026-11-04", "price_eur": 99},
]


class SearchQuery(BaseModel):
    destination: str
    depart_after: str | None = None


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    query: SearchQuery | None
    results: list[dict]


def plan(state: AgentState) -> dict:
    # The bug on purpose: the fake model reads the destination and forgets the date.
    args = {"destination": "Lisbon", "depart_after": None}
    call = {"name": "search_flights", "args": args, "id": "call-1", "type": "tool_call"}
    msg = AIMessage(content="", id="ai-plan", tool_calls=[call])
    return {"messages": [msg], "query": SearchQuery(**args)}


def search_flights(destination: str, depart_after: str | None) -> list[dict]:
    hits = [f for f in FLIGHTS if f["destination"] == destination]
    if depart_after:
        hits = [f for f in hits if f["date"] > depart_after]
    return sorted(hits, key=lambda f: f["price_eur"])


def tools(state: AgentState) -> dict:
    last = state["messages"][-1]
    call = last.tool_calls[0]
    results = search_flights(**call["args"])
    msg = ToolMessage(content=json.dumps(results), tool_call_id=call["id"], id="tool-1")
    return {"messages": [msg], "results": results}


def answer(state: AgentState) -> dict:
    if not state["results"]:
        text = "No flights found."
    else:
        best = state["results"][0]
        text = f"Cheapest: {best['flight']} on {best['date']} for EUR {best['price_eur']}."
    return {"messages": [AIMessage(content=text, id="ai-answer")]}


def build() -> StateGraph:
    b = StateGraph(AgentState)
    b.add_node("plan", plan)
    b.add_node("tools", tools)
    b.add_node("answer", answer)
    b.add_edge(START, "plan")
    b.add_edge("plan", "tools")
    b.add_edge("tools", "answer")
    b.add_edge("answer", END)
    return b


graph = build().compile()


class TickState(TypedDict):
    step: int
    window: list


def _tick_builder(n: int) -> StateGraph:
    def tick(state: TickState) -> dict:
        i = state["step"] + 1
        window = (state["window"] + [AIMessage(content=f"tick {i}", id=f"tick-{i}")])[-5:]
        return {"step": i, "window": window}

    b = StateGraph(TickState)
    b.add_node("tick", tick)
    b.add_edge(START, "tick")
    b.add_conditional_edges("tick", lambda s: "tick" if s["step"] < n else END, ["tick", END])
    return b


def make_sample_db(path: str | Path, long_checkpoints: int = 0) -> Path:
    """Write the sample threads to a fresh SQLite file and return its path.

    Threads: `lisbon-bug` (the buggy run), `lisbon-branched` (same run plus a branch made with
    update_state), and, when long_checkpoints > 0, `long-<n>` with exactly n checkpoints.
    """
    if long_checkpoints and long_checkpoints < 3:
        raise ValueError("long_checkpoints must be 0 or at least 3")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        Path(str(path) + suffix).unlink(missing_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA synchronous=OFF")  # 10x faster fixture writes; sample data only
    saver = SqliteSaver(conn)
    app = build().compile(checkpointer=saver)
    start = {"messages": [HumanMessage(content=USER_ASK, id="human-1")], "query": None, "results": []}
    app.invoke(start, {"configurable": {"thread_id": "lisbon-bug"}})
    cfg = {"configurable": {"thread_id": "lisbon-branched"}}
    app.invoke(start, cfg)
    after_tools = next(s for s in app.get_state_history(cfg) if s.metadata.get("step") == 2)
    fixed = ToolMessage(content="[]", tool_call_id="call-1", id="tool-1")
    branch_cfg = app.update_state(after_tools.config, {"messages": [fixed], "results": []}, as_node="tools")
    app.invoke(None, branch_cfg)
    if long_checkpoints:
        steps = long_checkpoints - 2  # input checkpoint + __start__ checkpoint + one per tick
        long_app = _tick_builder(steps).compile(checkpointer=saver)
        long_app.invoke(
            {"step": 0, "window": []},
            {"configurable": {"thread_id": f"long-{long_checkpoints}"}, "recursion_limit": steps + 10},
        )
    conn.close()
    return path
