import { describe, expect, it } from 'vitest'
import { apply, diff, formatPath, isKeyed, type Json } from './diff'

const msgs = (ids: string[]): Json => ids.map((id) => ({ id, content: id.toUpperCase() }))

describe('diff', () => {
  it('is empty for equal values, whatever the key order', () => {
    expect(diff({ a: 1, b: [1, { c: 2 }] }, { b: [1, { c: 2 }], a: 1 })).toEqual([])
  })

  it('adds, removes and replaces object keys', () => {
    expect(diff({ a: 1, b: 2 }, { b: 3, c: 4 })).toEqual([
      { op: 'remove', path: ['a'], value: 1 },
      { op: 'replace', path: ['b'], before: 2, after: 3 },
      { op: 'add', path: ['c'], value: 4 },
    ])
  })

  it('addresses messages by id, which is how the date bug shows up', () => {
    const before: Json = { messages: [{ id: 'h', content: 'hi' }, { id: 'ai-plan', tool_calls: [{ args: { depart_after: null } }] }] }
    const after: Json = { messages: [{ id: 'h', content: 'hi' }, { id: 'ai-plan', tool_calls: [{ args: { depart_after: '2026-11-01' } }] }] }
    const ops = diff(before, after)
    expect(ops).toEqual([
      { op: 'replace', path: ['messages', { id: 'ai-plan' }, 'tool_calls', 0, 'args', 'depart_after'], before: null, after: '2026-11-01' },
    ])
    expect(formatPath((ops[0] as { path: (string | number | { id: string })[] }).path)).toBe(
      'messages[id=ai-plan].tool_calls[0].args.depart_after',
    )
  })

  it('reports a reordered keyed list as moves only', () => {
    const ops = diff(msgs(['a', 'b', 'c', 'd']), msgs(['c', 'a', 'd', 'b']))
    expect(ops.length).toBeGreaterThan(0)
    expect(ops.every((o) => o.op === 'move')).toBe(true)
    expect(apply(msgs(['a', 'b', 'c', 'd']), ops)).toEqual(msgs(['c', 'a', 'd', 'b']))
  })

  it('inserts into a keyed list at the final index', () => {
    const ops = diff(msgs(['a', 'c']), msgs(['a', 'b', 'c']))
    expect(ops).toEqual([{ op: 'add', path: [1], value: { id: 'b', content: 'B' } }])
  })

  it('diffs plain arrays by index', () => {
    expect(diff([1, 2, 3], [1, 9])).toEqual([
      { op: 'replace', path: [1], before: 2, after: 9 },
      { op: 'remove', path: [2], value: 3 },
    ])
    expect(apply([1, 2, 3], diff([1, 2, 3], [1, 9, 3, 4]))).toEqual([1, 9, 3, 4])
  })

  it('replaces at the root when types differ', () => {
    expect(diff([1], { a: 1 })).toEqual([{ op: 'replace', path: [], before: [1], after: { a: 1 } }])
  })

  it('treats duplicate or missing ids as an indexed list', () => {
    expect(isKeyed([{ id: 'a' }, { id: 'a' }])).toBe(false)
    expect(isKeyed([{ id: 'a' }, { x: 1 }])).toBe(false)
    expect(isKeyed([])).toBe(false)
    expect(isKeyed([{ id: 'a' }, { id: 'b' }])).toBe(true)
  })

  it('formats the root path', () => {
    expect(formatPath([])).toBe('(root)')
  })

  it('does not mutate its inputs', () => {
    const a: Json = { m: msgs(['a', 'b']) }
    const copy = structuredClone(a)
    apply(a, diff(a, { m: msgs(['b', 'a']) }))
    expect(a).toEqual(copy)
  })
})
