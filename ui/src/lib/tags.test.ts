import { describe, expect, it } from 'vitest'
import { isMessage, orderChannels, tagOf, typeName } from './tags'

describe('tags', () => {
  it('finds the tag of a bridged value', () => {
    expect(tagOf({ __lc_message__: 'ai', id: 'x', content: '' })).toBe('__lc_message__')
    expect(tagOf({ __uuid__: 'u' })).toBe('__uuid__')
    expect(tagOf({ plain: 1 })).toBeNull()
    expect(tagOf([1])).toBeNull()
    expect(tagOf('s')).toBeNull()
  })
  it('detects messages', () => {
    expect(isMessage({ __lc_message__: 'human', id: 'h', content: 'hi' })).toBe(true)
    expect(isMessage({ id: 'h' })).toBe(false)
  })
  it('shortens dotted type names', () => {
    expect(typeName('flight_recorder.samples.SearchQuery')).toBe('SearchQuery')
  })
  it('orders channels messages first and splits off internal ones', () => {
    expect(orderChannels({ results: [], 'branch:to:tools': null, query: 1, messages: [], __start__: null })).toEqual({
      user: ['messages', 'query', 'results'],
      internal: ['__start__', 'branch:to:tools'],
    })
  })
})
