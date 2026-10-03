// Diff two ~1 MB states 30 times; writes ../bench/results/diff.json. Run: pnpm bench:diff
import { writeFileSync, mkdirSync } from 'node:fs'
import os from 'node:os'
import { diff, type Json } from '../src/lib/diff.ts'

function state(n: number, edit: boolean): Json {
  const messages = Array.from({ length: n }, (_, i) => ({
    __lc_message__: i % 2 ? 'ai' : 'human',
    id: `m-${i}`,
    content: `${edit && i % 100 === 7 ? 'EDITED ' : ''}${'lorem ipsum dolor sit amet '.repeat(16)}${i}`,
    tool_calls: i % 2 ? [{ name: 'search', args: { q: `q${i}`, page: i % 5 }, id: `c-${i}` }] : [],
  }))
  if (edit) {
    messages.splice(10, 0, { __lc_message__: 'ai', id: 'new-1', content: 'inserted', tool_calls: [] })
    ;[messages[20], messages[21]] = [messages[21], messages[20]]
  }
  return { messages, count: n }
}

const a = state(2000, false)
const b = state(2000, true)
const bytes = JSON.stringify(a).length
const times: number[] = []
let ops = 0
for (let i = 0; i < 35; i++) {
  const t0 = performance.now()
  ops = diff(a, b).length
  const ms = performance.now() - t0
  if (i >= 5) times.push(ms) // first 5 are JIT warm-up
}
times.sort((x, y) => x - y)
const pick = (q: number) => Math.round(times[Math.min(times.length - 1, Math.round(q * (times.length - 1)))] * 10) / 10
const result = {
  machine: { platform: `${os.type()} ${os.release()}`, cpu: os.cpus()[0]?.model ?? 'unknown', node: process.version },
  state_bytes: bytes,
  ops,
  runs: times.length,
  diff_p50_ms: pick(0.5),
  diff_p95_ms: pick(0.95),
}
mkdirSync('../bench/results', { recursive: true })
writeFileSync('../bench/results/diff.json', JSON.stringify(result, null, 2) + '\n')
console.log(result)
