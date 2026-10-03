# ADR-0002: The read path decodes checkpoints without importing anything

- Status: accepted (2026-10-04)

## Context
LangGraph's `JsonPlusSerializer` stores custom values as msgpack extensions holding
`(module, class, payload, ...)`. On load it imports `module` and calls the class. Prototyped on
langgraph-checkpoint 4.2.0:
- A pydantic model from a module that is not importable comes back as a plain dict (type lost).
- A dataclass from a module that is not importable comes back as `None` (value silently dropped).
- Importing modules named inside a file is code execution when the file is untrusted, for example a
  checkpoint attached to a bug report.

## Decision
- `decode.SafeSerializer` is `JsonPlusSerializer(__unpack_ext_hook__=safe_ext_hook)`. The hook decodes
  every extension code (0 to 5 carry `(module, name, payload[, method])`, 6 numpy, 7 delta snapshot)
  into a frozen `Ext(kind, type, data, method)` record and never imports.
- `bridge.to_json` maps `Ext` records to the type-tagged JSON in the spec. Unknown kinds become
  `__unrepresentable__` with a repr, never `None`.
- The fork path, which must run user code anyway, uses LangGraph's normal serializer. Fork events are
  converted with `real.dumps_typed` then `safe.loads_typed`, so the UI sees one format.
- `tests/test_decode.py::test_reading_never_imports` proves it with a canary module.

## What I gave up
- The hook depends on LangGraph's extension code numbers, which are module constants, not a public
  API. They are imported by name from `langgraph.checkpoint.serde.jsonplus`, so a rename fails loudly
  at import, and `flight-recorder doctor` prints the installed `langgraph-checkpoint` version.
- Custom `__repr__` or computed properties of user classes are not shown; only stored fields.
