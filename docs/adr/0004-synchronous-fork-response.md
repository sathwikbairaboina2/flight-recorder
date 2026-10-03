# ADR-0004: v0.1 forks run synchronously and return all events in the response

- Status: accepted (2026-10-04)

## Context
The design doc streamed fork events over SSE. The sample agent's fork round trip took about 94 ms in
the prototype. SSE adds a second endpoint, client reconnect logic and harder tests.

## Decision
`POST /api/forks` copies the ancestor chain, calls `update_state`, runs
`graph.stream(None, config, stream_mode="updates")` to completion or interrupt, and returns
`{status, events, elapsed_ms, ...}`. `status` is `done`, `interrupted` (the fork head still has
`next`) or `error` (with the exception text; the partial fork stays visible). The run uses
`recursion_limit` 100.

## What I gave up
- Live progress for long forks. A fork that calls a slow real model blocks the request until done.
- SSE is the first v0.2 item; the event shape is kept so SSE can reuse it.
