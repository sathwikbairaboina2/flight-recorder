import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import { apply, deepEqual, diff, type Json } from './diff'

const msg = fc.record({
  id: fc.constantFrom('a', 'b', 'c', 'd', 'e', 'f'),
  content: fc.string({ maxLength: 4 }),
  n: fc.integer({ min: 0, max: 3 }),
})
const msgs = fc.uniqueArray(msg, { selector: (m) => m.id, maxLength: 6 })
const tree = fc.letrec((tie) => ({
  node: fc.oneof(
    { depthSize: 'small' },
    fc.jsonValue({ maxDepth: 2 }),
    msgs,
    fc.dictionary(fc.string({ maxLength: 3 }), tie('node'), { maxKeys: 4 }),
    fc.array(tie('node'), { maxLength: 4 }),
  ),
})).node

describe('diff properties', () => {
  it('diff(a, a) is empty and apply(a, diff(a, b)) equals b', () => {
    fc.assert(
      fc.property(tree, tree, (a, b) => {
        expect(diff(a as Json, a as Json)).toEqual([])
        expect(deepEqual(apply(a as Json, diff(a as Json, b as Json)), b as Json)).toBe(true)
      }),
      { numRuns: 500 },
    )
  })

  it('a permutation of a keyed list is moves only', () => {
    fc.assert(
      fc.property(msgs, fc.integer(), (m, seed) => {
        const shuffled = [...m].sort((x, y) => ((x.id.charCodeAt(0) * 31 + seed) % 7) - ((y.id.charCodeAt(0) * 31 + seed) % 7))
        const ops = diff(m as Json, shuffled as Json)
        expect(ops.every((o) => o.op === 'move')).toBe(true)
        expect(deepEqual(apply(m as Json, ops), shuffled as Json)).toBe(true)
      }),
      { numRuns: 500 },
    )
  })
})
