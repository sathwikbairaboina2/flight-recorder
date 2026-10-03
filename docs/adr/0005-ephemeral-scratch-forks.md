# ADR-0005: Forks copy only the ancestor chain into an ephemeral scratch database

- Status: accepted (2026-10-04)

## Decision
- The scratch database is the `SqliteSaver` tables plus `fr_forks` (provenance: source SHA-256, source
  thread and checkpoint, `as_node`, edited values, time).
- Each fork gets thread id `fork:<uuid4 hex>`. If that equals a source thread id it is regenerated.
- Only the chain from the root to the chosen checkpoint is copied, oldest first, with each
  checkpoint's pending writes. Checkpoint ids and parent links are kept, so the UI can show which
  steps are shared with the source. Copying used `SqliteSaver.put` and `put_writes` in the prototype
  and kept parent links equal.
- The graph is recompiled with `compiled.builder.compile(checkpointer=scratch)` (or
  `builder.compile(...)` when the user points at an uncompiled `StateGraph`).
- Default scratch path: a fresh temp dir deleted at exit. `--scratch PATH` keeps forks across runs.

## What I gave up
- Forks are lost on exit by default. The design doc proposed keeping them; for a debugger a clean
  slate is the safer default and the flag covers the other case.
- Compile options set on the user's compiled graph (for example `interrupt_before`) are not carried
  over by `builder.compile`. Documented as a known limit.
- Subgraph namespaces cannot be forked in v0.1.
