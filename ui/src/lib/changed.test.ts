import { describe, expect, it } from 'vitest'
import { changedTopLevel } from './changed'

describe('changedTopLevel', () => {
  it('keeps only top-level channels that changed or are new', () => {
    const before = { messages: [{ id: 'a', content: 'x' }], count: 1, results: [] }
    const after = { messages: [{ id: 'a', content: 'y' }], count: 1, results: [], extra: true }
    expect(changedTopLevel(before, after)).toEqual({ messages: [{ id: 'a', content: 'y' }], extra: true })
  })

  it('ignores key order and removed keys', () => {
    expect(changedTopLevel({ a: { x: 1, y: 2 }, gone: 1 }, { a: { y: 2, x: 1 } })).toEqual({})
  })
})
