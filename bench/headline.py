"""Build the README headline from bench/results/*.json, or check that README.md contains it.

uv run python bench/headline.py               prints the headline and the numbers table
uv run python bench/headline.py --check README.md   exits 1 if README.md lacks the headline
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"


def load(name: str) -> dict | None:
    p = RESULTS / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def headline() -> str:
    api, ui = load("api.json"), load("ui.json")
    if api is None:
        raise SystemExit("bench/results/api.json is missing; run: uv run python bench/bench.py")
    if not api["source_unchanged"]:
        raise SystemExit("the source changed during the benchmark; fix that before publishing any number")
    n = f"{api['checkpoints']:,}"
    if ui is not None:
        opens = f"opens a {n}-checkpoint LangGraph thread in {ui['open_warm_median_ms']:g} ms"
        steps = f"steps between checkpoints in {ui['step_median_ms']:g} ms"
    else:
        opens = f"lists a {n}-checkpoint LangGraph thread in {api['index_warm_p50_ms']:g} ms"
        steps = f"loads a checkpoint's state in {api['state_p50_ms']:g} ms"
    return f"**flight-recorder {opens}, {steps}, and forks any step without changing a byte of the original.**"


def main(argv: list[str]) -> int:
    line = headline()
    if len(argv) == 2 and argv[0] == "--check":
        text = Path(argv[1]).read_text(encoding="utf-8")
        if line not in text:
            print(f"README is missing the measured headline:\n{line}", file=sys.stderr)
            return 1
        print("README headline matches bench/results")
        return 0
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
