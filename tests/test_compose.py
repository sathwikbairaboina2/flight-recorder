"""Invariant 7 for Docker: every published port is bound to the host loopback."""

import re
from pathlib import Path

COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yml"


def published_ports(text: str) -> list[str]:
    ports, in_ports = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ports:"):
            in_ports = True
            continue
        if in_ports and stripped.startswith("- "):
            ports.append(stripped[2:].strip().strip("\"'"))
        elif in_ports and stripped:
            in_ports = False
    return ports


def test_compose_ports_loopback_only():
    ports = published_ports(COMPOSE.read_text(encoding="utf-8"))
    assert ports, "expected at least one published port"
    for p in ports:
        assert p.startswith("127.0.0.1:"), f"port {p!r} is not bound to 127.0.0.1"


def test_names_are_prefixed():
    text = COMPOSE.read_text(encoding="utf-8")
    assert re.search(r"^name: flight-recorder$", text, re.M)
    assert "container_name: flight-recorder-demo" in text


def test_parser_catches_a_public_port():
    assert published_ports('services:\n  a:\n    ports:\n      - "5324:5320"\n') == ["5324:5320"]
