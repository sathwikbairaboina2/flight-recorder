import sqlite3

import pytest
from conftest import dir_fingerprint

from flight_recorder.snapshot import Snapshot


def test_copy_is_readable_and_separate(sample_db):
    snap = Snapshot(sample_db)
    try:
        assert snap.path != sample_db
        assert snap.path.parent != sample_db.parent
        with sqlite3.connect(snap.path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0] == 12
    finally:
        snap.close()


def test_opening_and_reading_leaves_source_dir_untouched(sample_db):
    before = dir_fingerprint(sample_db.parent)
    snap = Snapshot(sample_db)
    with sqlite3.connect(snap.path) as conn:
        conn.execute("SELECT * FROM checkpoints").fetchall()
    snap.refresh()
    snap.close()
    assert dir_fingerprint(sample_db.parent) == before


def test_refresh_only_when_source_changes(sample_db):
    snap = Snapshot(sample_db)
    try:
        assert snap.refresh() is False
        with sqlite3.connect(sample_db) as conn:  # the user's agent writes more
            conn.execute("DELETE FROM checkpoints WHERE thread_id = 'lisbon-bug'")
        assert snap.refresh() is True
        assert snap.generation == 1
        with sqlite3.connect(snap.path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0] == 7
    finally:
        snap.close()


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        Snapshot(tmp_path / "nope.sqlite")


def test_source_sha256_is_stable(sample_db):
    snap = Snapshot(sample_db)
    try:
        assert snap.source_sha256() == snap.source_sha256()
        assert len(snap.source_sha256()) == 64
    finally:
        snap.close()


def test_refresh_keeps_at_most_two_generations(sample_db):
    snap = Snapshot(sample_db)
    try:
        for i in range(5):
            with sqlite3.connect(sample_db) as conn:
                conn.execute("INSERT INTO writes SELECT * FROM writes LIMIT 0")
                conn.execute("UPDATE checkpoints SET metadata = metadata WHERE rowid = ?", (i + 1,))
                conn.execute("CREATE TABLE IF NOT EXISTS bump (n)")
                conn.execute("INSERT INTO bump VALUES (?)", (i,))
            assert snap.refresh() is True
        gens = [p.name for p in snap._dir.iterdir() if p.name.startswith("gen")]
        assert len(gens) <= 2
        assert snap.path.parent.name == "gen5"
        with sqlite3.connect(snap.path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM bump").fetchone()[0] == 5
    finally:
        snap.close()
