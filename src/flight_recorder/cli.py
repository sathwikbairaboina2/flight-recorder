"""`flight-recorder` command line: serve, demo, doctor (ADR 0007 for the host rules)."""

from __future__ import annotations

import argparse
import atexit
import json
import shutil
import sys
import tempfile
import threading
import webbrowser
from collections.abc import Sequence
from importlib.metadata import version as dist_version
from pathlib import Path
from typing import Any

from . import __version__

DEFAULT_PORT = 5320
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
STATIC_DIR = Path(__file__).parent / "static"
SAMPLE_GRAPH = "flight_recorder.samples:graph"


class UsageError(Exception):
    pass


def check_host(host: str, acknowledged: bool) -> None:
    if host not in LOOPBACK and not acknowledged:
        raise UsageError(
            f"refusing to bind {host}: the server has no auth. "
            "Pass --i-know-this-is-unauthenticated if you really mean it (for example inside Docker)."
        )


def _add_server_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--i-know-this-is-unauthenticated", dest="ack", action="store_true")
    p.add_argument("--scratch", help="keep forks in this SQLite file (default: a temp file removed at exit)")
    p.add_argument("--no-browser", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flight-recorder", description="Time-travel debugger for LangGraph")
    parser.add_argument("--version", action="version", version=f"flight-recorder {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="open a checkpoint database")
    serve.add_argument("--db", required=True)
    serve.add_argument("--graph", help="module:attr of your StateGraph, needed for forks")
    _add_server_args(serve)
    demo = sub.add_parser("demo", help="write the sample database and serve it")
    demo.add_argument("--dir", help="where to write checkpoints.sqlite (default: a temp dir)")
    demo.add_argument("--long", type=int, default=0, help="also write a long-<N> thread with N checkpoints")
    _add_server_args(demo)
    doctor = sub.add_parser("doctor", help="check a database and print what the reader sees")
    doctor.add_argument("--db", required=True)
    return parser


def build_app(db: str, graph: str | None, scratch: str | None) -> tuple[Any, list]:
    """Create the FastAPI app. Returns (app, closers)."""
    from .api import create_app
    from .fork import ForkEngine
    from .graph_loader import fork_serde, load_builder, topology
    from .reader import Reader
    from .scratch import ScratchStore
    from .snapshot import Snapshot

    snapshot = Snapshot(db)
    closers: list = [snapshot.close]
    store = engine = topo = None
    if graph:
        builder = load_builder(graph)
        if scratch:
            scratch_path = Path(scratch)
        else:
            tmp = Path(tempfile.mkdtemp(prefix="flight-recorder-scratch-"))
            scratch_path = tmp / "scratch.sqlite"
            closers.append(lambda: shutil.rmtree(tmp, ignore_errors=True))
        store = ScratchStore(scratch_path, serde=fork_serde(builder))
        closers.insert(0, store.close)
        engine = ForkEngine(builder, store, snapshot.source_sha256())
        topo = topology(builder)
    reader = Reader(snapshot, store)
    if not (STATIC_DIR / "index.html").is_file():
        print(
            f"warning: no UI at {STATIC_DIR}; serving the API only. Run `pnpm -C ui build` before packaging.",
            file=sys.stderr,
        )
    return create_app(reader, engine, topo, STATIC_DIR), closers


def _serve(args: argparse.Namespace, db: str, graph: str | None) -> int:
    import uvicorn

    check_host(args.host, args.ack)
    app, closers = build_app(db, graph, args.scratch)
    for close in closers:
        atexit.register(close)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"flight-recorder {__version__} serving {db} at {url}", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def doctor(db: str) -> dict:
    from .reader import Reader
    from .snapshot import Snapshot

    snapshot = Snapshot(db)
    try:
        reader = Reader(snapshot)  # raises SchemaError (a RuntimeError) on a foreign database
        threads = reader.threads()
        states = unrepresentable = 0
        for t in threads:
            for row in reader.checkpoints(t["thread_id"]):
                st = reader.state(t["thread_id"], row["checkpoint_id"])
                states += 1
                unrepresentable += json.dumps(st["values"]).count('"__unrepresentable__"')
        return {
            "flight_recorder": __version__,
            "langgraph": dist_version("langgraph"),
            "langgraph_checkpoint": dist_version("langgraph-checkpoint"),
            "langgraph_checkpoint_sqlite": dist_version("langgraph-checkpoint-sqlite"),
            "schema": "ok",
            "threads": len(threads),
            "checkpoints_read": states,
            "unrepresentable_values": unrepresentable,
        }
    finally:
        snapshot.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            return _serve(args, args.db, args.graph)
        if args.command == "demo":
            from .samples import make_sample_db

            folder = Path(args.dir) if args.dir else Path(tempfile.mkdtemp(prefix="flight-recorder-demo-"))
            db = make_sample_db(folder / "checkpoints.sqlite", long_checkpoints=args.long)
            return _serve(args, str(db), SAMPLE_GRAPH)
        if args.command == "doctor":
            print(json.dumps(doctor(args.db), indent=2))
            return 0
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


def main_entry() -> None:
    sys.exit(main())
