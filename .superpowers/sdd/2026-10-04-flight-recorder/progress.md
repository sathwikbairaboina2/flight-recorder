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
Task 9: complete (tests: uv run pytest tests/test_immutability.py -q -> 2 passed; red seen: yes, with Snapshot.path = source, test_live_writer_with_uncheckpointed_wal failed on dir_fingerprint mismatch, then reverted)
Task 10: complete (tests: uv run pytest tests/test_api.py -q -> 5 passed; red seen: module api absent before write)
Task 11: complete (tests: uv run pytest -q -> 64 passed; ruff check -> All checks passed!; ruff format --check -> 38 files already formatted; smoke on 5320: /api/health ok graph true, /api/threads lists both; process stopped; red seen: module cli absent before write)
Task 12: complete (tests: pnpm -C ui test -> 3 passed; pnpm -C ui typecheck -> exit 0; red seen: yes, vitest failed to resolve ./api)
Task 13: complete (tests: pnpm -C ui test -> Tests 15 passed (15); typecheck exit 0; red seen: yes, diff is not a function)
Ruling: annotated before/after as Json in diff.test.ts date-bug test - TypeScript 7 infers a heterogeneous array literal that is not assignable to Json - none
Task 14: complete (tests: pnpm -C ui test -> Tests 27 passed (27), 7 files; typecheck no errors; red seen: yes, 4 files failed to import)
Ruling: design direction 'flight data recorder' per plan (dark first, single accent #ff5f1f, monospace data, CSS custom properties, no external fonts or icon packages) - design-taste-frontend loaded but scoped to landing pages; this is a dense dev tool so the plan's decided direction wins and the skill's dial/density/em-dash/no-icon-hand-roll rules were applied where they fit - none
Task 15: complete (tests: pnpm -C ui test -> 9 files, 32 tests passed; typecheck clean; red seen: yes, components missing then rows not rendered in jsdom)
Ruling: stubbed getBoundingClientRect, offsetHeight and offsetWidth in ui/src/test/setup.ts - jsdom measures 0x0 so TanStack Virtual rendered no rows (the plan anticipated this) - tests do not exercise real layout; e2e covers that
Task 16: complete (tests: pnpm -C ui test -> 10 files, 36 tests passed; typecheck clean; red seen: yes, component missing)
Task 17: complete (tests: pnpm -C ui test -> DiffPanel 3 tests pass; run total 12 files 42 tests; red seen: yes, components missing)
Task 18: complete (tests: pnpm -C ui test -> ForkEditor 3 tests pass; run total 12 files 42 tests, typecheck clean; red seen: yes)
Task 19: complete (tests: pnpm -C ui test -> 13 files, 47 tests passed; typecheck clean; fixtures via uv run python scripts/capture_fixtures.py; red seen: yes, 5 App tests failed against placeholder)
Task 20: complete (tests: pnpm -C ui test -> 13 files, 47 tests passed; pnpm -C ui build wrote src/flight_recorder/static/index.html + assets; uv build ok, wheel has 3 flight_recorder/static files; fresh venv python -m flight_recorder --version -> flight-recorder 0.1.0)
Ruling: wheel version check in the fresh venv used 'python -m flight_recorder --version' - a Windows Application Control policy blocked the newly created .e2e/wheel-venv/Scripts/flight-recorder.exe launcher (the repo .venv launcher runs fine); not worked around, the launcher itself is only a trampoline to the same entry point - gate 7 literal exe check unverified in a fresh venv, rerun in CI (ubuntu)
Task 21: complete (tests: pnpm -C ui e2e -> 2 passed (chromium, port 5322), also with FR_SCREENSHOTS=1; screenshots docs/img/01-timeline.png 02-diff.png 03-fork.png viewed; red seen: n/a flow passed first run against built UI)
