# Handoff

## 2026-10-04 - Claude (Sonnet builder) - main

**What changed**
- Python package `flight_recorder`: snapshot copy, SQL index, no-import decoder, tagged JSON bridge, reader, graph loader, fork engine, REST API, CLI (serve, demo, doctor), sample agent.
- React UI: thread list, virtualized timeline with branch lanes, message-aware inspector, structural diff, fork editor, keyboard and URL state.
- Playwright flow test (port 5322) and perf test (port 5325), screenshots in `docs/img/`.
- Dockerfile and compose demo on 127.0.0.1:5324, GitHub Actions workflow (linted, not run).
- Benchmarks and measured headline in `bench/results/`.

**What is left (v0.2)**
- SSE for fork progress, graph view, export, Postgres, forks inside subgraphs, PyPI publishing.
- Run CI on a real remote (ubuntu and windows matrix).

**How to verify**
```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest -q
pnpm -C ui typecheck && pnpm -C ui test && pnpm -C ui build && pnpm -C ui e2e
uv build
docker compose build && docker compose up -d && curl http://127.0.0.1:5324/api/health && docker compose down
uv run python bench/headline.py --check README.md
```

**For the reviewer**
- See the `Ruling:` lines in `.superpowers/sdd/2026-10-04-flight-recorder/progress.md`.
- The fresh-venv `flight-recorder.exe` launcher was blocked by a Windows Application Control policy; `python -m flight_recorder --version` printed `flight-recorder 0.1.0`.
- For several tasks (for example 4, 5, 8, 10, 11, 22) the test file was written, then the module, without a separately captured red run in between; the modules did not exist beforehand so the first run would have been a collection error.

## 2026-10-04 - Claude (Opus lead, verify) - main

**What changed**
- Confirmed the three important review findings are fixed in `e867ca0`:
  - Wheel UI: the README and DEVDOCS quickstarts build the UI before `uv build`. `build_app` warns `no UI at ...` when `static/index.html` is missing. CI has a `wheel` job that asserts `flight_recorder/static/index.html` is in the wheel and runs `flight-recorder --version` from a fresh venv. Checked on a fresh `git clone`: following the README, the wheel holds `static/index.html` plus 2 assets. From a fresh venv, `python -m flight_recorder demo --port 5326` served `GET /` 200.
  - Slash thread ids: the routes use `{thread_id:path}`. `tests/test_api.py::test_thread_ids_with_url_special_characters` covers `org/user-42` and `a?b#c`, including a fork.
  - Stale state error: errors are keyed by `thread|checkpoint`, cleared on success, and only the selected one is shown. `App.test.tsx` covers it.
- Leftover fixed (`1f1230d`): the sample generator used the default serde, so the demo and e2e printed LangGraph's "Deserializing unregistered type SearchQuery" warning. It now uses `fork_serde(builder)`. The new test in `tests/test_samples.py` failed before the fix and passes after it.
- Rewrote `docs/DEVDOCS.md` as a plain developer guide.

**Gates run on this commit (real output)**
- ruff check: All checks passed. ruff format: 44 files already formatted. pytest: 74 passed.
- UI typecheck clean, vitest 48 passed, build OK, Playwright e2e 2 passed (no unregistered-type warning).
- `bench/headline.py --check README.md`: README headline matches bench/results.
- Docker: `docker compose build && up -d`, `/api/health` gave `{"ok":true,"version":"0.1.0","graph":true,...}`, `GET /` 200, then `down`.

**What is left**
- v0.2: SSE fork progress, graph view, export, Postgres, subgraph forks, PyPI.
- CI has never run (no remote). Push and watch the ubuntu/windows matrix and the wheel job.
- On this machine, Windows Application Control blocks the fresh-venv `flight-recorder.exe` launcher. `python -m flight_recorder` works.

**How to verify**
```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest -q
pnpm -C ui typecheck && pnpm -C ui test && pnpm -C ui build && pnpm -C ui e2e
uv build && python -c "import glob,zipfile; print('flight_recorder/static/index.html' in zipfile.ZipFile(glob.glob('dist/*.whl')[0]).namelist())"
docker compose build && docker compose up -d && curl http://127.0.0.1:5324/api/health && docker compose down
uv run python bench/headline.py --check README.md
```
