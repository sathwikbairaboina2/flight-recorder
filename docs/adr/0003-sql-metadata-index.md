# ADR-0003: The checkpoint index reads the SqliteSaver table with SQL

- Status: accepted (2026-10-04)

## Context
The design doc said "use the checkpointer API, not raw SQL". The API has no metadata-only listing.
`SqliteSaver.list()` fully deserializes every checkpoint and runs one `writes` query per row. On a
generated 10,000-checkpoint thread (37.5 MB) it took 3.6 s in the prototype. One SQL query for ids,
parent id, metadata JSON and the blob, plus a shallow msgpack decode of each blob for
`updated_channels`, took about 0.3 s warm.

## Decision
- `index.py` queries `checkpoints(thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type,
  checkpoint, metadata)` directly. It decodes each blob with `ormsgpack.unpackb` and an ext hook that
  returns `None`, only to read `updated_channels`. `state_bytes` is `length(checkpoint)`.
- `index.check_schema(conn)` verifies those columns and the `writes` table exist. If not, `doctor` and
  `serve` fail with a message naming the columns found.
- Full state for one checkpoint still uses `SqliteSaver.get_tuple` with the safe serializer, so values
  and pending writes follow LangGraph's own decoding rules.
- `created_at` is decoded from the uuid6 `checkpoint_id` (within 0.6 ms of `checkpoint["ts"]` in the
  prototype; LangGraph reads the two from separate clock calls), so time needs no full decode.
- `next` and `writes_from` are derived from `updated_channels`, `channel_versions` and `versions_seen`
  (rules in the spec). In the prototype they matched `get_state_history` for every checkpoint of the
  sample threads, an `update_state` branch and a fork.

## What I gave up
- Coupling to the SqliteSaver table layout. A schema change in langgraph-checkpoint-sqlite breaks the
  index until updated; `check_schema` turns that into a clear error instead of wrong data.
- Postgres support needs a second index implementation (v0.2 or later).
