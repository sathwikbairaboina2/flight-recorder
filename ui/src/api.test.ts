import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from './api'

function stubFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } }))
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('builds encoded urls', async () => {
    const fn = stubFetch(200, [])
    await api.checkpoints('fork:abc', '')
    expect(fn).toHaveBeenCalledWith('/api/threads/fork%3Aabc/checkpoints?ns=', undefined)
  })

  it('posts forks as json', async () => {
    const fn = stubFetch(200, { status: 'done' })
    await api.fork({ thread_id: 't', checkpoint_id: 'c', values: { a: 1 }, as_node: 'plan' })
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/forks')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ thread_id: 't', checkpoint_id: 'c', values: { a: 1 }, as_node: 'plan' })
  })

  it('turns error responses into ApiError with the server detail', async () => {
    stubFetch(404, { detail: 'thread nope has no checkpoints' })
    await expect(api.threads()).rejects.toMatchObject({ status: 404, message: 'thread nope has no checkpoints' })
    await expect(api.threads()).rejects.toBeInstanceOf(ApiError)
  })
})
