import { describe, expect, it } from 'vitest'
import { computeLanes, laneCount } from './lanes'

const row = (checkpoint_id: string, parent_id: string | null) => ({ checkpoint_id, parent_id })

describe('computeLanes', () => {
  it('puts a linear thread on lane 0', () => {
    const lanes = computeLanes([row('a', null), row('b', 'a'), row('c', 'b')])
    expect([...lanes.values()].every((l) => l.lane === 0 && l.branchFrom === null)).toBe(true)
    expect(laneCount(lanes)).toBe(1)
  })

  it('gives the newest leaf lane 0 and an older branch lane 1', () => {
    // a-b-c-d is the first run; c-e-f is an update_state branch made later (ids sort by time)
    const lanes = computeLanes([row('a', null), row('b', 'a'), row('c', 'b'), row('d', 'c'), row('e', 'c'), row('f', 'e')])
    expect(lanes.get('f')).toEqual({ lane: 0, branchFrom: null })
    expect(lanes.get('e')).toEqual({ lane: 0, branchFrom: null })
    expect(lanes.get('d')).toEqual({ lane: 1, branchFrom: 'c' })
    expect(laneCount(lanes)).toBe(2)
  })

  it('treats a missing parent as a root', () => {
    expect(computeLanes([row('x', 'gone')]).get('x')).toEqual({ lane: 0, branchFrom: null })
  })
})
