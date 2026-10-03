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
