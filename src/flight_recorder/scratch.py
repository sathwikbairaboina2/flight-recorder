"""The scratch database where forks live: SqliteSaver tables plus fr_forks provenance (ADR 0005)."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

_FORKS_DDL = """
CREATE TABLE IF NOT EXISTS fr_forks (
  fork_id TEXT PRIMARY KEY,
  source_db_sha256 TEXT NOT NULL,
  source_thread_id TEXT NOT NULL,
  source_checkpoint_id TEXT NOT NULL,
  scratch_thread_id TEXT NOT NULL UNIQUE,
  as_node TEXT,
  values_json TEXT NOT NULL,
  created_at TEXT NOT NULL
)
"""


class ScratchStore:
    """The scratch SQLite database: SqliteSaver tables plus fr_forks."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.saver = SqliteSaver(self.conn)
        self.saver.setup()
        self.conn.execute(_FORKS_DDL)
        self.conn.commit()

    def forks(self) -> list[dict]:
        cols = ["fork_id", "source_thread_id", "source_checkpoint_id", "scratch_thread_id", "as_node", "created_at"]
        with self.lock:
            rows = self.conn.execute(f"SELECT {', '.join(cols)} FROM fr_forks ORDER BY created_at").fetchall()
        return [dict(zip(cols, r, strict=True)) for r in rows]

    def thread_ids(self) -> set[str]:
        return {f["scratch_thread_id"] for f in self.forks()}

    def close(self) -> None:
        self.conn.close()
