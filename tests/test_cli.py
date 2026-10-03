"""Invariant 7 (local only) and the doctor command."""

import json
import sqlite3

import pytest

from flight_recorder.cli import DEFAULT_PORT, UsageError, build_parser, check_host, main


def test_defaults_are_loopback_and_5320():
    args = build_parser().parse_args(["serve", "--db", "x.sqlite"])
    assert args.host == "127.0.0.1"
    assert args.port == DEFAULT_PORT == 5320


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_hosts_are_allowed(host):
    check_host(host, acknowledged=False)


def test_public_host_needs_the_flag():
    with pytest.raises(UsageError):
        check_host("0.0.0.0", acknowledged=False)
    check_host("0.0.0.0", acknowledged=True)


def test_serve_refuses_public_host(sample_db, capsys):
    assert main(["serve", "--db", str(sample_db), "--host", "0.0.0.0", "--no-browser"]) == 2
    assert "--i-know-this-is-unauthenticated" in capsys.readouterr().err


def test_doctor(sample_db, capsys):
    assert main(["doctor", "--db", str(sample_db)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == "ok"
    assert report["threads"] == 2
    assert report["checkpoints_read"] == 12
    assert report["unrepresentable_values"] == 0
    assert report["langgraph"].startswith("1.")


def test_doctor_on_foreign_db(tmp_path, capsys):
    db = tmp_path / "x.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE t (a)")
    assert main(["doctor", "--db", str(db)]) == 1
    assert "missing columns" in capsys.readouterr().err


def test_missing_db(tmp_path, capsys):
    assert main(["doctor", "--db", str(tmp_path / "nope.sqlite")]) == 1


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "flight-recorder 0.1.0" in capsys.readouterr().out
