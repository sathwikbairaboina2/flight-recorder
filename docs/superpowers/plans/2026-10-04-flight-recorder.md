# Flight recorder v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `langgraph-flight-recorder` v0.1: a local time-travel debugger for LangGraph SQLite checkpoints (step, diff, fork into a scratch DB) whose source file provably never changes, installable as a wheel, with a measured headline number.

**Architecture:** A Python sidecar (FastAPI on `127.0.0.1`) reads a private snapshot copy of the checkpoint DB, builds a metadata index with SQL, decodes full states with a serializer that never imports, and forks into a scratch SQLite DB using the user's graph. A React 19 + Vite 8 UI (bundled into the wheel) shows a virtualized timeline with branch lanes, a message-aware state inspector, a pure structural diff and a fork editor.

**Tech Stack:** Python 3.12, uv 0.12.21, hatchling 1.32.4, langgraph 1.2.12, langgraph-checkpoint 4.2.0, langgraph-checkpoint-sqlite 3.1.1, ormsgpack 1.12.2, fastapi 0.142.2, uvicorn 0.54.0, pytest 9.1.1, hypothesis 6.168.3, httpx 0.28.1, ruff 0.16.10. Node 24, pnpm 9.12.0, React 19.3.0, Vite 8.3.2, @vitejs/plugin-react 6.1.1, TypeScript 7.0.2, vitest 5.0.3, fast-check 4.10.2, @tanstack/react-virtual 3.14.13, @testing-library/react 16.3.3, @testing-library/user-event 14.6.7, @testing-library/jest-dom 7.0.1, jsdom 30.1.1, @playwright/test 1.63.0. Docker for the demo image.

**Spec:** `docs/superpowers/specs/2026-10-04-flight-recorder.md`. **ADRs:** `docs/adr/0001` to `0008`. **Design doc (background):** `C:\Users\sathwik\projects\taskarinchu\docs\devdocs\flight-recorder.md`. **Ledger:** `.superpowers/sdd/2026-10-04-flight-recorder/progress.md`.

## Already done (by the planner, do not redo)

- `git init -b main` in `C:\Users\sathwik\projects\taskarinchu\flight-recorder`. Git identity is configured globally.
- Spec, ADRs 0001 to 0008, this plan and the ledger are written and committed.
- Every dependency version above was checked on PyPI / npm on 2026-10-04.
- Prototypes (scratch, not in the repo) verified on 2026-10-04 on this machine:
  - A `mode=ro` open of a WAL SQLite DB creates `-wal` and `-shm` next to it (hence ADR 0001). Plain file copy of db + wal, including with a live writer holding un-checkpointed WAL frames, leaves the source dir byte-identical and the copy has all rows.
  - LangGraph's default deserializer turns an unimportable dataclass into `None` (hence ADR 0002). The `__unpack_ext_hook__` decoder in Task 4 keeps it.
  - The index rules in Task 5 give `parent_id` and `next` equal to `get_state_history` for every checkpoint of the sample threads, an `update_state` branch, and a fork.
  - The Python code blocks in Tasks 1 to 11 were run as a package: **63 tests passed in 8.5 s** (`pytest -q`), `ruff check` and `ruff format --check` clean. A wheel built with the Task 1 `pyproject.toml` contains `flight_recorder/static/**`; installed into a fresh venv, `flight-recorder demo --port 5329 --no-browser` served `/api/health`, `/api/threads` and `/`.
  - `diff.ts` in Task 13 passed 3,000 fast-check round-trip runs plus 2,000 shuffle-only-moves runs. `lanes.ts` in Task 14 gave the expected lanes for linear, branched and orphan inputs.
  - Generating a 10,000-checkpoint thread takes about 18 s with `PRAGMA synchronous=OFF` (257 s without). The SQL index over it took about 0.33 s warm.

So for Tasks 1 to 11 and 13 to 14 the code is given in full and is known to pass. Copy it exactly. Still run each test before the implementation exists and record that you saw it fail (TDD red), then add the code and see it pass.

## Global Constraints

- Work only inside `C:\Users\sathwik\projects\taskarinchu\flight-recorder`. Never edit sibling repos. Never push, never add remotes, never open PRs.
- Shells: commands below are PowerShell unless marked. `uv` and `pnpm` are on PATH. The repo root is `$R = 'C:\Users\sathwik\projects\taskarinchu\flight-recorder'`; UI commands run in `$R\ui`.
- Ports (spec table): serve/demo default **5320**, Vite dev **5321**, Playwright e2e **5322**, API bench **5323**, Docker demo host side **5324**, Playwright perf **5325**. Nothing else. Always `--strictPort` for Vite.
- Docker: image `flight-recorder:dev`, compose project `flight-recorder`, container `flight-recorder-demo`. Stop every container you start (`docker compose down`).
- Own runtime: `.venv` (uv) at the repo root and `ui/node_modules`. Do not share with other repos.
- Never invent numbers. README and DEVDOCS numbers come only from `bench/results/*.json` produced by the bench commands, quoted with the machine line those files contain.
- No secrets, no `.env` files committed.
- Each task ends with exactly one commit using the given subject, then a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Commit only after the task's tests pass. Never commit `node_modules`, `.venv`, `dist`, `src/flight_recorder/static`, `test-results`, `playwright-report`, `.bench`, `.e2e`.
- If a permission check blocks a commit, do not work around it. Write a `Ruling:` line in the ledger and continue.
- Do not ask questions. When something in this plan is wrong for the real tools, make the smallest fix that keeps the spec's behavior, and record it as a `Ruling: <what> - <why> - <cost>` line in the ledger.
- Plain short sentences in docs and UI copy. No em dash or en dash characters in UI copy, README or DEVDOCS.
- Python style: `from __future__ import annotations`, type hints, ruff line length 120. TypeScript: strict, no `any` except where a test needs a cast.

## Ledger protocol

File: `.superpowers/sdd/2026-10-04-flight-recorder/progress.md` (already created, committed).
After each task append one line: `Task N: complete (tests: <command> -> <real result line>; red seen: <yes/no and how>)`.
Decisions: `Ruling: <decision> - <reason> - <cost or none>`.
If you stop early, append `PARTIAL: next is Task N, step M` so a fresh builder can resume.

## Gates (run in Task 25, all must pass; record the real output lines in the ledger)

1. `uv run ruff check .` prints `All checks passed!`
2. `uv run ruff format --check .` prints `... files already formatted`
3. `uv run pytest -q` ends with `N passed` and no `failed` or `error`
4. `pnpm -C ui typecheck` exits 0; `pnpm -C ui test` ends with all tests passed
5. `pnpm -C ui build` writes `src/flight_recorder/static/index.html`
6. `pnpm -C ui e2e` passes (Playwright flow test)
7. `uv build` then a fresh venv install of the wheel: `flight-recorder --version` prints `flight-recorder 0.1.0`
8. `docker compose build` then `docker compose up -d`, `curl.exe -s http://127.0.0.1:5324/api/health` returns `"ok":true`, then `docker compose down`
9. `bench/results/api.json`, `bench/results/ui.json` (if Playwright perf ran), `bench/results/diff.json` exist and `uv run python bench/headline.py --check README.md` exits 0

## File map

```text
flight-recorder/
  pyproject.toml  uv.lock  .python-version  .gitignore  .gitattributes  LICENSE  README.md
  src/flight_recorder/
    __init__.py  __main__.py  cli.py  api.py  reader.py  index.py  snapshot.py
    decode.py  bridge.py  scratch.py  fork.py  graph_loader.py  samples.py
    static/            (built UI, gitignored, bundled into the wheel)
  tests/               (pytest: conftest + one file per module + immutability + compose)
  ui/
    package.json  pnpm-lock.yaml  tsconfig.json  vite.config.ts  playwright.config.ts  playwright.perf.config.ts  index.html
    src/main.tsx  src/App.tsx  src/styles.css  src/api.ts
    src/lib/diff.ts  src/lib/lanes.ts  src/lib/changed.ts  src/lib/format.ts  src/lib/tags.ts
    src/components/ThreadList.tsx  Timeline.tsx  StateInspector.tsx  JsonTree.tsx  MessageCard.tsx  DiffPanel.tsx  ForkEditor.tsx
    src/test/setup.ts  src/**/*.test.ts(x)
    bench/diff-bench.ts
    e2e/flow.spec.ts  e2e/perf.spec.ts
  bench/bench.py  bench/headline.py  bench/results/
  docs/adr/  docs/superpowers/  docs/DEVDOCS.md  docs/handoff.md  docs/img/
  Dockerfile  .dockerignore  docker-compose.yml  .github/workflows/ci.yml
```

---

### Task 1: Python scaffold

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.gitignore`, `.gitattributes`, `LICENSE`, `README.md` (stub), `src/flight_recorder/__init__.py`, `src/flight_recorder/__main__.py`, `tests/test_smoke.py`

- [ ] **Step 1: Write** `pyproject.toml`

```toml
[project]
name = "langgraph-flight-recorder"
version = "0.1.0"
description = "Time-travel debugger for LangGraph checkpoints: step, diff and fork without touching the original."
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"
keywords = ["langgraph", "debugger", "checkpoints", "agents", "time-travel"]
dependencies = [
  "langgraph>=1.2.12,<2",
  "langgraph-checkpoint>=4.2.0,<5",
  "langgraph-checkpoint-sqlite>=3.1.1,<4",
  "ormsgpack>=1.12.2",
  "fastapi>=0.142.2,<1",
  "uvicorn>=0.54.0,<1",
]

[project.scripts]
flight-recorder = "flight_recorder.cli:main_entry"

[dependency-groups]
dev = [
  "pytest==9.1.1",
  "httpx==0.28.1",
  "hypothesis==6.168.3",
  "ruff==0.16.10",
]

[build-system]
requires = ["hatchling==1.32.4"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/flight_recorder"]
artifacts = ["src/flight_recorder/static/**"]

[tool.hatch.build.targets.sdist]
artifacts = ["src/flight_recorder/static/**"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-p no:cacheprovider"

[tool.ruff]
line-length = 120
target-version = "py312"
extend-exclude = ["ui", "src/flight_recorder/static"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["flight_recorder"]
```

- [ ] **Step 2: Write the small files**

`.python-version`: `3.12`

`.gitignore`:
```text
.venv/
__pycache__/
*.pyc
dist/
build/
*.egg-info/
.pytest_cache/
.ruff_cache/
.hypothesis/
src/flight_recorder/static/
ui/node_modules/
ui/test-results/
ui/playwright-report/
.bench/
.e2e/
*.sqlite
*.sqlite-wal
*.sqlite-shm
.env*
!.env*.example
*.log
```

`.gitattributes`:
```text
* text=auto eol=lf
*.png binary
```

`LICENSE`: the standard MIT license text, `Copyright (c) 2026 Sathwik Bairaboina`.

`README.md` (stub, replaced in Task 25): `# flight-recorder` and one line `Time-travel debugger for LangGraph checkpoints. Work in progress.`

`src/flight_recorder/__init__.py`:
```python
"""Time-travel debugger for LangGraph checkpoints."""

__version__ = "0.1.0"
```

`src/flight_recorder/__main__.py`:
```python
from flight_recorder.cli import main_entry

main_entry()
```
(`cli.py` arrives in Task 11; `__main__` is not imported by tests before that.)

- [ ] **Step 3: Write the test** `tests/test_smoke.py`

```python
import flight_recorder


def test_version():
    assert flight_recorder.__version__ == "0.1.0"
```

- [ ] **Step 4: Sync and run**

```powershell
cd $R
uv sync
uv run pytest -q
uv run ruff check .
```
Expected: `uv sync` creates `.venv` and `uv.lock`; pytest prints `1 passed`; ruff prints `All checks passed!`.
(`uv run ruff check .` would report `F401`/`E402` style issues only if you deviate from the code above.)

- [ ] **Step 5: Commit** `chore: scaffold python package`

---

### Task 2: Sample agent and database generator

The sample agent has a real bug on purpose (it drops the date filter), which makes the demo story. See the module docstring.

**Files:**
- Create: `src/flight_recorder/samples.py`, `tests/conftest.py`, `tests/test_samples.py`

- [ ] **Step 1: Write** `tests/conftest.py`

```python
import hashlib
import warnings
from pathlib import Path

import pytest

from flight_recorder.samples import make_sample_db

# LangGraph warns when its own serializer meets the sample's pydantic model; that is the fork path's
# normal behavior and not what these tests check.
warnings.filterwarnings("ignore", message="Deserializing unregistered type")


@pytest.fixture
def sample_db(tmp_path: Path) -> Path:
    return make_sample_db(tmp_path / "src" / "checkpoints.sqlite")


def dir_fingerprint(folder: Path) -> dict[str, str]:
    """SHA-256 of every file in `folder`; the key set doubles as the file list."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}
```

- [ ] **Step 2: Write the failing test** `tests/test_samples.py`

```python
import sqlite3

import pytest

from flight_recorder.samples import USER_ASK, make_sample_db, search_flights


def _counts(db) -> dict[str, int]:
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT thread_id, COUNT(*) FROM checkpoints GROUP BY thread_id").fetchall()
    return dict(rows)


def test_sample_threads(sample_db):
    assert _counts(sample_db) == {"lisbon-bug": 5, "lisbon-branched": 7}


def test_long_thread_has_exact_count(tmp_path):
    db = make_sample_db(tmp_path / "c.sqlite", long_checkpoints=40)
    assert _counts(db)["long-40"] == 40


def test_long_thread_rejects_tiny_counts(tmp_path):
    with pytest.raises(ValueError):
        make_sample_db(tmp_path / "c.sqlite", long_checkpoints=2)


def test_the_bug_and_the_fix():
    assert "2026-11-01" in USER_ASK
    assert search_flights("Lisbon", None)[0]["date"] == "2026-10-28"
    assert search_flights("Lisbon", "2026-11-01")[0]["flight"] == "TP1363"


def test_regenerating_replaces_the_file(sample_db):
    make_sample_db(sample_db)
    assert _counts(sample_db) == {"lisbon-bug": 5, "lisbon-branched": 7}
```

- [ ] **Step 3: Run it and see it fail**

`uv run pytest tests/test_samples.py -q` -> `ModuleNotFoundError: No module named 'flight_recorder.samples'` (collection error).

- [ ] **Step 4: Implement** `src/flight_recorder/samples.py`

```python
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
```

- [ ] **Step 5: Run** `uv run pytest tests/test_samples.py -q` -> `5 passed`.

- [ ] **Step 6: Commit** `feat: sample flight-search agent and database generator`

---

### Task 3: Snapshot copy of the source (ADR 0001)

**Files:**
- Create: `src/flight_recorder/snapshot.py`, `tests/test_snapshot.py`

- [ ] **Step 1: Write the failing test** `tests/test_snapshot.py`

```python
import sqlite3

import pytest
from conftest import dir_fingerprint

from flight_recorder.snapshot import Snapshot


def test_copy_is_readable_and_separate(sample_db):
    snap = Snapshot(sample_db)
    try:
        assert snap.path != sample_db
        assert snap.path.parent != sample_db.parent
        with sqlite3.connect(snap.path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0] == 12
    finally:
        snap.close()


def test_opening_and_reading_leaves_source_dir_untouched(sample_db):
    before = dir_fingerprint(sample_db.parent)
    snap = Snapshot(sample_db)
    with sqlite3.connect(snap.path) as conn:
        conn.execute("SELECT * FROM checkpoints").fetchall()
    snap.refresh()
    snap.close()
    assert dir_fingerprint(sample_db.parent) == before


def test_refresh_only_when_source_changes(sample_db):
    snap = Snapshot(sample_db)
    try:
        assert snap.refresh() is False
        with sqlite3.connect(sample_db) as conn:  # the user's agent writes more
            conn.execute("DELETE FROM checkpoints WHERE thread_id = 'lisbon-bug'")
        assert snap.refresh() is True
        assert snap.generation == 1
        with sqlite3.connect(snap.path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0] == 7
    finally:
        snap.close()


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        Snapshot(tmp_path / "nope.sqlite")


def test_source_sha256_is_stable(sample_db):
    snap = Snapshot(sample_db)
    try:
        assert snap.source_sha256() == snap.source_sha256()
        assert len(snap.source_sha256()) == 64
    finally:
        snap.close()
```

- [ ] **Step 2: Run** `uv run pytest tests/test_snapshot.py -q` -> collection error, no module `flight_recorder.snapshot`.

- [ ] **Step 3: Implement** `src/flight_recorder/snapshot.py`

```python
"""Private copy of the source database so SQLite never opens the user's file (ADR 0001)."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import threading
from pathlib import Path


def _stat(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    return (st.st_size, st.st_mtime_ns)


class Snapshot:
    def __init__(self, source: str | os.PathLike[str]) -> None:
        self.source = Path(source).resolve()
        if not self.source.is_file():
            raise FileNotFoundError(f"no such database: {self.source}")
        self._wal = self.source.with_name(self.source.name + "-wal")
        self._dir = Path(tempfile.mkdtemp(prefix="flight-recorder-snap-"))
        self._lock = threading.Lock()
        self.generation = 0
        self._stamp: tuple | None = None
        self.path = self._dir / "gen0" / self.source.name
        self._copy()

    def _current_stamp(self) -> tuple:
        return (_stat(self.source), _stat(self._wal))

    def _copy(self) -> None:
        for _attempt in range(2):
            stamp = self._current_stamp()
            target_dir = self._dir / f"gen{self.generation}"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / self.source.name
            shutil.copyfile(self.source, target)
            if stamp[1] is not None:
                shutil.copyfile(self._wal, target_dir / self._wal.name)
            if self._current_stamp() == stamp:
                break
        self._stamp = stamp
        self.path = target

    def refresh(self) -> bool:
        """Re-copy if the source changed since the last copy. Returns True when a new copy was made."""
        with self._lock:
            if self._current_stamp() == self._stamp:
                return False
            self.generation += 1
            self._copy()
            return True

    def source_sha256(self) -> str:
        h = hashlib.sha256()
        with open(self.source, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def close(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)
```

- [ ] **Step 4: Run** `uv run pytest tests/test_snapshot.py -q` -> `5 passed`.

- [ ] **Step 5: Commit** `feat: read a private snapshot copy, never the source file`

---

### Task 4: Safe decoder and tagged JSON bridge (ADR 0002, spec "Bridged JSON")

**Files:**
- Create: `src/flight_recorder/decode.py`, `src/flight_recorder/bridge.py`, `tests/test_bridge.py`

- [ ] **Step 1: Write the failing test** `tests/test_bridge.py`

```python
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
```

- [ ] **Step 2: Run** `uv run pytest tests/test_bridge.py -q` -> collection error (no `flight_recorder.bridge`).

- [ ] **Step 3: Implement** `src/flight_recorder/decode.py`

```python
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
```

- [ ] **Step 4: Implement** `src/flight_recorder/bridge.py`

```python
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
```

- [ ] **Step 5: Run** `uv run pytest tests/test_bridge.py -q` -> `8 passed` (the property test runs 300 examples).

- [ ] **Step 6: Commit** `feat: decode checkpoints without imports and bridge them to tagged JSON`

---

### Task 5: Metadata index (ADR 0003, invariant 6)

**Files:**
- Create: `src/flight_recorder/index.py`, `tests/test_index.py`

- [ ] **Step 1: Write the failing test** `tests/test_index.py`

```python
"""Invariant 6: the index's parent links and next nodes equal LangGraph's own history."""

import datetime as dt
import sqlite3

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

from flight_recorder.index import SchemaError, check_schema, list_checkpoints, list_threads, uuid6_time
from flight_recorder.samples import build


def _history(db, thread_id):
    conn = sqlite3.connect(db, check_same_thread=False)
    app = build().compile(checkpointer=SqliteSaver(conn))
    out = {}
    for s in app.get_state_history({"configurable": {"thread_id": thread_id}}):
        parent = (s.parent_config or {}).get("configurable", {}).get("checkpoint_id")
        out[s.config["configurable"]["checkpoint_id"]] = (parent, sorted(s.next), s.created_at)
    conn.close()
    return out


@pytest.mark.parametrize("thread_id", ["lisbon-bug", "lisbon-branched"])
def test_parent_links_match_state_history(sample_db, thread_id):
    truth = _history(sample_db, thread_id)
    with sqlite3.connect(sample_db) as conn:
        rows = list_checkpoints(conn, thread_id)
    assert len(rows) == len(truth)
    for r in rows:
        parent, nxt, created = truth[r["checkpoint_id"]]
        assert r["parent_id"] == parent
        assert r["next"] == nxt
        gap = abs(dt.datetime.fromisoformat(r["created_at"]) - dt.datetime.fromisoformat(created))
        assert gap < dt.timedelta(milliseconds=5)


def test_rows_are_oldest_first_with_writers(sample_db):
    with sqlite3.connect(sample_db) as conn:
        rows = list_checkpoints(conn, "lisbon-bug")
    assert [r["step"] for r in rows] == [-1, 0, 1, 2, 3]
    assert [r["source"] for r in rows] == ["input", "loop", "loop", "loop", "loop"]
    assert [r["writes_from"] for r in rows] == [[], ["__start__"], ["plan"], ["tools"], ["answer"]]
    assert [r["next"] for r in rows] == [["__start__"], ["plan"], ["tools"], ["answer"], []]
    assert all(r["state_bytes"] > 0 for r in rows)


def test_branch_has_an_update_row(sample_db):
    with sqlite3.connect(sample_db) as conn:
        rows = list_checkpoints(conn, "lisbon-branched")
    update = next(r for r in rows if r["source"] == "update")
    assert update["next"] == ["answer"]
    assert update["writes_from"] == []
    parents = [r["parent_id"] for r in rows]
    assert parents.count(update["parent_id"]) == 2  # the branch point has two children


def test_threads_summary(sample_db):
    with sqlite3.connect(sample_db) as conn:
        threads = list_threads(conn)
    by_id = {t["thread_id"]: t for t in threads}
    assert by_id["lisbon-bug"]["checkpoint_count"] == 5
    assert by_id["lisbon-branched"]["namespaces"] == [""]
    assert threads[0]["last_at"] >= threads[1]["last_at"]


def test_uuid6_time_known_value():
    assert uuid6_time("1f1bf756-229e-6563-8003-d41065ca3b5a") == "2026-10-03T21:57:10.418774Z"


def test_check_schema_rejects_foreign_db(tmp_path):
    conn = sqlite3.connect(tmp_path / "x.sqlite")
    conn.execute("CREATE TABLE checkpoints (thread_id TEXT)")
    with pytest.raises(SchemaError, match="missing columns"):
        check_schema(conn)
    conn.close()


def test_unknown_thread_is_empty(sample_db):
    with sqlite3.connect(sample_db) as conn:
        assert list_checkpoints(conn, "nope") == []
```

- [ ] **Step 2: Run** `uv run pytest tests/test_index.py -q` -> collection error.

- [ ] **Step 3: Implement** `src/flight_recorder/index.py`

```python
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
```

- [ ] **Step 4: Run** `uv run pytest tests/test_index.py -q` -> `8 passed`.

- [ ] **Step 5: Commit** `feat: sql metadata index with next nodes and writers`

---

### Task 6: Scratch store, reader, and the never-imports proof (invariant 8)

**Files:**
- Create: `src/flight_recorder/scratch.py`, `src/flight_recorder/reader.py`, `tests/test_reader.py`, `tests/test_decode.py`

- [ ] **Step 1: Write the failing tests** `tests/test_reader.py` and `tests/test_decode.py`

```python
import pytest

from flight_recorder.reader import NotFound, Reader
from flight_recorder.snapshot import Snapshot


@pytest.fixture
def reader(sample_db):
    snap = Snapshot(sample_db)
    yield Reader(snap)
    snap.close()


def test_threads_have_origin(reader):
    threads = reader.threads()
    assert {t["thread_id"] for t in threads} == {"lisbon-bug", "lisbon-branched"}
    assert all(t["origin"] == "source" and t["fork_of"] is None for t in threads)


def test_state_is_bridged(reader):
    rows = reader.checkpoints("lisbon-bug")
    plan_row = next(r for r in rows if r["writes_from"] == ["plan"])
    st = reader.state("lisbon-bug", plan_row["checkpoint_id"])
    assert st["next"] == ["tools"]
    assert st["values"]["query"] == {
        "__pydantic__": "flight_recorder.samples.SearchQuery",
        "fields": {"destination": "Lisbon", "depart_after": None},
    }
    ai = st["values"]["messages"][-1]
    assert ai["__lc_message__"] == "ai"
    assert ai["tool_calls"][0]["args"]["depart_after"] is None
    assert st["metadata"]["source"] == "loop"


def test_pending_writes_are_listed(reader):
    first = reader.checkpoints("lisbon-bug")[0]
    st = reader.state("lisbon-bug", first["checkpoint_id"])
    assert {w["channel"] for w in st["pending_writes"]} >= {"messages"}


def test_not_found(reader):
    with pytest.raises(NotFound):
        reader.checkpoints("nope")
    with pytest.raises(NotFound):
        reader.state("lisbon-bug", "nope")


def test_index_is_cached_per_generation(reader):
    assert reader.checkpoints("lisbon-bug") is reader.checkpoints("lisbon-bug")
```

```python
"""ADR 0002: the read path decodes everything and imports nothing."""

import subprocess
import sys
import textwrap

from flight_recorder.reader import Reader
from flight_recorder.snapshot import Snapshot

CANARY = textwrap.dedent(
    """
    import pathlib, dataclasses, pydantic
    pathlib.Path(__file__).with_name("IMPORTED").write_text("canary module was imported")

    @dataclasses.dataclass
    class Box:
        label: str

    class Card(pydantic.BaseModel):
        n: int
    """
)
WRITER = textwrap.dedent(
    """
    import sqlite3, sys
    from typing import Any, TypedDict
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph
    import fr_canary_mod as m

    class S(TypedDict):
        v: Any

    b = StateGraph(S)
    b.add_node("n", lambda s: {"v": {"box": m.Box(label="x"), "card": m.Card(n=3)}})
    b.add_edge(START, "n")
    b.add_edge("n", END)
    conn = sqlite3.connect(sys.argv[1], check_same_thread=False)
    b.compile(checkpointer=SqliteSaver(conn)).invoke({"v": None}, {"configurable": {"thread_id": "t"}})
    conn.close()
    """
)


def _write_canary_db(tmp_path):
    mod_dir = tmp_path / "mod"
    mod_dir.mkdir()
    (mod_dir / "fr_canary_mod.py").write_text(CANARY)
    db = tmp_path / "db" / "c.sqlite"
    db.parent.mkdir()
    env_path = str(mod_dir)
    subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, {env_path!r}); exec({WRITER!r})", str(db)],
        check=True,
    )
    (mod_dir / "IMPORTED").unlink()  # the writer imported it; the reader must not
    return db, mod_dir


def test_reading_never_imports(tmp_path, monkeypatch):
    db, mod_dir = _write_canary_db(tmp_path)
    monkeypatch.syspath_prepend(str(mod_dir))  # importing would succeed, so only our decoder can prevent it
    snap = Snapshot(db)
    try:
        reader = Reader(snap)
        rows = reader.checkpoints("t")
        values = reader.state("t", rows[-1]["checkpoint_id"])["values"]
    finally:
        snap.close()
    assert not (mod_dir / "IMPORTED").exists()
    assert "fr_canary_mod" not in sys.modules
    assert values["v"]["box"] == {"__object__": "fr_canary_mod.Box", "fields": {"label": "x"}}
    assert values["v"]["card"] == {"__pydantic__": "fr_canary_mod.Card", "fields": {"n": 3}}


def test_dataclass_from_missing_module_is_not_dropped(tmp_path):
    db, mod_dir = _write_canary_db(tmp_path)
    (mod_dir / "fr_canary_mod.py").unlink()  # module gone entirely
    snap = Snapshot(db)
    try:
        reader = Reader(snap)
        rows = reader.checkpoints("t")
        values = reader.state("t", rows[-1]["checkpoint_id"])["values"]
    finally:
        snap.close()
    assert values["v"]["box"]["fields"] == {"label": "x"}
```

- [ ] **Step 2: Run** `uv run pytest tests/test_reader.py tests/test_decode.py -q` -> collection errors.

- [ ] **Step 3: Implement** `src/flight_recorder/scratch.py`

```python
"""The scratch database where forks live: SqliteSaver tables plus fr_forks provenance (ADR 0005)."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

_FORKS_DDL = """
CREATE TABLE IF NOT EXISTS fr_forks (
  fork_id TEXT PRIMARY KEY,
  source_db_sha256 TEXT NOT NULL,
  source_thread_id TEXT NOT NULL,
  source_checkpoint_id TEXT NOT NULL,
  scratch_thread_id TEXT NOT NULL UNIQUE,
  as_node TEXT,
  values_json TEXT NOT NULL,
  created_at TEXT NOT NULL
)
"""


class ScratchStore:
    """The scratch SQLite database: SqliteSaver tables plus fr_forks."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.saver = SqliteSaver(self.conn)
        self.saver.setup()
        self.conn.execute(_FORKS_DDL)
        self.conn.commit()

    def forks(self) -> list[dict]:
        cols = ["fork_id", "source_thread_id", "source_checkpoint_id", "scratch_thread_id", "as_node", "created_at"]
        with self.lock:
            rows = self.conn.execute(f"SELECT {', '.join(cols)} FROM fr_forks ORDER BY created_at").fetchall()
        return [dict(zip(cols, r, strict=True)) for r in rows]

    def thread_ids(self) -> set[str]:
        return {f["scratch_thread_id"] for f in self.forks()}

    def close(self) -> None:
        self.conn.close()
```

- [ ] **Step 4: Implement** `src/flight_recorder/reader.py`

```python
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
```

- [ ] **Step 5: Run** `uv run pytest tests/test_reader.py tests/test_decode.py -q` -> `7 passed`.

- [ ] **Step 6: Commit** `feat: reader over snapshot and scratch, proven never to import`

---

### Task 7: Graph loader

**Files:**
- Create: `src/flight_recorder/graph_loader.py`, `tests/test_graph_loader.py`

- [ ] **Step 1: Write the failing test** `tests/test_graph_loader.py`

```python
import pytest
from langgraph.graph import StateGraph

from flight_recorder.graph_loader import GraphLoadError, load_builder, topology


def test_loads_compiled_graph():
    assert isinstance(load_builder("flight_recorder.samples:graph"), StateGraph)


def test_loads_uncompiled_builder(tmp_path):
    (tmp_path / "fr_user_graph.py").write_text(
        "from flight_recorder.samples import build\nbuilder = build()\nnot_a_graph = 3\n"
    )
    assert isinstance(load_builder("fr_user_graph:builder", cwd=tmp_path), StateGraph)
    with pytest.raises(GraphLoadError, match="not a StateGraph"):
        load_builder("fr_user_graph:not_a_graph", cwd=tmp_path)


@pytest.mark.parametrize("spec", ["no_colon", "missing_mod_xyz:graph", "flight_recorder.samples:nope"])
def test_bad_specs(spec):
    with pytest.raises(GraphLoadError):
        load_builder(spec)


def test_topology():
    topo = topology(load_builder("flight_recorder.samples:graph"))
    assert topo["nodes"] == ["__start__", "plan", "tools", "answer", "__end__"]
    assert {"source": "plan", "target": "tools", "conditional": False} in topo["edges"]
```

- [ ] **Step 2: Run** -> collection error.

- [ ] **Step 3: Implement** `src/flight_recorder/graph_loader.py`

```python
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
```

- [ ] **Step 4: Run** `uv run pytest tests/test_graph_loader.py -q` -> `6 passed`.

- [ ] **Step 5: Commit** `feat: load user graphs by module:attr`

---

### Task 8: Fork engine (ADR 0004, ADR 0005, invariant 2)

**Files:**
- Create: `src/flight_recorder/fork.py`, `tests/test_fork.py`

- [ ] **Step 1: Write the failing test** `tests/test_fork.py`

```python
import sqlite3

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from flight_recorder.fork import FORK_PREFIX, ForkEngine, ForkError, new_fork_thread_id
from flight_recorder.graph_loader import load_builder
from flight_recorder.reader import Reader
from flight_recorder.scratch import ScratchStore
from flight_recorder.snapshot import Snapshot


@pytest.fixture
def env(sample_db, tmp_path):
    snap = Snapshot(sample_db)
    store = ScratchStore(tmp_path / "scratch" / "scratch.sqlite")
    engine = ForkEngine(load_builder("flight_recorder.samples:graph"), store, snap.source_sha256())
    reader = Reader(snap, store)
    yield snap, store, engine, reader
    store.close()
    snap.close()


def _plan_step(reader):
    rows = reader.checkpoints("lisbon-bug")
    row = next(r for r in rows if r["writes_from"] == ["plan"])
    return row, reader.state("lisbon-bug", row["checkpoint_id"])["values"]


def _fixed_messages(values):
    msgs = values["messages"]
    msgs[-1]["tool_calls"][0]["args"]["depart_after"] = "2026-11-01"
    return msgs


def test_fork_with_the_date_restored_finds_the_november_flight(env):
    snap, store, engine, reader = env
    row, values = _plan_step(reader)
    res = engine.fork(
        snap.path, "lisbon-bug", row["checkpoint_id"], {"messages": _fixed_messages(values)}, "plan", set()
    )
    assert res["status"] == "done", res["error"]
    assert res["thread_id"].startswith(FORK_PREFIX)
    assert [e["node"] for e in res["events"]] == ["tools", "answer"]
    assert res["events"][-1]["update"]["messages"][0]["content"] == "Cheapest: TP1363 on 2026-11-03 for EUR 142."
    assert res["elapsed_ms"] > 0


def test_fork_thread_is_listed_with_copied_rows_marked(env):
    snap, store, engine, reader = env
    row, values = _plan_step(reader)
    res = engine.fork(
        snap.path, "lisbon-bug", row["checkpoint_id"], {"messages": _fixed_messages(values)}, "plan", set()
    )
    forked = next(t for t in reader.threads() if t["thread_id"] == res["thread_id"])
    assert forked["origin"] == "scratch"
    assert forked["fork_of"] == {"thread_id": "lisbon-bug", "checkpoint_id": row["checkpoint_id"]}
    rows = reader.checkpoints(res["thread_id"])
    assert [(r["step"], r["origin"]) for r in rows] == [
        (-1, "source"), (0, "source"), (1, "source"), (2, "scratch"), (3, "scratch"), (4, "scratch"),
    ]  # fmt: skip
    assert rows[-1]["checkpoint_id"] == res["head_checkpoint_id"]


def test_provenance_row(env):
    snap, store, engine, reader = env
    row, values = _plan_step(reader)
    res = engine.fork(snap.path, "lisbon-bug", row["checkpoint_id"], {}, "plan", set())
    with sqlite3.connect(store.path) as conn:
        rec = conn.execute(
            "SELECT source_db_sha256, source_thread_id, source_checkpoint_id, as_node FROM fr_forks WHERE fork_id = ?",
            (res["fork_id"],),
        ).fetchone()
    assert rec == (snap.source_sha256(), "lisbon-bug", row["checkpoint_id"], "plan")


def test_a_failing_node_gives_status_error_and_keeps_the_fork(env):
    snap, store, engine, reader = env
    row, values = _plan_step(reader)
    broken = values["messages"]
    broken[-1]["tool_calls"] = []  # tools node will index an empty list
    res = engine.fork(snap.path, "lisbon-bug", row["checkpoint_id"], {"messages": broken}, "plan", set())
    assert res["status"] == "error"
    assert "IndexError" in res["error"]
    assert res["thread_id"] in {t["thread_id"] for t in reader.threads()}


def test_bad_values(env):
    snap, store, engine, reader = env
    row, _ = _plan_step(reader)
    with pytest.raises(ForkError):
        engine.fork(
            snap.path, "lisbon-bug", row["checkpoint_id"], {"x": {"__unrepresentable__": "a", "repr": "b"}}, None, set()
        )
    with pytest.raises(ForkError):
        engine.fork(snap.path, "lisbon-bug", row["checkpoint_id"], ["not", "a", "dict"], None, set())  # type: ignore[arg-type]


@settings(max_examples=200, deadline=None)
@given(st.sets(st.one_of(st.text(max_size=12), st.text(max_size=8).map(lambda s: FORK_PREFIX + s)), max_size=20))
def test_fork_thread_namespace(source_ids):
    _, thread_id = new_fork_thread_id(source_ids)
    assert thread_id not in source_ids
    assert thread_id.startswith(FORK_PREFIX)


def test_forced_clash_is_regenerated():
    ids = iter(["aaa", "aaa", "bbb"])
    fork_id, thread_id = new_fork_thread_id({"fork:aaa"}, make_id=lambda: next(ids))
    assert (fork_id, thread_id) == ("bbb", "fork:bbb")
```

- [ ] **Step 2: Run** -> collection error.

- [ ] **Step 3: Implement** `src/flight_recorder/fork.py`

```python
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
```

- [ ] **Step 4: Run** `uv run pytest tests/test_fork.py -q` -> `7 passed`. One LangGraph log line `Deserializing unregistered type flight_recorder.samples.SearchQuery` is expected on the fork path; it is LangGraph's own serializer warning, not an error.

- [ ] **Step 5: Commit** `feat: fork into a scratch database and run to completion`

---

### Task 9: Immutability proof (invariant 1)

**Files:**
- Create: `tests/test_immutability.py`

- [ ] **Step 1: Write** `tests/test_immutability.py`

```python
"""Invariant 1: reads and forks never change a byte in the source directory (ADR 0001)."""

import sqlite3
from typing import TypedDict

from conftest import dir_fingerprint
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from flight_recorder.fork import ForkEngine
from flight_recorder.graph_loader import load_builder
from flight_recorder.reader import Reader
from flight_recorder.scratch import ScratchStore
from flight_recorder.snapshot import Snapshot


def test_source_db_unchanged(sample_db, tmp_path):
    before = dir_fingerprint(sample_db.parent)
    snap = Snapshot(sample_db)
    store = ScratchStore(tmp_path / "scratch.sqlite")
    reader = Reader(snap, store)
    engine = ForkEngine(load_builder("flight_recorder.samples:graph"), store, snap.source_sha256())
    for t in reader.threads():
        for row in reader.checkpoints(t["thread_id"]):
            reader.state(t["thread_id"], row["checkpoint_id"])
    plan_row = next(r for r in reader.checkpoints("lisbon-bug") if r["writes_from"] == ["plan"])
    for _ in range(5):
        res = engine.fork(snap.path, "lisbon-bug", plan_row["checkpoint_id"], {}, "plan", set())
        assert res["status"] == "done"
    store.close()
    snap.close()
    assert dir_fingerprint(sample_db.parent) == before


class S(TypedDict):
    x: int


def test_live_writer_with_uncheckpointed_wal(tmp_path):
    src = tmp_path / "live"
    src.mkdir()
    db = src / "live.sqlite"
    b = StateGraph(S)
    b.add_node("n", lambda s: {"x": s["x"] + 1})
    b.add_edge(START, "n")
    b.add_edge("n", END)
    writer = sqlite3.connect(db, check_same_thread=False)
    b.compile(checkpointer=SqliteSaver(writer)).invoke({"x": 0}, {"configurable": {"thread_id": "live"}})
    try:
        assert (src / "live.sqlite-wal").exists()  # the writer is still open, so the WAL holds the data
        before = dir_fingerprint(src)
        snap = Snapshot(db)
        reader = Reader(snap)
        assert reader.threads()[0]["checkpoint_count"] == 3
        snap.close()
        assert dir_fingerprint(src) == before
    finally:
        writer.close()
```

- [ ] **Step 2: Prove the test can fail.** Temporarily change `Snapshot._copy` to `target = self.source` (read the source in place) and run `uv run pytest tests/test_immutability.py -q`. Expected: `test_live_writer_with_uncheckpointed_wal` or `test_source_db_unchanged` fails because a `-shm`/`-wal` appears or changes, or fork writes land in the scratch file only (record exactly what you saw in the ledger; if neither fails on this OS, write `Ruling: red not observable on <OS> because <reason>`). Revert the change.

- [ ] **Step 3: Run** `uv run pytest tests/test_immutability.py -q` -> `2 passed`.

- [ ] **Step 4: Commit** `test: prove the source directory is byte-identical after reads and forks`

---

### Task 10: REST API

**Files:**
- Create: `src/flight_recorder/api.py`, `tests/test_api.py`

- [ ] **Step 1: Write the failing test** `tests/test_api.py`

```python
import pytest
from fastapi.testclient import TestClient

from flight_recorder.api import create_app
from flight_recorder.fork import ForkEngine
from flight_recorder.graph_loader import load_builder, topology
from flight_recorder.reader import Reader
from flight_recorder.scratch import ScratchStore
from flight_recorder.snapshot import Snapshot


@pytest.fixture
def client(sample_db, tmp_path):
    snap = Snapshot(sample_db)
    store = ScratchStore(tmp_path / "scratch.sqlite")
    builder = load_builder("flight_recorder.samples:graph")
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>flight-recorder</title>")
    app = create_app(Reader(snap, store), ForkEngine(builder, store, snap.source_sha256()), topology(builder), static)
    yield TestClient(app)
    store.close()
    snap.close()


@pytest.fixture
def read_only_client(sample_db):
    snap = Snapshot(sample_db)
    yield TestClient(create_app(Reader(snap)))
    snap.close()


def test_health(client):
    assert client.get("/api/health").json() == {
        "ok": True, "version": "0.1.0", "graph": True, "source": "checkpoints.sqlite",
    }  # fmt: skip


def test_read_endpoints(client):
    threads = client.get("/api/threads").json()
    assert {t["thread_id"] for t in threads} == {"lisbon-bug", "lisbon-branched"}
    rows = client.get("/api/threads/lisbon-bug/checkpoints").json()
    assert len(rows) == 5 and rows[0]["origin"] == "source"
    st = client.get(f"/api/threads/lisbon-bug/checkpoints/{rows[-1]['checkpoint_id']}").json()
    assert st["values"]["messages"][-1]["content"] == "Cheapest: TP1351 on 2026-10-28 for EUR 89."


def test_static_ui_is_served(client):
    assert "flight-recorder" in client.get("/").text


def test_fork_endpoint(client):
    rows = client.get("/api/threads/lisbon-bug/checkpoints").json()
    plan = next(r for r in rows if r["writes_from"] == ["plan"])
    values = client.get(f"/api/threads/lisbon-bug/checkpoints/{plan['checkpoint_id']}").json()["values"]
    values["messages"][-1]["tool_calls"][0]["args"]["depart_after"] = "2026-11-01"
    body = {
        "thread_id": "lisbon-bug",
        "checkpoint_id": plan["checkpoint_id"],
        "values": {"messages": values["messages"]},
        "as_node": "plan",
    }
    res = client.post("/api/forks", json=body).json()
    assert res["status"] == "done"
    head = client.get(f"/api/threads/{res['thread_id']}/checkpoints/{res['head_checkpoint_id']}").json()
    assert head["values"]["messages"][-1]["content"] == "Cheapest: TP1363 on 2026-11-03 for EUR 142."
    again = client.post("/api/forks", json={**body, "thread_id": res["thread_id"], "values": {}}).json()
    assert again["status"] == "done"  # forking a fork reads from the scratch database


def test_error_codes(client, read_only_client):
    rows = client.get("/api/threads/lisbon-bug/checkpoints").json()
    cid = rows[1]["checkpoint_id"]
    assert client.get("/api/threads/nope/checkpoints").status_code == 404
    assert client.get("/api/threads/lisbon-bug/checkpoints/nope").status_code == 404
    assert client.post("/api/forks", json={"thread_id": "nope", "checkpoint_id": cid, "values": {}}).status_code == 404
    assert (
        client.post("/api/forks", json={"thread_id": "lisbon-bug", "checkpoint_id": "x", "values": {}}).status_code
        == 404
    )
    bad = {"thread_id": "lisbon-bug", "checkpoint_id": cid, "values": {"x": {"__unrepresentable__": "a", "repr": "b"}}}
    assert client.post("/api/forks", json=bad).status_code == 422
    assert (
        read_only_client.post(
            "/api/forks", json={"thread_id": "lisbon-bug", "checkpoint_id": cid, "values": {}}
        ).status_code
        == 400
    )
    assert read_only_client.get("/api/graph").status_code == 404
    assert client.get("/api/graph").json()["nodes"][1] == "plan"
```

- [ ] **Step 2: Run** -> collection error.

- [ ] **Step 3: Implement** `src/flight_recorder/api.py`

```python
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

    @app.get("/api/threads/{thread_id}/checkpoints")
    def checkpoints(thread_id: str, ns: str = "") -> list[dict]:
        try:
            return reader.checkpoints(thread_id, ns)
        except NotFound as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/threads/{thread_id}/checkpoints/{checkpoint_id}")
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
```

- [ ] **Step 4: Run** `uv run pytest tests/test_api.py -q` -> `5 passed`.

- [ ] **Step 5: Commit** `feat: rest api for threads, checkpoints, state, graph and forks`

---

### Task 11: CLI (invariant 7)

**Files:**
- Create: `src/flight_recorder/cli.py`, `tests/test_cli.py`

- [ ] **Step 1: Write the failing test** `tests/test_cli.py`

```python
"""Invariant 7 (local only) and the doctor command."""

import json
import sqlite3

import pytest

from flight_recorder.cli import DEFAULT_PORT, UsageError, build_parser, check_host, main


def test_defaults_are_loopback_and_5320():
    args = build_parser().parse_args(["serve", "--db", "x.sqlite"])
    assert args.host == "127.0.0.1"
    assert args.port == DEFAULT_PORT == 5320


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_hosts_are_allowed(host):
    check_host(host, acknowledged=False)


def test_public_host_needs_the_flag():
    with pytest.raises(UsageError):
        check_host("0.0.0.0", acknowledged=False)
    check_host("0.0.0.0", acknowledged=True)


def test_serve_refuses_public_host(sample_db, capsys):
    assert main(["serve", "--db", str(sample_db), "--host", "0.0.0.0", "--no-browser"]) == 2
    assert "--i-know-this-is-unauthenticated" in capsys.readouterr().err


def test_doctor(sample_db, capsys):
    assert main(["doctor", "--db", str(sample_db)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == "ok"
    assert report["threads"] == 2
    assert report["checkpoints_read"] == 12
    assert report["unrepresentable_values"] == 0
    assert report["langgraph"].startswith("1.")


def test_doctor_on_foreign_db(tmp_path, capsys):
    db = tmp_path / "x.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE t (a)")
    assert main(["doctor", "--db", str(db)]) == 1
    assert "missing columns" in capsys.readouterr().err


def test_missing_db(tmp_path, capsys):
    assert main(["doctor", "--db", str(tmp_path / "nope.sqlite")]) == 1


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "flight-recorder 0.1.0" in capsys.readouterr().out
```

- [ ] **Step 2: Run** -> collection error.

- [ ] **Step 3: Implement** `src/flight_recorder/cli.py`

```python
"""`flight-recorder` command line: serve, demo, doctor (ADR 0007 for the host rules)."""

from __future__ import annotations

import argparse
import atexit
import json
import shutil
import sys
import tempfile
import threading
import webbrowser
from collections.abc import Sequence
from importlib.metadata import version as dist_version
from pathlib import Path
from typing import Any

from . import __version__

DEFAULT_PORT = 5320
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
STATIC_DIR = Path(__file__).parent / "static"
SAMPLE_GRAPH = "flight_recorder.samples:graph"


class UsageError(Exception):
    pass


def check_host(host: str, acknowledged: bool) -> None:
    if host not in LOOPBACK and not acknowledged:
        raise UsageError(
            f"refusing to bind {host}: the server has no auth. "
            "Pass --i-know-this-is-unauthenticated if you really mean it (for example inside Docker)."
        )


def _add_server_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--i-know-this-is-unauthenticated", dest="ack", action="store_true")
    p.add_argument("--scratch", help="keep forks in this SQLite file (default: a temp file removed at exit)")
    p.add_argument("--no-browser", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flight-recorder", description="Time-travel debugger for LangGraph")
    parser.add_argument("--version", action="version", version=f"flight-recorder {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="open a checkpoint database")
    serve.add_argument("--db", required=True)
    serve.add_argument("--graph", help="module:attr of your StateGraph, needed for forks")
    _add_server_args(serve)
    demo = sub.add_parser("demo", help="write the sample database and serve it")
    demo.add_argument("--dir", help="where to write checkpoints.sqlite (default: a temp dir)")
    demo.add_argument("--long", type=int, default=0, help="also write a long-<N> thread with N checkpoints")
    _add_server_args(demo)
    doctor = sub.add_parser("doctor", help="check a database and print what the reader sees")
    doctor.add_argument("--db", required=True)
    return parser


def build_app(db: str, graph: str | None, scratch: str | None) -> tuple[Any, list]:
    """Create the FastAPI app. Returns (app, closers)."""
    from .api import create_app
    from .fork import ForkEngine
    from .graph_loader import load_builder, topology
    from .reader import Reader
    from .scratch import ScratchStore
    from .snapshot import Snapshot

    snapshot = Snapshot(db)
    closers: list = [snapshot.close]
    store = engine = topo = None
    if graph:
        builder = load_builder(graph)
        if scratch:
            scratch_path = Path(scratch)
        else:
            tmp = Path(tempfile.mkdtemp(prefix="flight-recorder-scratch-"))
            scratch_path = tmp / "scratch.sqlite"
            closers.append(lambda: shutil.rmtree(tmp, ignore_errors=True))
        store = ScratchStore(scratch_path)
        closers.insert(0, store.close)
        engine = ForkEngine(builder, store, snapshot.source_sha256())
        topo = topology(builder)
    reader = Reader(snapshot, store)
    return create_app(reader, engine, topo, STATIC_DIR), closers


def _serve(args: argparse.Namespace, db: str, graph: str | None) -> int:
    import uvicorn

    check_host(args.host, args.ack)
    app, closers = build_app(db, graph, args.scratch)
    for close in closers:
        atexit.register(close)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"flight-recorder {__version__} serving {db} at {url}", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def doctor(db: str) -> dict:
    from .reader import Reader
    from .snapshot import Snapshot

    snapshot = Snapshot(db)
    try:
        reader = Reader(snapshot)  # raises SchemaError (a RuntimeError) on a foreign database
        threads = reader.threads()
        states = unrepresentable = 0
        for t in threads:
            for row in reader.checkpoints(t["thread_id"]):
                st = reader.state(t["thread_id"], row["checkpoint_id"])
                states += 1
                unrepresentable += json.dumps(st["values"]).count('"__unrepresentable__"')
        return {
            "flight_recorder": __version__,
            "langgraph": dist_version("langgraph"),
            "langgraph_checkpoint": dist_version("langgraph-checkpoint"),
            "langgraph_checkpoint_sqlite": dist_version("langgraph-checkpoint-sqlite"),
            "schema": "ok",
            "threads": len(threads),
            "checkpoints_read": states,
            "unrepresentable_values": unrepresentable,
        }
    finally:
        snapshot.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            return _serve(args, args.db, args.graph)
        if args.command == "demo":
            from .samples import make_sample_db

            folder = Path(args.dir) if args.dir else Path(tempfile.mkdtemp(prefix="flight-recorder-demo-"))
            db = make_sample_db(folder / "checkpoints.sqlite", long_checkpoints=args.long)
            return _serve(args, str(db), SAMPLE_GRAPH)
        if args.command == "doctor":
            print(json.dumps(doctor(args.db), indent=2))
            return 0
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


def main_entry() -> None:
    sys.exit(main())
```

- [ ] **Step 4: Run the whole suite and lint**

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```
Expected: `64 passed` (63 from the reference run plus `test_smoke`; record the real line), `All checks passed!`, `... files already formatted`.

- [ ] **Step 5: Manual smoke (real server)**

```powershell
Start-Process -NoNewWindow uv -ArgumentList 'run','flight-recorder','demo','--dir','.e2e\smoke','--port','5320','--no-browser' -RedirectStandardOutput .e2e\smoke.log
Start-Sleep -Seconds 6
curl.exe -s http://127.0.0.1:5320/api/health
curl.exe -s http://127.0.0.1:5320/api/threads
Get-Process flight-recorder -ErrorAction SilentlyContinue | Stop-Process -Force
```
Expected: health JSON with `"graph":true`; threads JSON lists `lisbon-bug` and `lisbon-branched`. `/` returns 404 until the UI is built (Task 20). Stop the process.

- [ ] **Step 6: Commit** `feat: cli with serve, demo and doctor; loopback by default`

---

### Task 12: UI scaffold and API client

**Files:**
- Create: `ui/package.json`, `ui/tsconfig.json`, `ui/vite.config.ts`, `ui/vitest.config.ts`, `ui/index.html`, `ui/src/main.tsx`, `ui/src/App.tsx` (placeholder), `ui/src/styles.css` (empty for now), `ui/src/api.ts`, `ui/src/test/setup.ts`, `ui/src/api.test.ts`
- Generates: `ui/pnpm-lock.yaml`

- [ ] **Step 1: Write** `ui/package.json` (exact versions, checked 2026-10-04)

```json
{
  "name": "flight-recorder-ui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "packageManager": "pnpm@9.12.0",
  "engines": { "node": ">=24" },
  "scripts": {
    "dev": "vite --port 5321 --strictPort",
    "build": "pnpm typecheck && vite build",
    "typecheck": "tsc -p tsconfig.json --noEmit",
    "test": "vitest run",
    "e2e": "pnpm build && playwright test",
    "perf": "pnpm build && playwright test -c playwright.perf.config.ts",
    "bench:diff": "node bench/diff-bench.ts"
  },
  "dependencies": {
    "@tanstack/react-virtual": "3.14.13",
    "react": "19.3.0",
    "react-dom": "19.3.0"
  },
  "devDependencies": {
    "@playwright/test": "1.63.0",
    "@testing-library/jest-dom": "7.0.1",
    "@testing-library/react": "16.3.3",
    "@testing-library/user-event": "14.6.7",
    "@types/node": "26.6.4",
    "@types/react": "19.3.0",
    "@types/react-dom": "19.3.0",
    "@vitejs/plugin-react": "6.1.1",
    "fast-check": "4.10.2",
    "jsdom": "30.1.1",
    "typescript": "7.0.2",
    "vite": "8.3.2",
    "vitest": "5.0.3"
  }
}
```

- [ ] **Step 2: Write the config files**

`ui/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "resolveJsonModule": true,
    "allowImportingTsExtensions": true,
    "types": ["vite/client", "node"]
  },
  "include": ["src", "bench", "e2e", "vite.config.ts", "vitest.config.ts", "playwright.config.ts", "playwright.perf.config.ts"]
}
```

`ui/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The build lands inside the Python package so the wheel serves it (ADR 0008).
export default defineConfig({
  plugins: [react()],
  build: { outDir: '../src/flight_recorder/static', emptyOutDir: true },
  server: { port: 5321, strictPort: true, proxy: { '/api': 'http://127.0.0.1:5320' } },
})
```

`ui/vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', setupFiles: ['src/test/setup.ts'], include: ['src/**/*.test.{ts,tsx}'] },
})
```

`ui/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="color-scheme" content="dark light" />
    <title>flight-recorder</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`ui/src/main.tsx`:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

`ui/src/App.tsx` (placeholder until Task 19): `export function App() { return <h1>flight-recorder</h1> }`

`ui/src/test/setup.ts`:
```ts
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => cleanup())

// jsdom has no ResizeObserver; TanStack Virtual only needs the methods to exist.
class NoopResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= NoopResizeObserver as unknown as typeof ResizeObserver
```

- [ ] **Step 3: Write the failing test** `ui/src/api.test.ts`

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from './api'

function stubFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } }))
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('builds encoded urls', async () => {
    const fn = stubFetch(200, [])
    await api.checkpoints('fork:abc', '')
    expect(fn).toHaveBeenCalledWith('/api/threads/fork%3Aabc/checkpoints?ns=', undefined)
  })

  it('posts forks as json', async () => {
    const fn = stubFetch(200, { status: 'done' })
    await api.fork({ thread_id: 't', checkpoint_id: 'c', values: { a: 1 }, as_node: 'plan' })
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/forks')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ thread_id: 't', checkpoint_id: 'c', values: { a: 1 }, as_node: 'plan' })
  })

  it('turns error responses into ApiError with the server detail', async () => {
    stubFetch(404, { detail: 'thread nope has no checkpoints' })
    await expect(api.threads()).rejects.toMatchObject({ status: 404, message: 'thread nope has no checkpoints' })
    await expect(api.threads()).rejects.toBeInstanceOf(ApiError)
  })
})
```

- [ ] **Step 4: Install and see it fail**

```powershell
cd $R\ui
pnpm install
pnpm test
```
Expected: install creates `pnpm-lock.yaml`; the test run fails to resolve `./api`.

- [ ] **Step 5: Implement** `ui/src/api.ts`

```ts
// Typed client for the sidecar REST API (spec: REST table). Same origin; Vite proxies /api in dev.
import type { Json } from './lib/diff'

export type Origin = 'source' | 'scratch'
export interface ThreadSummary {
  thread_id: string
  origin: Origin
  checkpoint_count: number
  first_at: string | null
  last_at: string | null
  namespaces: string[]
  fork_of: { thread_id: string; checkpoint_id: string } | null
}
export interface CheckpointRow {
  checkpoint_id: string
  parent_id: string | null
  step: number | null
  source: string | null
  next: string[]
  writes_from: string[]
  created_at: string
  state_bytes: number
  origin: Origin
}
export interface PendingWrite {
  task_id: string
  channel: string
  value: Json
}
export interface CheckpointState {
  checkpoint_id: string
  values: { [channel: string]: Json }
  next: string[]
  pending_writes: PendingWrite[]
  metadata: Json
}
export interface Health {
  ok: boolean
  version: string
  graph: boolean
  source: string
}
export interface Graph {
  nodes: string[]
  edges: { source: string; target: string; conditional: boolean }[]
}
export interface ForkRequest {
  thread_id: string
  checkpoint_id: string
  values: { [channel: string]: Json }
  as_node: string | null
}
export interface ForkResult {
  fork_id: string
  thread_id: string
  base_checkpoint_id: string
  head_checkpoint_id: string
  status: 'done' | 'interrupted' | 'error'
  events: { node: string; update: Json }[]
  error: string | null
  elapsed_ms: number
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // keep statusText
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

const enc = encodeURIComponent

export const api = {
  health: () => call<Health>('/api/health'),
  threads: () => call<ThreadSummary[]>('/api/threads'),
  checkpoints: (threadId: string, ns = '') => call<CheckpointRow[]>(`/api/threads/${enc(threadId)}/checkpoints?ns=${enc(ns)}`),
  state: (threadId: string, checkpointId: string, ns = '') =>
    call<CheckpointState>(`/api/threads/${enc(threadId)}/checkpoints/${enc(checkpointId)}?ns=${enc(ns)}`),
  graph: () => call<Graph>('/api/graph'),
  fork: (req: ForkRequest) =>
    call<ForkResult>('/api/forks', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(req) }),
}
```

Note: `api.ts` imports the `Json` type from `./lib/diff`, which arrives in Task 13. For this task create `ui/src/lib/diff.ts` with only the `Json` type export (`export type Json = null | boolean | number | string | Json[] | { [key: string]: Json }`); Task 13 replaces the file. Calls with no `init` pass `undefined` as the second argument, which the first test asserts.

- [ ] **Step 6: Run**

```powershell
pnpm test
pnpm typecheck
```
Expected: `3 passed`; typecheck exits 0. If `tsc` from TypeScript 7 rejects an option, remove only that option and add a `Ruling:` line.

- [ ] **Step 7: Commit** `chore: scaffold ui with typed api client`

---

### Task 13: Structural diff (ADR 0006, invariants 3 and 4)

**Files:**
- Create: `ui/src/lib/diff.ts` (replace the stub), `ui/src/lib/diff.test.ts`, `ui/src/lib/diff.property.test.ts`

- [ ] **Step 1: Write the failing tests**

`ui/src/lib/diff.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { apply, diff, formatPath, isKeyed, type Json } from './diff'

const msgs = (ids: string[]): Json => ids.map((id) => ({ id, content: id.toUpperCase() }))

describe('diff', () => {
  it('is empty for equal values, whatever the key order', () => {
    expect(diff({ a: 1, b: [1, { c: 2 }] }, { b: [1, { c: 2 }], a: 1 })).toEqual([])
  })

  it('adds, removes and replaces object keys', () => {
    expect(diff({ a: 1, b: 2 }, { b: 3, c: 4 })).toEqual([
      { op: 'remove', path: ['a'], value: 1 },
      { op: 'replace', path: ['b'], before: 2, after: 3 },
      { op: 'add', path: ['c'], value: 4 },
    ])
  })

  it('addresses messages by id, which is how the date bug shows up', () => {
    const before = { messages: [{ id: 'h', content: 'hi' }, { id: 'ai-plan', tool_calls: [{ args: { depart_after: null } }] }] }
    const after = { messages: [{ id: 'h', content: 'hi' }, { id: 'ai-plan', tool_calls: [{ args: { depart_after: '2026-11-01' } }] }] }
    const ops = diff(before, after)
    expect(ops).toEqual([
      { op: 'replace', path: ['messages', { id: 'ai-plan' }, 'tool_calls', 0, 'args', 'depart_after'], before: null, after: '2026-11-01' },
    ])
    expect(formatPath((ops[0] as { path: (string | number | { id: string })[] }).path)).toBe(
      'messages[id=ai-plan].tool_calls[0].args.depart_after',
    )
  })

  it('reports a reordered keyed list as moves only', () => {
    const ops = diff(msgs(['a', 'b', 'c', 'd']), msgs(['c', 'a', 'd', 'b']))
    expect(ops.length).toBeGreaterThan(0)
    expect(ops.every((o) => o.op === 'move')).toBe(true)
    expect(apply(msgs(['a', 'b', 'c', 'd']), ops)).toEqual(msgs(['c', 'a', 'd', 'b']))
  })

  it('inserts into a keyed list at the final index', () => {
    const ops = diff(msgs(['a', 'c']), msgs(['a', 'b', 'c']))
    expect(ops).toEqual([{ op: 'add', path: [1], value: { id: 'b', content: 'B' } }])
  })

  it('diffs plain arrays by index', () => {
    expect(diff([1, 2, 3], [1, 9])).toEqual([
      { op: 'replace', path: [1], before: 2, after: 9 },
      { op: 'remove', path: [2], value: 3 },
    ])
    expect(apply([1, 2, 3], diff([1, 2, 3], [1, 9, 3, 4]))).toEqual([1, 9, 3, 4])
  })

  it('replaces at the root when types differ', () => {
    expect(diff([1], { a: 1 })).toEqual([{ op: 'replace', path: [], before: [1], after: { a: 1 } }])
  })

  it('treats duplicate or missing ids as an indexed list', () => {
    expect(isKeyed([{ id: 'a' }, { id: 'a' }])).toBe(false)
    expect(isKeyed([{ id: 'a' }, { x: 1 }])).toBe(false)
    expect(isKeyed([])).toBe(false)
    expect(isKeyed([{ id: 'a' }, { id: 'b' }])).toBe(true)
  })

  it('formats the root path', () => {
    expect(formatPath([])).toBe('(root)')
  })

  it('does not mutate its inputs', () => {
    const a: Json = { m: msgs(['a', 'b']) }
    const copy = structuredClone(a)
    apply(a, diff(a, { m: msgs(['b', 'a']) }))
    expect(a).toEqual(copy)
  })
})
```

`ui/src/lib/diff.property.test.ts`:
```ts
import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import { apply, deepEqual, diff, type Json } from './diff'

const msg = fc.record({
  id: fc.constantFrom('a', 'b', 'c', 'd', 'e', 'f'),
  content: fc.string({ maxLength: 4 }),
  n: fc.integer({ min: 0, max: 3 }),
})
const msgs = fc.uniqueArray(msg, { selector: (m) => m.id, maxLength: 6 })
const tree = fc.letrec((tie) => ({
  node: fc.oneof(
    { depthSize: 'small' },
    fc.jsonValue({ maxDepth: 2 }),
    msgs,
    fc.dictionary(fc.string({ maxLength: 3 }), tie('node'), { maxKeys: 4 }),
    fc.array(tie('node'), { maxLength: 4 }),
  ),
})).node

describe('diff properties', () => {
  it('diff(a, a) is empty and apply(a, diff(a, b)) equals b', () => {
    fc.assert(
      fc.property(tree, tree, (a, b) => {
        expect(diff(a as Json, a as Json)).toEqual([])
        expect(deepEqual(apply(a as Json, diff(a as Json, b as Json)), b as Json)).toBe(true)
      }),
      { numRuns: 500 },
    )
  })

  it('a permutation of a keyed list is moves only', () => {
    fc.assert(
      fc.property(msgs, fc.integer(), (m, seed) => {
        const shuffled = [...m].sort((x, y) => ((x.id.charCodeAt(0) * 31 + seed) % 7) - ((y.id.charCodeAt(0) * 31 + seed) % 7))
        const ops = diff(m as Json, shuffled as Json)
        expect(ops.every((o) => o.op === 'move')).toBe(true)
        expect(deepEqual(apply(m as Json, ops), shuffled as Json)).toBe(true)
      }),
      { numRuns: 500 },
    )
  })
})
```

- [ ] **Step 2: Run** `pnpm test` -> failures (`diff` is not exported from the stub).

- [ ] **Step 3: Implement** `ui/src/lib/diff.ts` (verified with fast-check before this plan was written)

```ts
// Structural diff over bridged JSON (ADR 0006). Pure: no DOM, no React.

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json }
export type PathSeg = string | number | { id: string }
export type Path = PathSeg[]
export type DiffOp =
  | { op: 'add'; path: Path; value: Json }
  | { op: 'remove'; path: Path; value: Json }
  | { op: 'replace'; path: Path; before: Json; after: Json }
  | { op: 'move'; from: Path; to: Path }

const isObj = (v: Json): v is { [key: string]: Json } => typeof v === 'object' && v !== null && !Array.isArray(v)

function keyOf(v: Json): string | null {
  return isObj(v) && typeof v.id === 'string' ? v.id : null
}

/** An array is keyed when every element is an object with a unique string `id`. Empty arrays are not keyed. */
export function isKeyed(arr: Json[]): boolean {
  if (arr.length === 0) return false
  const seen = new Set<string>()
  for (const v of arr) {
    const k = keyOf(v)
    if (k === null || seen.has(k)) return false
    seen.add(k)
  }
  return true
}

export function deepEqual(a: Json, b: Json): boolean {
  if (a === b) return true
  if (Array.isArray(a)) {
    if (!Array.isArray(b) || a.length !== b.length) return false
    return a.every((v, i) => deepEqual(v, b[i]))
  }
  if (isObj(a)) {
    if (!isObj(b)) return false
    const ka = Object.keys(a)
    if (ka.length !== Object.keys(b).length) return false
    return ka.every((k) => Object.prototype.hasOwnProperty.call(b, k) && deepEqual(a[k], b[k]))
  }
  return false
}

export function diff(a: Json, b: Json, path: Path = []): DiffOp[] {
  if (deepEqual(a, b)) return []
  if (isObj(a) && isObj(b)) {
    const ops: DiffOp[] = []
    for (const k of Object.keys(a)) {
      if (!Object.prototype.hasOwnProperty.call(b, k)) ops.push({ op: 'remove', path: [...path, k], value: a[k] })
      else ops.push(...diff(a[k], b[k], [...path, k]))
    }
    for (const k of Object.keys(b)) {
      if (!Object.prototype.hasOwnProperty.call(a, k)) ops.push({ op: 'add', path: [...path, k], value: b[k] })
    }
    return ops
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    return isKeyed(a) && isKeyed(b) ? diffKeyed(a, b, path) : diffIndexed(a, b, path)
  }
  return [{ op: 'replace', path, before: a, after: b }]
}

function diffIndexed(a: Json[], b: Json[], path: Path): DiffOp[] {
  const ops: DiffOp[] = []
  const common = Math.min(a.length, b.length)
  for (let i = 0; i < common; i++) ops.push(...diff(a[i], b[i], [...path, i]))
  for (let i = a.length - 1; i >= b.length; i--) ops.push({ op: 'remove', path: [...path, i], value: a[i] })
  for (let i = a.length; i < b.length; i++) ops.push({ op: 'add', path: [...path, i], value: b[i] })
  return ops
}

function diffKeyed(a: Json[], b: Json[], path: Path): DiffOp[] {
  const ops: DiffOp[] = []
  const bIds = new Set(b.map((v) => keyOf(v) as string))
  const aById = new Map(a.map((v) => [keyOf(v) as string, v]))
  // 1. nested changes and removals, addressed by id
  for (const v of a) {
    const id = keyOf(v) as string
    if (!bIds.has(id)) ops.push({ op: 'remove', path: [...path, { id }], value: v })
  }
  for (const v of b) {
    const id = keyOf(v) as string
    const before = aById.get(id)
    if (before !== undefined) ops.push(...diff(before, v, [...path, { id }]))
  }
  // 2. additions at their final index, left to right
  const cur: string[] = a.map((v) => keyOf(v) as string).filter((id) => bIds.has(id))
  b.forEach((v, i) => {
    const id = keyOf(v) as string
    if (!aById.has(id)) {
      ops.push({ op: 'add', path: [...path, i], value: v })
      cur.splice(i, 0, id)
    }
  })
  // 3. moves that fix the order left to right
  b.forEach((v, i) => {
    const id = keyOf(v) as string
    if (cur[i] !== id) {
      const from = cur.indexOf(id)
      cur.splice(from, 1)
      cur.splice(i, 0, id)
      ops.push({ op: 'move', from: [...path, { id }], to: [...path, i] })
    }
  })
  return ops
}

function clone<T extends Json>(v: T): T {
  return structuredClone(v)
}

// defineProperty, not assignment, so a key named __proto__ stays an own data property
function setOwn(obj: Record<string, Json>, key: string, value: Json): void {
  Object.defineProperty(obj, key, { value, writable: true, enumerable: true, configurable: true })
}

function locate(container: Json, seg: PathSeg): string | number {
  if (typeof seg === 'object') {
    if (!Array.isArray(container)) throw new Error('id segment on a non-array')
    const idx = container.findIndex((v) => keyOf(v) === seg.id)
    if (idx < 0) throw new Error(`no element with id ${seg.id}`)
    return idx
  }
  return seg
}

function parentOf(root: Json, path: Path): [Json, string | number] {
  let node = root
  for (const seg of path.slice(0, -1)) {
    const k = locate(node, seg)
    node = (node as Record<string | number, Json>)[k]
  }
  return [node, locate(node, path[path.length - 1])]
}

/** Replay ops on a copy of `a`. Throws on ops that do not fit. */
export function apply(a: Json, ops: DiffOp[]): Json {
  let root = clone(a)
  for (const o of ops) {
    if (o.op === 'move') {
      const [arr, from] = parentOf(root, o.from)
      const [, to] = parentOf(root, o.to)
      const list = arr as Json[]
      const [item] = list.splice(from as number, 1)
      list.splice(to as number, 0, item)
      continue
    }
    if (o.path.length === 0) {
      if (o.op === 'replace') root = clone(o.after)
      else throw new Error(`${o.op} at the root`)
      continue
    }
    const [parent, key] = parentOf(root, o.path)
    if (Array.isArray(parent)) {
      const i = key as number
      if (o.op === 'add') parent.splice(i, 0, clone(o.value))
      else if (o.op === 'remove') parent.splice(i, 1)
      else parent[i] = clone(o.after)
    } else {
      const obj = parent as Record<string, Json>
      if (o.op === 'remove') delete obj[key as string]
      else setOwn(obj, key as string, clone(o.op === 'add' ? o.value : o.after))
    }
  }
  return root
}

/** Human-readable path, e.g. messages[id=ai-plan].tool_calls[0].args.depart_after */
export function formatPath(path: Path): string {
  let out = ''
  for (const seg of path) {
    if (typeof seg === 'number') out += `[${seg}]`
    else if (typeof seg === 'object') out += `[id=${seg.id}]`
    else out += out === '' ? seg : `.${seg}`
  }
  return out === '' ? '(root)' : out
}
```

- [ ] **Step 4: Run** `pnpm test` -> all diff tests pass (`15 passed` across api, diff and property files; record the real line). `pnpm typecheck` exits 0.

- [ ] **Step 5: Commit** `feat(ui): structural diff keyed by message id with property tests`

---

### Task 14: Pure helpers: lanes, changed keys, formatting, tags

**Files:**
- Create: `ui/src/lib/lanes.ts`, `ui/src/lib/changed.ts`, `ui/src/lib/format.ts`, `ui/src/lib/tags.ts` and a test file for each: `lanes.test.ts`, `changed.test.ts`, `format.test.ts`, `tags.test.ts`

- [ ] **Step 1: Write the failing tests**

`ui/src/lib/lanes.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { computeLanes, laneCount } from './lanes'

const row = (checkpoint_id: string, parent_id: string | null) => ({ checkpoint_id, parent_id })

describe('computeLanes', () => {
  it('puts a linear thread on lane 0', () => {
    const lanes = computeLanes([row('a', null), row('b', 'a'), row('c', 'b')])
    expect([...lanes.values()].every((l) => l.lane === 0 && l.branchFrom === null)).toBe(true)
    expect(laneCount(lanes)).toBe(1)
  })

  it('gives the newest leaf lane 0 and an older branch lane 1', () => {
    // a-b-c-d is the first run; c-e-f is an update_state branch made later (ids sort by time)
    const lanes = computeLanes([row('a', null), row('b', 'a'), row('c', 'b'), row('d', 'c'), row('e', 'c'), row('f', 'e')])
    expect(lanes.get('f')).toEqual({ lane: 0, branchFrom: null })
    expect(lanes.get('e')).toEqual({ lane: 0, branchFrom: null })
    expect(lanes.get('d')).toEqual({ lane: 1, branchFrom: 'c' })
    expect(laneCount(lanes)).toBe(2)
  })

  it('treats a missing parent as a root', () => {
    expect(computeLanes([row('x', 'gone')]).get('x')).toEqual({ lane: 0, branchFrom: null })
  })
})
```

`ui/src/lib/changed.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { changedTopLevel } from './changed'

describe('changedTopLevel', () => {
  it('keeps only top-level channels that changed or are new', () => {
    const before = { messages: [{ id: 'a', content: 'x' }], count: 1, results: [] }
    const after = { messages: [{ id: 'a', content: 'y' }], count: 1, results: [], extra: true }
    expect(changedTopLevel(before, after)).toEqual({ messages: [{ id: 'a', content: 'y' }], extra: true })
  })

  it('ignores key order and removed keys', () => {
    expect(changedTopLevel({ a: { x: 1, y: 2 }, gone: 1 }, { a: { y: 2, x: 1 } })).toEqual({})
  })
})
```
(Removed keys are ignored on purpose: LangGraph cannot delete a channel through `update_state`. Sending a full reducer list such as `operator.add` again would duplicate it, which is why only changed channels are sent.)

`ui/src/lib/format.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { formatBytes, relativeTime, shortId } from './format'

describe('format', () => {
  it('formats bytes', () => {
    expect(formatBytes(812)).toBe('812 B')
    expect(formatBytes(18_634)).toBe('18.2 KB')
    expect(formatBytes(1_468_006)).toBe('1.4 MB')
  })
  it('formats time since the first checkpoint', () => {
    expect(relativeTime('2026-10-04T10:00:00.000Z', '2026-10-04T10:00:00.000Z')).toBe('+0 ms')
    expect(relativeTime('2026-10-04T10:00:00.250Z', '2026-10-04T10:00:00.000Z')).toBe('+250 ms')
    expect(relativeTime('2026-10-04T10:00:03.400Z', '2026-10-04T10:00:00.000Z')).toBe('+3.4 s')
    expect(relativeTime('2026-10-04T10:02:05.000Z', '2026-10-04T10:00:00.000Z')).toBe('+2m 5s')
  })
  it('shortens checkpoint ids to their last 8 characters', () => {
    expect(shortId('1f1bf756-229e-6563-8003-d41065ca3b5a')).toBe('65ca3b5a')
  })
})
```

`ui/src/lib/tags.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { isMessage, orderChannels, tagOf, typeName } from './tags'

describe('tags', () => {
  it('finds the tag of a bridged value', () => {
    expect(tagOf({ __lc_message__: 'ai', id: 'x', content: '' })).toBe('__lc_message__')
    expect(tagOf({ __uuid__: 'u' })).toBe('__uuid__')
    expect(tagOf({ plain: 1 })).toBeNull()
    expect(tagOf([1])).toBeNull()
    expect(tagOf('s')).toBeNull()
  })
  it('detects messages', () => {
    expect(isMessage({ __lc_message__: 'human', id: 'h', content: 'hi' })).toBe(true)
    expect(isMessage({ id: 'h' })).toBe(false)
  })
  it('shortens dotted type names', () => {
    expect(typeName('flight_recorder.samples.SearchQuery')).toBe('SearchQuery')
  })
  it('orders channels messages first and splits off internal ones', () => {
    expect(orderChannels({ results: [], 'branch:to:tools': null, query: 1, messages: [], __start__: null })).toEqual({
      user: ['messages', 'query', 'results'],
      internal: ['__start__', 'branch:to:tools'],
    })
  })
})
```

- [ ] **Step 2: Run** `pnpm test` -> the four new files fail to import.

- [ ] **Step 3: Implement**

`ui/src/lib/lanes.ts` (verified):

```ts
// Branch lanes for the timeline. Pure. Lane 0 is the chain ending at the newest checkpoint.

export interface LaneInput {
  checkpoint_id: string
  parent_id: string | null
}
export interface Lane {
  lane: number
  /** parent checkpoint id when this row starts a branch off another lane, else null */
  branchFrom: string | null
}

export function computeLanes(rows: LaneInput[]): Map<string, Lane> {
  const byId = new Map(rows.map((r) => [r.checkpoint_id, r]))
  const hasChild = new Set<string>()
  for (const r of rows) if (r.parent_id && byId.has(r.parent_id)) hasChild.add(r.parent_id)
  // checkpoint ids are uuid6, so string order is time order; newest leaf first
  const leaves = rows
    .filter((r) => !hasChild.has(r.checkpoint_id))
    .map((r) => r.checkpoint_id)
    .sort()
    .reverse()
  const out = new Map<string, Lane>()
  let next = 0
  for (const leaf of leaves) {
    const lane = next++
    let id: string | null = leaf
    let top: string | null = null
    while (id !== null && byId.has(id) && !out.has(id)) {
      out.set(id, { lane, branchFrom: null })
      top = id
      const parent: string | null = byId.get(id)!.parent_id
      id = parent
    }
    if (top !== null && id !== null && out.has(id)) out.set(top, { lane, branchFrom: id })
  }
  return out
}

export function laneCount(lanes: Map<string, Lane>): number {
  let max = -1
  for (const l of lanes.values()) max = Math.max(max, l.lane)
  return max + 1
}
```

`ui/src/lib/changed.ts`:
```ts
import { deepEqual, type Json } from './diff'

type Values = { [channel: string]: Json }

/** Top-level channels of `after` that differ from `before` (new keys included, removed keys ignored). */
export function changedTopLevel(before: Values, after: Values): Values {
  const out: Values = {}
  for (const [k, v] of Object.entries(after)) {
    if (!Object.prototype.hasOwnProperty.call(before, k) || !deepEqual(before[k], v)) out[k] = v
  }
  return out
}
```

`ui/src/lib/format.ts`:
```ts
export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export function relativeTime(at: string, first: string): string {
  const ms = Math.max(0, Date.parse(at) - Date.parse(first))
  if (ms < 1000) return `+${Math.round(ms)} ms`
  if (ms < 60_000) return `+${(ms / 1000).toFixed(1)} s`
  const s = Math.round(ms / 1000)
  return `+${Math.floor(s / 60)}m ${s % 60}s`
}

export function shortId(id: string): string {
  return id.slice(-8)
}
```

`ui/src/lib/tags.ts`:
```ts
import type { Json } from './diff'

export const TAGS = [
  '__lc_message__', '__pydantic__', '__object__', '__set__', '__bytes__', '__datetime__', '__date__',
  '__time__', '__uuid__', '__decimal__', '__float__', '__map__', '__unrepresentable__',
] as const
export type Tag = (typeof TAGS)[number]

export type Obj = { [key: string]: Json }
export const isObj = (v: Json): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v)

export function tagOf(v: Json): Tag | null {
  if (!isObj(v)) return null
  return TAGS.find((t) => Object.prototype.hasOwnProperty.call(v, t)) ?? null
}

export function isMessage(v: Json): v is Obj {
  return tagOf(v) === '__lc_message__'
}

export function typeName(dotted: string): string {
  return dotted.slice(dotted.lastIndexOf('.') + 1)
}

/** LangGraph bookkeeping channels: `branch:to:<node>` triggers and `__start__`-style names. */
export const isInternal = (channel: string) => channel.startsWith('branch:to:') || channel.startsWith('__')

/** User channels with `messages` first then sorted, and internal channels sorted. */
export function orderChannels(values: Obj): { user: string[]; internal: string[] } {
  const keys = Object.keys(values)
  const user = keys
    .filter((k) => !isInternal(k))
    .sort((a, b) => (a === 'messages' ? -1 : b === 'messages' ? 1 : a.localeCompare(b)))
  return { user, internal: keys.filter(isInternal).sort() }
}
```
(The tag list must equal `bridge.TAGS` in Python; keep both in the same order.)

- [ ] **Step 4: Run** `pnpm test` and `pnpm typecheck` -> all pass.

- [ ] **Step 5: Commit** `feat(ui): lanes, changed-channel, format and tag helpers`

---

### Before Task 15: design direction (do this once)

Invoke the `design-taste-frontend` skill (the user's rule: load a taste skill before any UI work). Apply it to a dense developer tool, not a landing page. The direction below is decided; the skill is for execution quality. Record `Ruling: design direction ...` in the ledger.

- Name: "flight data recorder". Dark first (`#0b0d10` background, `#12151a` panels, `#1b2027` lines), light theme through `prefers-color-scheme: light` with the same tokens.
- One accent only: international orange `#ff5f1f`. It means "selected" and "scratch/fork". Source rows are neutral.
- Data in a monospace stack (`ui-monospace, "Cascadia Code", "JetBrains Mono", Consolas, monospace`), chrome in `system-ui`. 13px base for data, 12px for chips.
- Chips: small rounded rectangles for node names (`plan`, `tools`), source (`input`, `loop`, `update`) and tags (`datetime`, `SearchQuery`).
- All colors and sizes as CSS custom properties in `:root` in `ui/src/styles.css`. No external fonts, no CDN, no component library, no icons package.

### Task 15: Thread list and virtualized timeline

**Files:**
- Create: `ui/src/components/ThreadList.tsx`, `ui/src/components/Timeline.tsx`, `ui/src/components/Timeline.test.tsx`, `ui/src/components/ThreadList.test.tsx`
- Modify: `ui/src/styles.css`

**Contracts:**
- `ThreadList({ threads, selected, onSelect })`: `threads: ThreadSummary[]`, `selected: string | null`, `onSelect(threadId: string)`. Renders `role="listbox"` with `aria-label="Threads"`; each item `role="option"`, `aria-selected`, text includes `thread_id` and `checkpoint_count`; a scratch thread shows `fork of <fork_of.thread_id>`.
- `Timeline({ rows, selectedId, compareId, onSelect })`: `rows: CheckpointRow[]` (oldest first), `onSelect(checkpointId: string, opts: { shift: boolean })`. Uses `useVirtualizer` from `@tanstack/react-virtual` with `estimateSize: () => 36`, `overscan: 12`. Scroll container has `data-testid="timeline"`, `data-count={rows.length}`, `role="listbox"`, `aria-label="Checkpoints"`, fixed height from CSS (fills its pane). Each rendered row: `data-testid="timeline-row"`, `data-checkpoint-id`, `data-lane`, `data-origin`, `role="option"`, `aria-selected`, plus `data-compare="true"` on the compare row. Row content: lane gutter (lane dots, a short horizontal mark when `branchFrom` is set), step number, `source` chip, `writes_from` chips, an arrow, `next` chips, relative time from the first row (`relativeTime`), `formatBytes(state_bytes)`. When `selectedId` changes, call `virtualizer.scrollToIndex(index, { align: 'auto' })`.

- [ ] **Step 1: Write the failing tests**

`ui/src/components/Timeline.test.tsx`:
```tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CheckpointRow } from '../api'
import { Timeline } from './Timeline'

function rows(n: number): CheckpointRow[] {
  return Array.from({ length: n }, (_, i) => ({
    checkpoint_id: `cp-${String(i).padStart(6, '0')}`,
    parent_id: i === 0 ? null : `cp-${String(i - 1).padStart(6, '0')}`,
    step: i - 1,
    source: i === 0 ? 'input' : 'loop',
    next: ['tick'],
    writes_from: i === 0 ? [] : ['tick'],
    created_at: new Date(Date.UTC(2026, 9, 4, 10, 0, 0, i)).toISOString(),
    state_bytes: 1500,
    origin: 'source',
  }))
}

describe('Timeline', () => {
  it('virtualizes: 10,000 rows render only a window', () => {
    render(<Timeline rows={rows(10_000)} selectedId={null} compareId={null} onSelect={() => {}} />)
    expect(screen.getByTestId('timeline')).toHaveAttribute('data-count', '10000')
    const rendered = screen.getAllByTestId('timeline-row').length
    expect(rendered).toBeGreaterThan(0)
    expect(rendered).toBeLessThan(100)
  })

  it('selects on click and passes shift for compare', () => {
    const onSelect = vi.fn()
    render(<Timeline rows={rows(5)} selectedId="cp-000001" compareId={null} onSelect={onSelect} />)
    const [first] = screen.getAllByTestId('timeline-row')
    fireEvent.click(first)
    fireEvent.click(first, { shiftKey: true })
    expect(onSelect).toHaveBeenNthCalledWith(1, 'cp-000000', { shift: false })
    expect(onSelect).toHaveBeenNthCalledWith(2, 'cp-000000', { shift: true })
    const selected = screen.getAllByTestId('timeline-row').find((r) => r.getAttribute('aria-selected') === 'true')
    expect(selected).toHaveAttribute('data-checkpoint-id', 'cp-000001')
  })

  it('puts an older branch on lane 1', () => {
    const base = rows(4)
    const branch: CheckpointRow = { ...base[3], checkpoint_id: 'cp-000009', parent_id: 'cp-000002', source: 'update' }
    render(<Timeline rows={[...base, branch]} selectedId={null} compareId={null} onSelect={() => {}} />)
    const byId = (id: string) => screen.getAllByTestId('timeline-row').find((r) => r.dataset.checkpointId === id)!
    expect(byId('cp-000009')).toHaveAttribute('data-lane', '0')
    expect(byId('cp-000003')).toHaveAttribute('data-lane', '1')
  })

  it('shows node chips', () => {
    render(<Timeline rows={rows(3)} selectedId={null} compareId={null} onSelect={() => {}} />)
    expect(screen.getAllByText('tick').length).toBeGreaterThan(0)
  })
})
```
If jsdom reports zero height and TanStack renders no rows at all, add to `src/test/setup.ts` a stub of `HTMLElement.prototype.getBoundingClientRect` returning `{ width: 800, height: 600, top: 0, left: 0, right: 800, bottom: 600, x: 0, y: 0, toJSON() {} }` and record a `Ruling:`.

`ui/src/components/ThreadList.test.tsx`:
```tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ThreadSummary } from '../api'
import { ThreadList } from './ThreadList'

const t = (thread_id: string, extra: Partial<ThreadSummary> = {}): ThreadSummary => ({
  thread_id, origin: 'source', checkpoint_count: 5, first_at: null, last_at: null, namespaces: [''], fork_of: null, ...extra,
})

describe('ThreadList', () => {
  it('lists threads, marks the selected one and reports clicks', () => {
    const onSelect = vi.fn()
    render(
      <ThreadList
        threads={[t('lisbon-bug'), t('fork:abc', { origin: 'scratch', fork_of: { thread_id: 'lisbon-bug', checkpoint_id: 'c' } })]}
        selected="lisbon-bug"
        onSelect={onSelect}
      />,
    )
    const options = screen.getAllByRole('option')
    expect(options[0]).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText(/fork of lisbon-bug/)).toBeInTheDocument()
    fireEvent.click(options[1])
    expect(onSelect).toHaveBeenCalledWith('fork:abc')
  })
})
```

- [ ] **Step 2: Run** `pnpm test` -> new tests fail (no components).
- [ ] **Step 3: Implement** both components to the contracts, with styles in `styles.css`.
- [ ] **Step 4: Run** `pnpm test` and `pnpm typecheck` -> pass.
- [ ] **Step 5: Commit** `feat(ui): thread list and virtualized timeline with branch lanes`

---

### Task 16: State inspector

**Files:**
- Create: `ui/src/components/StateInspector.tsx`, `ui/src/components/JsonTree.tsx`, `ui/src/components/MessageCard.tsx`, `ui/src/components/StateInspector.test.tsx`

**Contracts:**
- `StateInspector({ state, loading, error })`: root `data-testid="inspector"` with `data-checkpoint-id={state?.checkpoint_id ?? ''}`. Loading shows `Loading state...`; error shows it in `role="alert"`. One section per top-level channel (`messages` first, the rest sorted), each with a heading of the channel name. LangGraph's internal channels (names starting with `branch:to:` or `__`) go last, inside one collapsed `<details>` titled `Internal channels`. Put the ordering in a helper `orderChannels(values)` in `ui/src/lib/tags.ts` and reuse it in the fork editor. A "Next" line lists `state.next` chips (or `end of run` when empty). A "Pending writes" section lists `channel` + value when any.
- `MessageCard({ message })`: shows the role (`human`, `ai`, `tool`, `system` or the raw `__lc_message__` value), the content (string, or a `JsonTree` for list content), each tool call as `name` plus a `JsonTree` of `args`, and `tool_call_id` for tool messages. `data-testid="message"`, `data-role`.
- `JsonTree({ value, depth })`: objects and arrays as `<details>` (open when `depth < 2`); `__pydantic__` and `__object__` render the short type name (`typeName`) then their `fields` or `args`; `__datetime__`, `__date__`, `__time__`, `__uuid__`, `__decimal__`, `__float__` render as a chip `<tag name> <value>`; `__set__` as `set` + items; `__bytes__` as `bytes` + base64 length; `__map__` as key/value pairs; `__unrepresentable__` as a warning chip `unrepresentable <type>` with the repr in a `title`; messages inside any tree use `MessageCard`. Strings longer than 400 characters show the first 400 and a `Show all` button.

- [ ] **Step 1: Write the failing test** `ui/src/components/StateInspector.test.tsx`

```tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { CheckpointState } from '../api'
import { StateInspector } from './StateInspector'

const state: CheckpointState = {
  checkpoint_id: 'cp-1',
  next: ['tools'],
  metadata: { source: 'loop', step: 1 },
  pending_writes: [{ task_id: 't1', channel: 'messages', value: 'w' }],
  values: {
    results: [],
    query: { __pydantic__: 'flight_recorder.samples.SearchQuery', fields: { destination: 'Lisbon', depart_after: null } },
    messages: [
      { __lc_message__: 'human', id: 'human-1', content: 'Find me the cheapest flight to Lisbon departing after 2026-11-01.' },
      {
        __lc_message__: 'ai', id: 'ai-plan', content: '',
        tool_calls: [{ name: 'search_flights', args: { destination: 'Lisbon', depart_after: null }, id: 'call-1', type: 'tool_call' }],
      },
    ],
    when: { __datetime__: '2026-10-04T09:30:00+00:00' },
    blob: { __unrepresentable__: 'numpy', repr: 'array([1, 2])' },
    long: 'x'.repeat(1000),
  },
}

describe('StateInspector', () => {
  it('renders messages with roles and tool calls', () => {
    render(<StateInspector state={state} loading={false} />)
    expect(screen.getByTestId('inspector')).toHaveAttribute('data-checkpoint-id', 'cp-1')
    const roles = screen.getAllByTestId('message').map((m) => m.getAttribute('data-role'))
    expect(roles).toEqual(['human', 'ai'])
    expect(screen.getByText('search_flights')).toBeInTheDocument()
    expect(screen.getAllByText(/depart_after/).length).toBeGreaterThan(0)
  })

  it('renders tagged values', () => {
    render(<StateInspector state={state} loading={false} />)
    expect(screen.getByText('SearchQuery')).toBeInTheDocument()
    expect(screen.getByText(/2026-10-04T09:30:00/)).toBeInTheDocument()
    expect(screen.getByText(/unrepresentable numpy/)).toHaveAttribute('title', 'array([1, 2])')
    expect(screen.getByText(/tools/)).toBeInTheDocument()
  })

  it('truncates long strings until asked', () => {
    render(<StateInspector state={state} loading={false} />)
    fireEvent.click(screen.getByRole('button', { name: 'Show all' }))
    expect(screen.getByText('x'.repeat(1000))).toBeInTheDocument()
  })

  it('shows loading and errors', () => {
    const { rerender } = render(<StateInspector state={null} loading />)
    expect(screen.getByText('Loading state...')).toBeInTheDocument()
    rerender(<StateInspector state={null} loading={false} error="boom" />)
    expect(screen.getByRole('alert')).toHaveTextContent('boom')
  })
})
```

- [ ] **Step 2: Run** -> fails. **Step 3: Implement.** **Step 4: Run** `pnpm test`, `pnpm typecheck` -> pass.
- [ ] **Step 5: Commit** `feat(ui): message-aware state inspector`

---

### Task 17: Diff panel

**Files:**
- Create: `ui/src/components/DiffPanel.tsx`, `ui/src/components/DiffPanel.test.tsx`

**Contract:** `DiffPanel({ before, after, beforeLabel, afterLabel })` with `before`/`after: CheckpointState | null`. Root `data-testid="diff-panel"`. Header `<beforeLabel> -> <afterLabel>` and the count (`1 change`, `3 changes`). Ops from `diff(before.values, after.values)` (memoized), each `data-testid="diff-op"` with `data-op`, the op name, `formatPath(path)` (for `move`: `formatPath(from)` then `to index N`), and for `replace` the before and after as `JSON.stringify` truncated to 200 characters; `add`/`remove` show the value. No ops: `No changes`. Either side null: `Loading...`.

- [ ] **Step 1: Write the failing test** `ui/src/components/DiffPanel.test.tsx`

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { CheckpointState } from '../api'
import { DiffPanel } from './DiffPanel'

const st = (values: CheckpointState['values']): CheckpointState => ({ checkpoint_id: 'x', values, next: [], pending_writes: [], metadata: null })

describe('DiffPanel', () => {
  it('shows the dropped date filter as one replace', () => {
    const before = st({ messages: [{ __lc_message__: 'ai', id: 'ai-plan', tool_calls: [{ args: { depart_after: null } }] }] })
    const after = st({ messages: [{ __lc_message__: 'ai', id: 'ai-plan', tool_calls: [{ args: { depart_after: '2026-11-01' } }] }] })
    render(<DiffPanel before={before} after={after} beforeLabel="step 1" afterLabel="fork step 2" />)
    const ops = screen.getAllByTestId('diff-op')
    expect(ops).toHaveLength(1)
    expect(ops[0]).toHaveAttribute('data-op', 'replace')
    expect(ops[0]).toHaveTextContent('messages[id=ai-plan].tool_calls[0].args.depart_after')
    expect(ops[0]).toHaveTextContent('"2026-11-01"')
    expect(screen.getByText('1 change')).toBeInTheDocument()
  })

  it('says when nothing changed or a side is loading', () => {
    const { rerender } = render(<DiffPanel before={st({ a: 1 })} after={st({ a: 1 })} beforeLabel="a" afterLabel="b" />)
    expect(screen.getByText('No changes')).toBeInTheDocument()
    rerender(<DiffPanel before={null} after={st({ a: 1 })} beforeLabel="a" afterLabel="b" />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders moves', () => {
    const m = (ids: string[]) => st({ messages: ids.map((id) => ({ id })) })
    render(<DiffPanel before={m(['a', 'b'])} after={m(['b', 'a'])} beforeLabel="a" afterLabel="b" />)
    expect(screen.getAllByTestId('diff-op').every((o) => o.getAttribute('data-op') === 'move')).toBe(true)
  })
})
```

- [ ] **Step 2-4:** fail, implement, pass (`pnpm test`, `pnpm typecheck`).
- [ ] **Step 5: Commit** `feat(ui): diff panel`

---

### Task 18: Fork editor

**Files:**
- Create: `ui/src/components/ForkEditor.tsx`, `ui/src/components/ForkEditor.test.tsx`

**Contract:** `ForkEditor({ threadId, row, state, nodes, onFork, onOpenThread })`. `nodes` excludes `__start__` and `__end__` (filter inside). A `<textarea aria-label="Fork values">` starts as `JSON.stringify` (2-space indent) of the user channels only, in `orderChannels` order (`messages` first, then sorted; internal `branch:to:*` and `__*` channels left out). The order matters: the e2e test edits the first `"depart_after": null`, which must be the one inside the AI tool call, not `query`. A `<select aria-label="As node">` lists `nodes`, default `row.writes_from[0]` when it is in `nodes`, else the first node. Button `Run fork`. On submit: parse JSON (failure: `role="alert"` with `Invalid JSON: <message>`, no call); the body is `{ thread_id: threadId, checkpoint_id: row.checkpoint_id, values: changedTopLevel(state.values, parsed), as_node }`. While running the button is disabled and reads `Running...`. Result block `data-testid="fork-result"` shows `status`, `elapsed_ms` as `<n> ms`, the event node names in order, and `error` when set; a button `Open fork` calls `onOpenThread(result.thread_id, result.head_checkpoint_id)`. An `ApiError` from `onFork` shows its message in `role="alert"`. Help text under the textarea: `Only changed top-level channels are sent. The original thread is never modified.`

- [ ] **Step 1: Write the failing test** `ui/src/components/ForkEditor.test.tsx`

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CheckpointRow, CheckpointState, ForkResult } from '../api'
import { ForkEditor } from './ForkEditor'

const row: CheckpointRow = {
  checkpoint_id: 'cp-plan', parent_id: 'cp-0', step: 1, source: 'loop', next: ['tools'], writes_from: ['plan'],
  created_at: '2026-10-04T10:00:00Z', state_bytes: 900, origin: 'source',
}
const state: CheckpointState = {
  checkpoint_id: 'cp-plan', next: ['tools'], pending_writes: [], metadata: null,
  values: { messages: [{ __lc_message__: 'ai', id: 'ai-plan', tool_calls: [{ args: { depart_after: null } }] }], results: [] },
}
const result: ForkResult = {
  fork_id: 'f1', thread_id: 'fork:f1', base_checkpoint_id: 'cp-plan', head_checkpoint_id: 'cp-head', status: 'done',
  events: [{ node: 'tools', update: {} }, { node: 'answer', update: {} }], error: null, elapsed_ms: 87.5,
}
const nodes = ['__start__', 'plan', 'tools', 'answer', '__end__']

describe('ForkEditor', () => {
  it('sends only the changed channels with the default as_node', async () => {
    const onFork = vi.fn(async () => result)
    const onOpen = vi.fn()
    render(<ForkEditor threadId="lisbon-bug" row={row} state={state} nodes={nodes} onFork={onFork} onOpenThread={onOpen} />)
    expect(screen.getByLabelText('As node')).toHaveValue('plan')
    const box = screen.getByLabelText('Fork values') as HTMLTextAreaElement
    fireEvent.change(box, { target: { value: box.value.replace('"depart_after": null', '"depart_after": "2026-11-01"') } })
    fireEvent.click(screen.getByRole('button', { name: 'Run fork' }))
    await waitFor(() => expect(screen.getByTestId('fork-result')).toHaveTextContent('done'))
    expect(onFork).toHaveBeenCalledWith({
      thread_id: 'lisbon-bug',
      checkpoint_id: 'cp-plan',
      as_node: 'plan',
      values: { messages: [{ __lc_message__: 'ai', id: 'ai-plan', tool_calls: [{ args: { depart_after: '2026-11-01' } }] }] },
    })
    expect(screen.getByTestId('fork-result')).toHaveTextContent('87.5 ms')
    fireEvent.click(screen.getByRole('button', { name: 'Open fork' }))
    expect(onOpen).toHaveBeenCalledWith('fork:f1', 'cp-head')
  })

  it('refuses invalid JSON', () => {
    const onFork = vi.fn()
    render(<ForkEditor threadId="t" row={row} state={state} nodes={nodes} onFork={onFork} onOpenThread={() => {}} />)
    fireEvent.change(screen.getByLabelText('Fork values'), { target: { value: '{ nope' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run fork' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid JSON')
    expect(onFork).not.toHaveBeenCalled()
  })

  it('does not offer __start__ or __end__', () => {
    render(<ForkEditor threadId="t" row={row} state={state} nodes={nodes} onFork={vi.fn()} onOpenThread={() => {}} />)
    const options = Array.from((screen.getByLabelText('As node') as HTMLSelectElement).options).map((o) => o.value)
    expect(options).toEqual(['plan', 'tools', 'answer'])
  })
})
```

- [ ] **Step 2-4:** fail, implement, pass.
- [ ] **Step 5: Commit** `feat(ui): fork editor sends only changed channels`

---

### Task 19: App wiring, keyboard, URL and perf marks

**Files:**
- Create: `scripts/capture_fixtures.py`, `ui/src/test/fixtures/lisbon.json` (generated), `ui/src/App.test.tsx`
- Modify: `ui/src/App.tsx`, `ui/src/styles.css`

**Behavior (all required):**
- On mount: `api.health()` and `api.threads()`; if `health.graph`, `api.graph()`.
- URL `?thread=<id>&cp=<id>` picks the thread and checkpoint; otherwise the first thread and its newest checkpoint. Keep the URL in sync with `history.replaceState`.
- After the rows of a thread are first rendered, call `performance.mark('fr:timeline-ready')` once per page load (in a `useEffect` after the rows state is set, inside `requestAnimationFrame`). The perf test reads this mark.
- State fetching is lazy with a per-thread cache (`Map` in a ref); diff mode also fetches the parent (or compare) state.
- Layout: header (`flight-recorder`, the source file name from health, a chip `graph loaded` or `read only`, and the key hints `j/k step  d diff  f fork  shift+click compare  esc back`), then three panes: ThreadList, Timeline, and a right pane with three toggle buttons `State`, `Diff`, `Fork` (`aria-pressed`). `Fork` is disabled without a graph, with the title `Start with --graph module:attr to fork`.
- Keys on `window` (ignored when focus is in `input`, `textarea` or `select`, or when Ctrl, Meta or Alt is held): `j` next checkpoint, `k` previous, `d` toggles Diff/State, `f` opens Fork when allowed, `Escape` returns to State and clears the compare selection.
- Shift+click on a timeline row sets `compareId`; Diff then compares compare -> selected; without compare it compares parent -> selected (labels `step <n>`; root says `No parent`).
- After a fork succeeds: reload the thread list. `Open fork` selects the fork thread and its head checkpoint.

- [ ] **Step 1: Generate realistic fixtures from the real API**

`scripts/capture_fixtures.py`:
```python
"""Dump real API responses for the sample threads into ui/src/test/fixtures/lisbon.json (UI tests)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from flight_recorder.cli import build_app
from flight_recorder.samples import make_sample_db

OUT = Path(__file__).resolve().parents[1] / "ui" / "src" / "test" / "fixtures" / "lisbon.json"


def main() -> None:
    db = make_sample_db(Path(tempfile.mkdtemp(prefix="fr-fixtures-")) / "checkpoints.sqlite")
    app, closers = build_app(str(db), "flight_recorder.samples:graph", None)
    try:
        c = TestClient(app)
        data: dict = {"health": c.get("/api/health").json(), "graph": c.get("/api/graph").json()}
        data["threads"] = c.get("/api/threads").json()
        data["checkpoints"], data["states"] = {}, {}
        for t in data["threads"]:
            rows = c.get(f"/api/threads/{t['thread_id']}/checkpoints").json()
            data["checkpoints"][t["thread_id"]] = rows
            for r in rows:
                url = f"/api/threads/{t['thread_id']}/checkpoints/{r['checkpoint_id']}"
                data["states"][r["checkpoint_id"]] = c.get(url).json()
    finally:
        for close in closers:
            close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
```
Run `uv run python scripts/capture_fixtures.py` -> `wrote ...lisbon.json`. Commit the JSON (it is test data, about 30 KB).

- [ ] **Step 2: Write the failing test** `ui/src/App.test.tsx`

```tsx
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import fixture from './test/fixtures/lisbon.json'
import { App } from './App'

type Fx = typeof fixture
const fx = fixture as Fx & { checkpoints: Record<string, { checkpoint_id: string }[]>; states: Record<string, unknown> }

function serve(health = fx.health) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string) => {
      const url = new URL(input, 'http://x')
      const parts = url.pathname.split('/').map(decodeURIComponent)
      let body: unknown = { detail: 'not found' }
      let status = 200
      if (url.pathname === '/api/health') body = health
      else if (url.pathname === '/api/threads') body = fx.threads
      else if (url.pathname === '/api/graph') body = fx.graph
      else if (parts[4] === 'checkpoints' && parts.length === 5) body = fx.checkpoints[parts[3]]
      else if (parts[4] === 'checkpoints' && parts.length === 6) body = fx.states[parts[5]]
      else status = 404
      return new Response(JSON.stringify(body), { status })
    }),
  )
}

const rowsOf = (tid: string) => fx.checkpoints[tid]
const selectedRow = () => screen.getAllByTestId('timeline-row').find((r) => r.getAttribute('aria-selected') === 'true')

beforeEach(() => window.history.replaceState(null, '', '/?thread=lisbon-bug'))
afterEach(() => vi.unstubAllGlobals())

describe('App', () => {
  it('opens the thread from the url and shows its newest checkpoint', async () => {
    serve()
    render(<App />)
    const rows = rowsOf('lisbon-bug')
    await waitFor(() => expect(selectedRow()).toHaveAttribute('data-checkpoint-id', rows[rows.length - 1].checkpoint_id))
    await waitFor(() => expect(screen.getByTestId('inspector')).toHaveTextContent('TP1351'))
  })

  it('steps with j and k and keeps the url in sync', async () => {
    serve()
    render(<App />)
    const rows = rowsOf('lisbon-bug')
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    act(() => void fireEvent.keyDown(window, { key: 'k' }))
    await waitFor(() => expect(selectedRow()).toHaveAttribute('data-checkpoint-id', rows[rows.length - 2].checkpoint_id))
    expect(window.location.search).toContain(`cp=${rows[rows.length - 2].checkpoint_id}`)
    act(() => void fireEvent.keyDown(window, { key: 'j' }))
    await waitFor(() => expect(selectedRow()).toHaveAttribute('data-checkpoint-id', rows[rows.length - 1].checkpoint_id))
  })

  it('d shows the diff against the parent', async () => {
    serve()
    render(<App />)
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    act(() => void fireEvent.keyDown(window, { key: 'd' }))
    await waitFor(() => expect(screen.getByTestId('diff-panel')).toBeInTheDocument())
    await waitFor(() => expect(screen.getAllByTestId('diff-op').length).toBeGreaterThan(0))
  })

  it('f opens the fork editor only when a graph is loaded', async () => {
    serve({ ...fx.health, graph: false })
    const { unmount } = render(<App />)
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    act(() => void fireEvent.keyDown(window, { key: 'f' }))
    expect(screen.queryByLabelText('Fork values')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fork' })).toBeDisabled()
    unmount()
    vi.unstubAllGlobals()
    serve()
    render(<App />)
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    await waitFor(() => expect(screen.getByRole('button', { name: 'Fork' })).toBeEnabled())
    act(() => void fireEvent.keyDown(window, { key: 'f' }))
    await waitFor(() => expect(screen.getByLabelText('Fork values')).toBeInTheDocument())
  })

  it('ignores keys while typing', async () => {
    serve()
    render(<App />)
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    const before = selectedRow()!.getAttribute('data-checkpoint-id')
    act(() => void fireEvent.keyDown(window, { key: 'f' }))
    const box = await screen.findByLabelText('Fork values')
    fireEvent.keyDown(box, { key: 'k' })
    expect(selectedRow()!.getAttribute('data-checkpoint-id')).toBe(before)
  })
})
```
(If the JSON import needs a type, `resolveJsonModule` is already on. Adjust the fetch stub only if `api.ts` calls differ; do not weaken the assertions.)

- [ ] **Step 3: Run** `pnpm test` -> App tests fail (placeholder App).
- [ ] **Step 4: Implement** `App.tsx` to the behavior list.
- [ ] **Step 5: Run** `pnpm test`, `pnpm typecheck` -> all pass.
- [ ] **Step 6: Commit** `feat(ui): wire the app with keyboard, url state and perf mark`

---

### Task 20: Visual pass, responsive layout, bundle into the wheel

**Files:**
- Modify: `ui/src/styles.css`, components as needed (no behavior changes; all tests must stay green)

- [ ] **Step 1: Polish** with the design direction above. Requirements: three panes at widths >= 1100px (threads 240px, timeline 420px, right pane fills); below 1100px the thread list becomes a `<select aria-label="Thread">` above the timeline and the right pane stacks under a 45vh timeline; nothing scrolls horizontally at 390px wide. Selected row: accent left border and tinted background; compare row: dashed accent outline; scratch-origin rows: accent lane dot. Focus rings visible. Respect `prefers-reduced-motion` (no transitions then). The empty states have one plain sentence each.
- [ ] **Step 2: Build and look at it**

```powershell
cd $R\ui
pnpm build
cd $R
uv run flight-recorder demo --dir .e2e\look --port 5320
```
Expected: `pnpm build` writes `src/flight_recorder/static/index.html` and `assets/`. The browser opens `http://127.0.0.1:5320/`. Walk the demo story by hand: `k` twice to the `plan` step, `d`, `f`, edit `depart_after`, `Run fork`, `Open fork`. Stop the server (Ctrl+C).
- [ ] **Step 3: Wheel smoke**

```powershell
cd $R
uv build
uv venv .e2e\wheel-venv --python 3.12
uv pip install --python .e2e\wheel-venv dist\langgraph_flight_recorder-0.1.0-py3-none-any.whl
.e2e\wheel-venv\Scripts\flight-recorder.exe --version
python -c "import zipfile,glob;z=zipfile.ZipFile(glob.glob('dist/*.whl')[0]);print(sum(n.startswith('flight_recorder/static/') for n in z.namelist()))"
```
Expected: `flight-recorder 0.1.0`; the count of static files is at least 2.
- [ ] **Step 4:** `pnpm -C ui test` still passes.
- [ ] **Step 5: Commit** `feat(ui): flight data recorder visual design and responsive layout`

---

### Task 21: Playwright end-to-end flow and README screenshots

**Files:**
- Create: `ui/playwright.config.ts`, `ui/e2e/flow.spec.ts`, `docs/img/` (screenshots)

- [ ] **Step 1: Write** `ui/playwright.config.ts`

```ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: 'e2e',
  testIgnore: /perf\.spec\.ts/,
  timeout: 60_000,
  use: { baseURL: 'http://127.0.0.1:5322', trace: 'retain-on-failure', viewport: { width: 1440, height: 900 } },
  webServer: {
    command: 'uv run --project .. flight-recorder demo --dir ../.e2e/demo --port 5322 --no-browser',
    url: 'http://127.0.0.1:5322/api/health',
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
})
```

- [ ] **Step 2: Write** `ui/e2e/flow.spec.ts`

```ts
import { expect, test } from '@playwright/test'

const shots = process.env.FR_SCREENSHOTS === '1'
const shot = async (page: import('@playwright/test').Page, name: string) => {
  if (shots) await page.screenshot({ path: `../docs/img/${name}.png` })
}

test('find the dropped date filter and fix it with a fork', async ({ page }) => {
  await page.goto('/?thread=lisbon-bug')
  const rows = page.getByTestId('timeline-row')
  await expect(rows).toHaveCount(5)
  await expect(page.getByTestId('inspector')).toContainText('TP1351') // the wrong, October answer

  // step back to the checkpoint written by the plan node
  await page.keyboard.press('k')
  await page.keyboard.press('k') // rows: input, __start__, plan, tools, answer
  await expect(page.getByTestId('inspector')).toContainText('search_flights')
  await expect(page.getByTestId('timeline-row').nth(2)).toHaveAttribute('aria-selected', 'true')
  await shot(page, '01-timeline')

  await page.keyboard.press('d')
  await expect(page.getByTestId('diff-panel')).toContainText('messages')
  await shot(page, '02-diff')

  await page.keyboard.press('f')
  const box = page.getByLabel('Fork values')
  const text = await box.inputValue()
  await box.fill(text.replace('"depart_after": null', '"depart_after": "2026-11-01"'))
  await expect(page.getByLabel('As node')).toHaveValue('plan')
  await page.getByRole('button', { name: 'Run fork' }).click()
  await expect(page.getByTestId('fork-result')).toContainText('done')
  await page.getByRole('button', { name: 'Open fork' }).click()

  await expect(rows).toHaveCount(6)
  await expect(page.getByTestId('inspector')).toContainText('TP1363') // the right, November answer
  await expect(page.locator('[data-origin="scratch"]').first()).toBeVisible()
  await shot(page, '03-fork')
})

test('the source thread is unchanged after the fork', async ({ page }) => {
  await page.goto('/?thread=lisbon-bug')
  await expect(page.getByTestId('timeline-row')).toHaveCount(5)
  await expect(page.getByTestId('inspector')).toContainText('TP1351')
})
```

- [ ] **Step 3: Run**

```powershell
cd $R\ui
pnpm e2e
$env:FR_SCREENSHOTS = '1'; pnpm exec playwright test; Remove-Item Env:FR_SCREENSHOTS
```
Expected: `2 passed` both times; `docs/img/01-timeline.png`, `02-diff.png`, `03-fork.png` exist. Look at each PNG with the Read tool and fix anything ugly or cut off before committing. If the Chromium build for 1.63 is missing, run `pnpm exec playwright install chromium` and record it.

- [ ] **Step 4: Commit** `test(ui): playwright flow from bug to fix, with screenshots`

---

### Task 22: Docker image and compose demo

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `tests/test_compose.py`

- [ ] **Step 1: Write the failing test** `tests/test_compose.py`

```python
"""Invariant 7 for Docker: every published port is bound to the host loopback."""

import re
from pathlib import Path

COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yml"


def published_ports(text: str) -> list[str]:
    ports, in_ports = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ports:"):
            in_ports = True
            continue
        if in_ports and stripped.startswith("- "):
            ports.append(stripped[2:].strip().strip("\"'"))
        elif in_ports and stripped:
            in_ports = False
    return ports


def test_compose_ports_loopback_only():
    ports = published_ports(COMPOSE.read_text(encoding="utf-8"))
    assert ports, "expected at least one published port"
    for p in ports:
        assert p.startswith("127.0.0.1:"), f"port {p!r} is not bound to 127.0.0.1"


def test_names_are_prefixed():
    text = COMPOSE.read_text(encoding="utf-8")
    assert re.search(r"^name: flight-recorder$", text, re.M)
    assert "container_name: flight-recorder-demo" in text


def test_parser_catches_a_public_port():
    assert published_ports('services:\n  a:\n    ports:\n      - "5324:5320"\n') == ["5324:5320"]
```

- [ ] **Step 2: Run** `uv run pytest tests/test_compose.py -q` -> fails (no compose file).

- [ ] **Step 3: Write the Docker files**

`Dockerfile`:
```dockerfile
# Stage 1: build the UI bundle
FROM node:24-slim AS ui
WORKDIR /app/ui
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
COPY ui/package.json ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY ui/ ./
RUN pnpm exec vite build --outDir /app/static --emptyOutDir

# Stage 2: build the wheel with the UI inside, and the locked requirements
FROM python:3.12-slim AS build
WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.21
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY --from=ui /app/static ./src/flight_recorder/static
RUN uv build --wheel --out-dir /dist \
 && uv export --frozen --no-dev --no-emit-project --no-hashes -o /dist/requirements.txt

# Stage 3: runtime
FROM python:3.12-slim
COPY --from=build /dist /tmp/dist
RUN pip install --no-cache-dir -r /tmp/dist/requirements.txt \
 && pip install --no-cache-dir --no-deps /tmp/dist/*.whl \
 && rm -rf /tmp/dist \
 && useradd --create-home app
USER app
WORKDIR /home/app
EXPOSE 5320
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5320/api/health')"
# 0.0.0.0 inside the container only; compose publishes it on the host loopback (ADR 0007)
CMD ["flight-recorder", "demo", "--dir", "/home/app/demo", "--port", "5320", "--host", "0.0.0.0", "--i-know-this-is-unauthenticated", "--no-browser"]
```

`.dockerignore`:
```text
.git
.venv
**/__pycache__
ui/node_modules
ui/test-results
ui/playwright-report
src/flight_recorder/static
dist
.e2e
.bench
bench/results
docs
```

`docker-compose.yml`:
```yaml
name: flight-recorder
services:
  demo:
    build: .
    image: flight-recorder:dev
    container_name: flight-recorder-demo
    ports:
      - "127.0.0.1:5324:5320"
```

- [ ] **Step 4: Run**

```powershell
uv run pytest tests/test_compose.py -q
docker compose build 2>&1 | Select-Object -Last 5
docker compose up -d
Start-Sleep -Seconds 10
curl.exe -s http://127.0.0.1:5324/api/health
curl.exe -s http://127.0.0.1:5324/ | Select-String -Pattern '<div id="root">' -Quiet
docker compose down
```
Expected: `3 passed`; build ends with the image tagged `flight-recorder:dev`; health returns `{"ok":true,...,"graph":true,...}`; `True`; down removes `flight-recorder-demo`.

- [ ] **Step 5: Commit** `feat: docker image and loopback-only compose demo`

---

### Task 23: CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write** `.github/workflows/ci.yml`

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:

jobs:
  python:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest] # SQLite file locking differs; invariant 1 runs on both
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv==0.12.21
      - run: uv sync --locked
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pytest -q

  ui:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ui
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
      - run: corepack enable
      - run: pnpm install --frozen-lockfile
      - run: pnpm typecheck
      - run: pnpm test
      - run: pnpm build

  e2e:
    needs: [python, ui]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv==0.12.21
      - run: uv sync --locked
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
      - run: corepack enable
      - run: pnpm -C ui install --frozen-lockfile
      - run: pnpm -C ui exec playwright install --with-deps chromium
      - run: pnpm -C ui e2e

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t flight-recorder:ci .
```

- [ ] **Step 2: Lint the workflow**

```powershell
docker run --rm -v "${R}:/repo" -w /repo rhysd/actionlint:latest -color
```
Expected: no output, exit 0. Record the actionlint version it prints with `-version` in the ledger. The workflow cannot run here (no remote, no push); say so in the handoff.

- [ ] **Step 3: Commit** `ci: python on ubuntu and windows, ui, e2e and docker build`

---

### Task 24: Benchmarks and the headline number

**Files:**
- Create: `bench/bench.py`, `bench/headline.py`, `ui/bench/diff-bench.ts`, `ui/playwright.perf.config.ts`, `ui/e2e/perf.spec.ts`, `bench/results/.gitkeep`
- Generates (committed): `bench/results/api.json`, `bench/results/diff.json`, `bench/results/ui.json`

Every number in these files is measured by the code below. Nothing is typed by hand.

- [ ] **Step 1: Write** `bench/bench.py` (API, fork and immutability on a 10,000-checkpoint thread)

```python
"""API benchmark on a generated 10,000-checkpoint thread. Writes bench/results/api.json.

Starts the real server on 127.0.0.1:5323, measures with httpx, stops it, and checks the source
directory is byte-identical afterwards. Run: uv run python bench/bench.py
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

import httpx

from flight_recorder.samples import make_sample_db

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".bench" / "api"
OUT = ROOT / "bench" / "results" / "api.json"
PORT = 5323
BASE = f"http://127.0.0.1:{PORT}"
N = 10_000


def fingerprint(folder: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))], 1)


def timed(client: httpx.Client, method: str, url: str, **kw) -> tuple[float, httpx.Response]:
    t0 = time.perf_counter()
    r = client.request(method, url, **kw)
    ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return ms, r


def main() -> None:
    t0 = time.perf_counter()
    db = make_sample_db(WORK / "checkpoints.sqlite", long_checkpoints=N)
    gen_s = round(time.perf_counter() - t0, 1)
    before = fingerprint(db.parent)
    cmd = [sys.executable, "-m", "flight_recorder", "serve", "--db", str(db), "--graph",
           "flight_recorder.samples:graph", "--port", str(PORT), "--no-browser"]  # fmt: skip
    server = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url=BASE, timeout=60) as c:
            for _ in range(100):
                try:
                    if c.get("/api/health").status_code == 200:
                        break
                except httpx.TransportError:
                    time.sleep(0.2)
            tid = f"long-{N}"
            cold_ms, r = timed(c, "GET", f"/api/threads/{tid}/checkpoints")
            rows = r.json()
            assert len(rows) == N, len(rows)
            payload_kb = round(len(r.content) / 1024, 1)
            warm = [timed(c, "GET", f"/api/threads/{tid}/checkpoints")[0] for _ in range(20)]
            picks = [rows[i]["checkpoint_id"] for i in range(0, N, N // 50)]
            state = [timed(c, "GET", f"/api/threads/{tid}/checkpoints/{cid}")[0] for cid in picks]
            bug = c.get("/api/threads/lisbon-bug/checkpoints").json()
            plan = next(x for x in bug if x["writes_from"] == ["plan"])
            values = c.get(f"/api/threads/lisbon-bug/checkpoints/{plan['checkpoint_id']}").json()["values"]
            values["messages"][-1]["tool_calls"][0]["args"]["depart_after"] = "2026-11-01"
            body = {"thread_id": "lisbon-bug", "checkpoint_id": plan["checkpoint_id"],
                    "values": {"messages": values["messages"]}, "as_node": "plan"}  # fmt: skip
            fork_client, fork_server, answers = [], [], set()
            for _ in range(5):
                ms, fr = timed(c, "POST", "/api/forks", json=body)
                res = fr.json()
                fork_client.append(ms)
                fork_server.append(res["elapsed_ms"])
                answers.add(res["events"][-1]["update"]["messages"][0]["content"])
    finally:
        server.terminate()
        server.wait(timeout=30)
    after = fingerprint(db.parent)
    result = {
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "cpu_count": os.cpu_count(),
            "python": platform.python_version(),
            "langgraph": version("langgraph"),
        },
        "checkpoints": N,
        "fixture_generation_s": gen_s,
        "source_db_mb": round(db.stat().st_size / 1e6, 1),
        "index_cold_ms": round(cold_ms, 1),
        "index_warm_p50_ms": pct(warm, 0.5),
        "index_warm_p95_ms": pct(warm, 0.95),
        "index_payload_kb": payload_kb,
        "state_p50_ms": pct(state, 0.5),
        "state_p95_ms": pct(state, 0.95),
        "fork_roundtrip_p50_ms": pct(fork_client, 0.5),
        "fork_server_p50_ms": pct(fork_server, 0.5),
        "fork_answers": sorted(answers),
        "forks_run": len(fork_client),
        "source_files_before": sorted(before),
        "source_files_after": sorted(after),
        "source_unchanged": before == after,
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write** `ui/bench/diff-bench.ts` (runs with Node 24's built-in TypeScript stripping)

```ts
// Diff two ~1 MB states 30 times; writes ../bench/results/diff.json. Run: pnpm bench:diff
import { writeFileSync, mkdirSync } from 'node:fs'
import os from 'node:os'
import { diff, type Json } from '../src/lib/diff.ts'

function state(n: number, edit: boolean): Json {
  const messages = Array.from({ length: n }, (_, i) => ({
    __lc_message__: i % 2 ? 'ai' : 'human',
    id: `m-${i}`,
    content: `${edit && i % 100 === 7 ? 'EDITED ' : ''}${'lorem ipsum dolor sit amet '.repeat(16)}${i}`,
    tool_calls: i % 2 ? [{ name: 'search', args: { q: `q${i}`, page: i % 5 }, id: `c-${i}` }] : [],
  }))
  if (edit) {
    messages.splice(10, 0, { __lc_message__: 'ai', id: 'new-1', content: 'inserted', tool_calls: [] })
    ;[messages[20], messages[21]] = [messages[21], messages[20]]
  }
  return { messages, count: n }
}

const a = state(2000, false)
const b = state(2000, true)
const bytes = JSON.stringify(a).length
const times: number[] = []
let ops = 0
for (let i = 0; i < 35; i++) {
  const t0 = performance.now()
  ops = diff(a, b).length
  const ms = performance.now() - t0
  if (i >= 5) times.push(ms) // first 5 are JIT warm-up
}
times.sort((x, y) => x - y)
const pick = (q: number) => Math.round(times[Math.min(times.length - 1, Math.round(q * (times.length - 1)))] * 10) / 10
const result = {
  machine: { platform: `${os.type()} ${os.release()}`, cpu: os.cpus()[0]?.model ?? 'unknown', node: process.version },
  state_bytes: bytes,
  ops,
  runs: times.length,
  diff_p50_ms: pick(0.5),
  diff_p95_ms: pick(0.95),
}
mkdirSync('../bench/results', { recursive: true })
writeFileSync('../bench/results/diff.json', JSON.stringify(result, null, 2) + '\n')
console.log(result)
```

- [ ] **Step 3: Write** `ui/playwright.perf.config.ts` and `ui/e2e/perf.spec.ts`

```ts
// ui/playwright.perf.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: 'e2e',
  testMatch: /perf\.spec\.ts/,
  timeout: 300_000,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:5325', viewport: { width: 1440, height: 900 } },
  webServer: {
    command: 'uv run --project .. flight-recorder demo --dir ../.bench/ui --long 10000 --port 5325 --no-browser',
    url: 'http://127.0.0.1:5325/api/health',
    reuseExistingServer: false,
    timeout: 240_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
})
```

```ts
// ui/e2e/perf.spec.ts
import { mkdirSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import { expect, test } from '@playwright/test'

const N = 10_000
const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b)
  return Math.round(s[Math.floor(s.length / 2)] * 10) / 10
}
const p95 = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b)
  return Math.round(s[Math.min(s.length - 1, Math.round(0.95 * (s.length - 1)))] * 10) / 10
}

test('open and scrub a 10,000-checkpoint thread', async ({ browser, browserName }) => {
  const opens: number[] = []
  for (let run = 0; run < 6; run++) {
    const context = await browser.newContext()
    const page = await context.newPage()
    await page.goto(`/?thread=long-${N}`)
    await expect(page.getByTestId('timeline')).toHaveAttribute('data-count', String(N), { timeout: 60_000 })
    await expect(page.getByTestId('timeline-row').first()).toBeVisible()
    const ms = await page.evaluate(async () => {
      for (let i = 0; i < 200 && performance.getEntriesByName('fr:timeline-ready').length === 0; i++) {
        await new Promise((r) => setTimeout(r, 25))
      }
      return performance.getEntriesByName('fr:timeline-ready')[0]?.startTime ?? -1
    })
    expect(ms).toBeGreaterThan(0)
    opens.push(ms)
    await context.close()
  }

  const page = await browser.newPage()
  await page.goto(`/?thread=long-${N}`)
  await expect(page.getByTestId('timeline')).toHaveAttribute('data-count', String(N), { timeout: 60_000 })
  await expect(page.getByTestId('inspector')).not.toHaveAttribute('data-checkpoint-id', '')
  // 50 presses of k from the newest row: every step lands on a checkpoint whose state is not cached yet
  const steps: number[] = await page.evaluate(async () => {
    const out: number[] = []
    const inspector = () => document.querySelector('[data-testid="inspector"]')!.getAttribute('data-checkpoint-id')
    const frame = () => new Promise((r) => requestAnimationFrame(() => r(null)))
    for (let i = 0; i < 50; i++) {
      const before = inspector()
      const t0 = performance.now()
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k' }))
      while (inspector() === before) await frame()
      out.push(performance.now() - t0)
    }
    return out
  })
  const result = {
    machine: { platform: `${os.type()} ${os.release()}`, cpu: os.cpus()[0]?.model ?? 'unknown', browser: `${browserName} ${browser.version()}` },
    checkpoints: N,
    open_cold_ms: Math.round(opens[0] * 10) / 10,
    open_warm_median_ms: median(opens.slice(1)),
    open_runs: opens.map((x) => Math.round(x)),
    step_median_ms: median(steps),
    step_p95_ms: p95(steps),
    step_runs: steps.length,
  }
  mkdirSync('../bench/results', { recursive: true })
  writeFileSync('../bench/results/ui.json', JSON.stringify(result, null, 2) + '\n')
  console.log(result)
})
```
"Open" is the time from navigation start to the `fr:timeline-ready` mark (the first frame with the 10,000-row timeline rendered). The first run includes the server's cold index build; the rest hit its cache.

- [ ] **Step 4: Write** `bench/headline.py`

```python
"""Build the README headline from bench/results/*.json, or check that README.md contains it.

uv run python bench/headline.py               prints the headline and the numbers table
uv run python bench/headline.py --check README.md   exits 1 if README.md lacks the headline
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"


def load(name: str) -> dict | None:
    p = RESULTS / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def headline() -> str:
    api, ui = load("api.json"), load("ui.json")
    if api is None:
        raise SystemExit("bench/results/api.json is missing; run: uv run python bench/bench.py")
    if not api["source_unchanged"]:
        raise SystemExit("the source changed during the benchmark; fix that before publishing any number")
    n = f"{api['checkpoints']:,}"
    if ui is not None:
        opens = f"opens a {n}-checkpoint LangGraph thread in {ui['open_warm_median_ms']:g} ms"
        steps = f"steps between checkpoints in {ui['step_median_ms']:g} ms"
    else:
        opens = f"lists a {n}-checkpoint LangGraph thread in {api['index_warm_p50_ms']:g} ms"
        steps = f"loads a checkpoint's state in {api['state_p50_ms']:g} ms"
    return f"**flight-recorder {opens}, {steps}, and forks any step without changing a byte of the original.**"


def main(argv: list[str]) -> int:
    line = headline()
    if len(argv) == 2 and argv[0] == "--check":
        text = Path(argv[1]).read_text(encoding="utf-8")
        if line not in text:
            print(f"README is missing the measured headline:\n{line}", file=sys.stderr)
            return 1
        print("README headline matches bench/results")
        return 0
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 5: Run the benchmarks** (close other heavy apps first; note in the ledger if anything else was running)

```powershell
cd $R
uv run python bench/bench.py
cd ui
pnpm bench:diff
pnpm perf
cd ..
uv run python bench/headline.py
```
Expected: `bench/results/api.json` with `"source_unchanged": true`, `"forks_run": 5`, `fork_answers` equal to `["Cheapest: TP1363 on 2026-11-03 for EUR 142."]`; `diff.json` with `state_bytes` near 1,000,000 (record the real value); `ui.json` with 6 open runs and 50 step runs; the headline prints. If `pnpm perf` cannot run (browser or timeout), record `Ruling: ui perf not measured - <exact error> - headline falls back to the API number` and continue; `headline.py` handles the missing file. Never edit a result file by hand.

- [ ] **Step 6: Commit** `bench: measured api, diff and ui numbers on a 10,000-checkpoint thread`

---

### Task 25: README, DEVDOCS, handoff and the gates

**Files:**
- Create: `README.md` (replace stub), `docs/DEVDOCS.md`, `docs/handoff.md`
- Modify: ledger

- [ ] **Step 1: Write** `README.md` in this order. Every number comes from `bench/results/*.json`; copy them, never round differently.
  1. `# flight-recorder`, then the exact line printed by `uv run python bench/headline.py`.
  2. `![Forking the flight-search agent with the date filter restored](docs/img/03-fork.png)`
  3. **Try it in 30 seconds**: `uv tool install <path to wheel>` or `pipx install <path to wheel>` (PyPI publishing is not done yet; say so), then `flight-recorder demo`. Two sentences on the story: the agent drops "after 2026-11-01", press `k` twice, `d`, `f`, fix `depart_after`, run, open the fork.
  4. **Use it on your agent**: `flight-recorder serve --db path/to/checkpoints.sqlite --graph your_module:graph` and that `--graph` is only needed for forks. Note: reading never imports your code; forking does.
  5. **What it guarantees**: the invariants table from the spec with the test names, including the source-dir SHA-256 check on ubuntu and windows CI.
  6. **Benchmarks**: a table from the three JSON files (open cold/warm, step median/p95, index cold/warm p50, state p50, fork round trip p50, diff p50 on `state_bytes` bytes) and the machine lines; then the commands to reproduce.
  7. **How it works**: the mermaid diagram from the spec and three sentences.
  8. **Decisions and trade-offs**: one line per ADR with a link and its "what I gave up" in a few words.
  9. **Limits (v0.1)**: SQLite only, no SSE, no graph view, no export, no subgraph forks, `builder.compile` drops compile options, LangGraph serializer warning line on forks, not on PyPI yet.
  10. **Development**: the gate commands.
- [ ] **Step 2: Write** `docs/DEVDOCS.md` in the order the lead requires (it will be rewritten by the lead at the end, so keep it accurate rather than long): what it is plus the headline number; 5-minute quickstart with exact commands; architecture with one mermaid diagram; project layout table; run, test and benchmark commands; key decisions and what they gave up (ADR links); known limits and what is left.
- [ ] **Step 3: Write** `docs/handoff.md` with a first entry: `## 2026-10-04 - Claude (Sonnet builder) - main`, what changed (by area), what is left (v0.2 list from the spec), how to verify (the gate commands), and any `Ruling:` lines that matter to the reviewer.
- [ ] **Step 4: Run every gate** listed in "Gates" above, in order, and paste each real result line into the ledger as `Gate N: <command> -> <result>`. Stop and fix if any fails. Run `uv run python bench/headline.py --check README.md` last.
- [ ] **Step 5: Final checks**

```powershell
git status --short
git ls-files | Select-String -Pattern '\.env|node_modules|\.venv|static/' -Quiet
```
Expected: clean tree after the commit; the `Select-String` prints `False`.
- [ ] **Step 6: Commit** `docs: readme with measured headline, devdocs and handoff`

Then append `FINAL: all gates passed (<count> pytest, <count> vitest, 2 playwright)` to the ledger with the real counts, or `BLOCKED: <gate> - <error>` if one cannot pass, and commit the ledger with `chore: update ledger`.
