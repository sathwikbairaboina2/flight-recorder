# ADR-0007: Loopback only, and default port 5320

- Status: accepted (2026-10-04)

## Decision
- The server binds `127.0.0.1`. `--host` with any other value exits with code 2 unless
  `--i-know-this-is-unauthenticated` is also passed (needed inside Docker, where compose publishes
  the port only on the host loopback).
- Default port is 5320 (the build session owns 5320 to 5329; see the spec's port table). `--port`
  changes it.
- `tests/test_compose.py` parses `docker-compose.yml` and fails on any published port that does not
  start with `127.0.0.1:`.

## What I gave up
- No auth, so no remote or shared use. Anyone with a shell on the machine can reach the port.
- 5320 is not a memorable or conventional port; it was chosen to fit the build environment.
