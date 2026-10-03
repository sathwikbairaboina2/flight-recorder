"""Private copy of the source database so SQLite never opens the user's file (ADR 0001)."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import threading
from pathlib import Path


def _stat(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    return (st.st_size, st.st_mtime_ns)


class Snapshot:
    def __init__(self, source: str | os.PathLike[str]) -> None:
        self.source = Path(source).resolve()
        if not self.source.is_file():
            raise FileNotFoundError(f"no such database: {self.source}")
        self._wal = self.source.with_name(self.source.name + "-wal")
        self._dir = Path(tempfile.mkdtemp(prefix="flight-recorder-snap-"))
        self._lock = threading.Lock()
        self.generation = 0
        self._stamp: tuple | None = None
        self.path = self._dir / "gen0" / self.source.name
        self._copy()

    def _current_stamp(self) -> tuple:
        return (_stat(self.source), _stat(self._wal))

    def _copy(self) -> None:
        for _attempt in range(2):
            stamp = self._current_stamp()
            target_dir = self._dir / f"gen{self.generation}"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / self.source.name
            shutil.copyfile(self.source, target)
            if stamp[1] is not None:
                shutil.copyfile(self._wal, target_dir / self._wal.name)
            if self._current_stamp() == stamp:
                break
        self._stamp = stamp
        self.path = target

    def refresh(self) -> bool:
        """Re-copy if the source changed since the last copy. Returns True when a new copy was made."""
        with self._lock:
            if self._current_stamp() == self._stamp:
                return False
            self.generation += 1
            self._copy()
            return True

    def source_sha256(self) -> str:
        h = hashlib.sha256()
        with open(self.source, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def close(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)
