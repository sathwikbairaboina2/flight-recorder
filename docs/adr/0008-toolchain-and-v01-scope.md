# ADR-0008: Host toolchain for development, Docker for the demo, and a narrow v0.1 UI

- Status: accepted (2026-10-04)

## Decision
- Development and tests run on the host with `uv` (own `.venv`) and `pnpm` (own `ui/node_modules`).
  Docker is used for the packaged demo image and compose, not for every test run. CI runs pytest on
  ubuntu and windows (SQLite file locking differs) and the UI tests and Playwright on ubuntu.
- The UI is React 19 + Vite 8 + TypeScript 7 + TanStack Virtual, matching the sibling `co-author`
  repo. No component library.
- v0.1 has no graph view (React Flow and dagre), no single-file export and no SSE. The timeline shows
  `writes_from` and `next` node names as text chips instead of a graph.
- Python package `langgraph-flight-recorder` (name free on PyPI on 2026-10-04), import name
  `flight_recorder`, console script `flight-recorder`, built with hatchling, UI bundled at
  `flight_recorder/static`. Not published to PyPI by this session.

## What I gave up
- The graph view is the most visual part of the design doc. The fork story and the diff carry the
  demo instead; React Flow is the second v0.2 item.
- The design doc's fully containerized dev loop. The host already has the exact tools, and named
  volumes on Windows add friction for little gain.
