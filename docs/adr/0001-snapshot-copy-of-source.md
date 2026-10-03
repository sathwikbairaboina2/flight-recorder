# ADR-0001: Read a private copy of the source database, never the file itself

- Status: accepted (2026-10-04)

## Context
The core promise is that the user's checkpoint file is never modified. The design doc opened the source
with a SQLite URI in `mode=ro`. A prototype on 2026-10-04 (LangGraph 1.2.12, Windows 11) showed that a
`mode=ro` open of a WAL-mode database (SqliteSaver always sets WAL) creates `checkpoints.sqlite-wal`
and `checkpoints.sqlite-shm` next to the source. The main file hash stays the same, but the directory
changes, and a read-only reader can interfere with a writer's WAL checkpoint.

## Decision
- `snapshot.py` copies `<db>` and, if present, `<db>-wal` into a private temp dir with plain file
  reads (`shutil.copyfile`). SQLite only ever opens the copy. `-shm` is never copied; SQLite rebuilds
  the WAL index from the copied `-wal`.
- Before serving `/api/threads` the snapshot compares `(size, mtime_ns)` of the source db and wal with
  the values at copy time and re-copies on change. That makes "watch a running agent" work by refresh.
- `tests/test_immutability.py` hashes every file in the source directory and the file list before and
  after reading every checkpoint and running 5 forks, including a case where a live writer holds an
  un-checkpointed `-wal`. The prototype of that case passed on Windows.

## What I gave up
- Time and disk on huge files: a 37.5 MB database copied in about 34 ms in the prototype, but a
  multi-GB file will be slow. No size limit or incremental copy in v0.1.
- A torn read is possible if a writer commits while we copy. The copy is retried once if the source
  stat changed during the copy; after that the user sees the slightly older snapshot.
- `immutable=1` would avoid the copy but silently ignores a live `-wal`, so it hides recent steps.
