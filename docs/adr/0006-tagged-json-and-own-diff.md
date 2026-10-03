# ADR-0006: One tagged JSON format and an own structural diff keyed by message id

- Status: accepted (2026-10-04)

## Decision
- The API sends state as JSON with reserved `__tag__` keys (spec table). Messages become
  `{"__lc_message__": "<type>", "id": ..., ...}` so every message carries a string `id`.
- `ui/src/lib/diff.ts` is a pure function. Objects diff by key. Arrays whose elements are all objects
  with a unique string `id` diff by id (`remove`, `add`, nested ops at `{id}` paths, then `move` ops
  that fix the order left to right). Other arrays diff by index. `apply` replays ops in order.
- fast-check proves `diff(a, a) = []` and `apply(a, diff(a, b)) = b` over random JSON and random
  keyed lists.

## What I gave up
- jsondiffpatch: mature, but its array heuristics do not know message ids, and its delta format is
  harder to render as a list of changes.
- Minimal move sets. Left-to-right fixing can emit more moves than a longest-increasing-subsequence
  algorithm. Fine for message lists of hundreds.
- Line-level diff of long strings (display only) is v0.2.
