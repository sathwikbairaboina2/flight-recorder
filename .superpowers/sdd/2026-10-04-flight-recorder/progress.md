# Ledger: flight-recorder v0.1 (2026-10-04)

Plan: docs/superpowers/plans/2026-10-04-flight-recorder.md (25 tasks)
Spec: docs/superpowers/specs/2026-10-04-flight-recorder.md
ADRs: docs/adr/0001 to 0008
Gates: see the plan's "Gates" section (ruff check, ruff format --check, pytest, ui typecheck + test + build, playwright e2e, wheel install, docker compose health on 5324, bench results + headline --check)
Commits: local only, never push. Trailer: Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Format: "Task N: complete (tests: <cmd> -> <real line>; red seen: ...)", "Ruling: <decision> - <reason> - <cost>", "PARTIAL: next is Task N, step M"

Task 0 (plan, Opus): complete (spec, ADRs 0001-0008, plan, ledger written; repo initialized with git init -b main)
Prototype: mode=ro open of a WAL db creates -wal and -shm beside the source (LangGraph 1.2.12, Windows 11) -> ADR 0001 snapshot copy
Prototype: snapshot copy with a live writer holding un-checkpointed WAL frames -> copy has 3 rows, source dir byte-identical
Prototype: default serde turns an unimportable dataclass into None and a pydantic model into a dict -> ADR 0002 safe ext hook keeps both
Prototype: SqliteSaver.list() over 10,000 checkpoints 3.6 s; SQL index ~0.33 s warm -> ADR 0003
Prototype: index next/parent_id equal get_state_history for lisbon-bug, lisbon-branched (update_state branch) and a fork thread
Prototype: uuid6 checkpoint_id time is within 0.6 ms of checkpoint.ts (separate clock calls) -> tests allow 5 ms
Prototype: reference package of plan Tasks 1-11 -> pytest 63 passed in 8.5 s (+ test_smoke = 64); ruff check and format clean
Prototype: wheel from the Task 1 pyproject contains flight_recorder/static/**; fresh venv install served /api/health, /api/threads, / on 5329
Prototype: diff.ts passed 3,000 fast-check round trips and 2,000 shuffle-only-moves runs; lanes.ts linear/branched/orphan cases as expected
Prototype: 10,000-checkpoint fixture generation 18.3 s with PRAGMA synchronous=OFF (257 s without)
Ruling: v0.1 scope = read + step + diff + synchronous fork + wheel + docker + bench; SSE, graph view, export, Postgres, subgraph forks deferred to v0.2 (ADRs 0004, 0008) - fits ~25 tasks and keeps the fork wow - no graph view in the demo
Ruling: default port 5320 (session owns 5320-5329) instead of the design doc's 7341 - isolation rule - unconventional port (ADR 0007)
Ruling: the index reads the SqliteSaver table with SQL instead of the checkpointer API - 10x faster on 10k checkpoints - schema coupling, guarded by check_schema (ADR 0003)
Ruling: forks copy only the ancestor chain into an ephemeral scratch db - clean slate per session - forks lost on exit unless --scratch (ADR 0005)
Ruling: ledger is tracked in git - matches co-author - none
Task 1: complete (tests: uv run pytest -q -> 1 passed; ruff check -> All checks passed!; red seen: n/a scaffold)
Task 2: complete (tests: uv run pytest tests/test_samples.py -q -> 5 passed; red seen: yes, ModuleNotFoundError flight_recorder.samples)
Task 3: complete (tests: uv run pytest tests/test_snapshot.py -q -> 5 passed; red seen: yes, collection error no module snapshot)
Task 4: complete (tests: uv run pytest tests/test_bridge.py -q -> 8 passed; red seen: yes in effect, modules did not exist before the files were written)
Task 5: complete (tests: uv run pytest tests/test_index.py -q -> 8 passed; red seen: in effect, module absent before write)
Task 6: complete (tests: uv run pytest tests/test_reader.py tests/test_decode.py -q -> 7 passed; red seen: yes, collection errors)
Task 7: complete (tests: uv run pytest tests/test_graph_loader.py -q -> 6 passed; red seen: yes, collection error)
Task 8: complete (tests: uv run pytest tests/test_fork.py -q -> 7 passed; red seen: module fork absent before write)
