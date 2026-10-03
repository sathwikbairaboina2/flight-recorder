import { describe, expect, it } from 'vitest'
import { formatBytes, relativeTime, shortId } from './format'

describe('format', () => {
  it('formats bytes', () => {
    expect(formatBytes(812)).toBe('812 B')
    expect(formatBytes(18_634)).toBe('18.2 KB')
    expect(formatBytes(1_468_006)).toBe('1.4 MB')
  })
  it('formats time since the first checkpoint', () => {
    expect(relativeTime('2026-10-04T10:00:00.000Z', '2026-10-04T10:00:00.000Z')).toBe('+0 ms')
    expect(relativeTime('2026-10-04T10:00:00.250Z', '2026-10-04T10:00:00.000Z')).toBe('+250 ms')
    expect(relativeTime('2026-10-04T10:00:03.400Z', '2026-10-04T10:00:00.000Z')).toBe('+3.4 s')
    expect(relativeTime('2026-10-04T10:02:05.000Z', '2026-10-04T10:00:00.000Z')).toBe('+2m 5s')
  })
  it('shortens checkpoint ids to their last 8 characters', () => {
    expect(shortId('1f1bf756-229e-6563-8003-d41065ca3b5a')).toBe('65ca3b5a')
  })
})
