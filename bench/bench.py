"""API benchmark on a generated 10,000-checkpoint thread. Writes bench/results/api.json.

Starts the real server on 127.0.0.1:5323, measures with httpx, stops it, and checks the source
directory is byte-identical afterwards. Run: uv run python bench/bench.py
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

import httpx

from flight_recorder.samples import make_sample_db

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".bench" / "api"
OUT = ROOT / "bench" / "results" / "api.json"
PORT = 5323
BASE = f"http://127.0.0.1:{PORT}"
N = 10_000


def fingerprint(folder: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, round(q * (len(xs) - 1)))], 1)


def timed(client: httpx.Client, method: str, url: str, **kw) -> tuple[float, httpx.Response]:
    t0 = time.perf_counter()
    r = client.request(method, url, **kw)
    ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return ms, r


def main() -> None:
    t0 = time.perf_counter()
    db = make_sample_db(WORK / "checkpoints.sqlite", long_checkpoints=N)
    gen_s = round(time.perf_counter() - t0, 1)
    before = fingerprint(db.parent)
    cmd = [sys.executable, "-m", "flight_recorder", "serve", "--db", str(db), "--graph",
           "flight_recorder.samples:graph", "--port", str(PORT), "--no-browser"]  # fmt: skip
    server = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url=BASE, timeout=60) as c:
            for _ in range(100):
                try:
                    if c.get("/api/health").status_code == 200:
                        break
                except httpx.TransportError:
                    time.sleep(0.2)
            tid = f"long-{N}"
            cold_ms, r = timed(c, "GET", f"/api/threads/{tid}/checkpoints")
            rows = r.json()
            assert len(rows) == N, len(rows)
            payload_kb = round(len(r.content) / 1024, 1)
            warm = [timed(c, "GET", f"/api/threads/{tid}/checkpoints")[0] for _ in range(20)]
            picks = [rows[i]["checkpoint_id"] for i in range(0, N, N // 50)]
            state = [timed(c, "GET", f"/api/threads/{tid}/checkpoints/{cid}")[0] for cid in picks]
            bug = c.get("/api/threads/lisbon-bug/checkpoints").json()
            plan = next(x for x in bug if x["writes_from"] == ["plan"])
            values = c.get(f"/api/threads/lisbon-bug/checkpoints/{plan['checkpoint_id']}").json()["values"]
            values["messages"][-1]["tool_calls"][0]["args"]["depart_after"] = "2026-11-01"
            body = {"thread_id": "lisbon-bug", "checkpoint_id": plan["checkpoint_id"],
                    "values": {"messages": values["messages"]}, "as_node": "plan"}  # fmt: skip
            fork_client, fork_server, answers = [], [], set()
            for _ in range(5):
                ms, fr = timed(c, "POST", "/api/forks", json=body)
                res = fr.json()
                fork_client.append(ms)
                fork_server.append(res["elapsed_ms"])
                answers.add(res["events"][-1]["update"]["messages"][0]["content"])
    finally:
        server.terminate()
        server.wait(timeout=30)
    after = fingerprint(db.parent)
    result = {
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "cpu_count": os.cpu_count(),
            "python": platform.python_version(),
            "langgraph": version("langgraph"),
        },
        "checkpoints": N,
        "fixture_generation_s": gen_s,
        "source_db_mb": round(db.stat().st_size / 1e6, 1),
        "index_cold_ms": round(cold_ms, 1),
        "index_warm_p50_ms": pct(warm, 0.5),
        "index_warm_p95_ms": pct(warm, 0.95),
        "index_payload_kb": payload_kb,
        "state_p50_ms": pct(state, 0.5),
        "state_p95_ms": pct(state, 0.95),
        "fork_roundtrip_p50_ms": pct(fork_client, 0.5),
        "fork_server_p50_ms": pct(fork_server, 0.5),
        "fork_answers": sorted(answers),
        "forks_run": len(fork_client),
        "source_files_before": sorted(before),
        "source_files_after": sorted(after),
        "source_unchanged": before == after,
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
