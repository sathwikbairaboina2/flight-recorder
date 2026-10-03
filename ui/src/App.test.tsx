import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import fixture from './test/fixtures/lisbon.json'
import { App } from './App'

type Fx = typeof fixture
const fx = fixture as Fx & { checkpoints: Record<string, { checkpoint_id: string }[]>; states: Record<string, unknown> }

function serve(health = fx.health, failCid: string | null = null) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string) => {
      const url = new URL(input, 'http://x')
      const parts = url.pathname.split('/').map(decodeURIComponent)
      let body: unknown = { detail: 'not found' }
      let status = 200
      if (url.pathname === '/api/health') body = health
      else if (url.pathname === '/api/threads') body = fx.threads
      else if (url.pathname === '/api/graph') body = fx.graph
      else if (parts[4] === 'checkpoints' && parts.length === 5) body = fx.checkpoints[parts[3]]
      else if (parts[4] === 'checkpoints' && parts.length === 6 && parts[5] === failCid) {
        status = 500
        body = { detail: 'boom' }
      }
      else if (parts[4] === 'checkpoints' && parts.length === 6) body = fx.states[parts[5]]
      else status = 404
      return new Response(JSON.stringify(body), { status })
    }),
  )
}

const rowsOf = (tid: string) => fx.checkpoints[tid]
const selectedRow = () => screen.getAllByTestId('timeline-row').find((r) => r.getAttribute('aria-selected') === 'true')

beforeEach(() => window.history.replaceState(null, '', '/?thread=lisbon-bug'))
afterEach(() => vi.unstubAllGlobals())

describe('App', () => {
  it('a failed state fetch does not poison the other checkpoints', async () => {
    const rows = rowsOf('lisbon-bug')
    serve(fx.health, rows[rows.length - 1].checkpoint_id)
    render(<App />)
    await waitFor(() => expect(selectedRow()).toHaveAttribute('data-checkpoint-id', rows[rows.length - 1].checkpoint_id))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('boom'))
    act(() => void fireEvent.keyDown(window, { key: 'k' }))
    await waitFor(() => expect(selectedRow()).toHaveAttribute('data-checkpoint-id', rows[rows.length - 2].checkpoint_id))
    await waitFor(() => expect(screen.getByTestId('inspector')).toBeInTheDocument())
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('opens the thread from the url and shows its newest checkpoint', async () => {
    serve()
    render(<App />)
    const rows = rowsOf('lisbon-bug')
    await waitFor(() => expect(selectedRow()).toHaveAttribute('data-checkpoint-id', rows[rows.length - 1].checkpoint_id))
    await waitFor(() => expect(screen.getByTestId('inspector')).toHaveTextContent('TP1351'))
  })

  it('steps with j and k and keeps the url in sync', async () => {
    serve()
    render(<App />)
    const rows = rowsOf('lisbon-bug')
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    act(() => void fireEvent.keyDown(window, { key: 'k' }))
    await waitFor(() => expect(selectedRow()).toHaveAttribute('data-checkpoint-id', rows[rows.length - 2].checkpoint_id))
    expect(window.location.search).toContain(`cp=${rows[rows.length - 2].checkpoint_id}`)
    act(() => void fireEvent.keyDown(window, { key: 'j' }))
    await waitFor(() => expect(selectedRow()).toHaveAttribute('data-checkpoint-id', rows[rows.length - 1].checkpoint_id))
  })

  it('d shows the diff against the parent', async () => {
    serve()
    render(<App />)
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    act(() => void fireEvent.keyDown(window, { key: 'd' }))
    await waitFor(() => expect(screen.getByTestId('diff-panel')).toBeInTheDocument())
    await waitFor(() => expect(screen.getAllByTestId('diff-op').length).toBeGreaterThan(0))
  })

  it('f opens the fork editor only when a graph is loaded', async () => {
    serve({ ...fx.health, graph: false })
    const { unmount } = render(<App />)
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    act(() => void fireEvent.keyDown(window, { key: 'f' }))
    expect(screen.queryByLabelText('Fork values')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fork' })).toBeDisabled()
    unmount()
    vi.unstubAllGlobals()
    serve()
    render(<App />)
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    await waitFor(() => expect(screen.getByRole('button', { name: 'Fork' })).toBeEnabled())
    act(() => void fireEvent.keyDown(window, { key: 'f' }))
    await waitFor(() => expect(screen.getByLabelText('Fork values')).toBeInTheDocument())
  })

  it('ignores keys while typing', async () => {
    serve()
    render(<App />)
    await waitFor(() => expect(selectedRow()).toBeTruthy())
    const before = selectedRow()!.getAttribute('data-checkpoint-id')
    act(() => void fireEvent.keyDown(window, { key: 'f' }))
    const box = await screen.findByLabelText('Fork values')
    fireEvent.keyDown(box, { key: 'k' })
    expect(selectedRow()!.getAttribute('data-checkpoint-id')).toBe(before)
  })
})
