import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { CheckpointState } from '../api'
import { StateInspector } from './StateInspector'

const state: CheckpointState = {
  checkpoint_id: 'cp-1',
  next: ['tools'],
  metadata: { source: 'loop', step: 1 },
  pending_writes: [{ task_id: 't1', channel: 'messages', value: 'w' }],
  values: {
    results: [],
    query: { __pydantic__: 'flight_recorder.samples.SearchQuery', fields: { destination: 'Lisbon', depart_after: null } },
    messages: [
      { __lc_message__: 'human', id: 'human-1', content: 'Find me the cheapest flight to Lisbon departing after 2026-11-01.' },
      {
        __lc_message__: 'ai', id: 'ai-plan', content: '',
        tool_calls: [{ name: 'search_flights', args: { destination: 'Lisbon', depart_after: null }, id: 'call-1', type: 'tool_call' }],
      },
    ],
    when: { __datetime__: '2026-10-04T09:30:00+00:00' },
    blob: { __unrepresentable__: 'numpy', repr: 'array([1, 2])' },
    long: 'x'.repeat(1000),
  },
}

describe('StateInspector', () => {
  it('renders messages with roles and tool calls', () => {
    render(<StateInspector state={state} loading={false} />)
    expect(screen.getByTestId('inspector')).toHaveAttribute('data-checkpoint-id', 'cp-1')
    const roles = screen.getAllByTestId('message').map((m) => m.getAttribute('data-role'))
    expect(roles).toEqual(['human', 'ai'])
    expect(screen.getByText('search_flights')).toBeInTheDocument()
    expect(screen.getAllByText(/depart_after/).length).toBeGreaterThan(0)
  })

  it('renders tagged values', () => {
    render(<StateInspector state={state} loading={false} />)
    expect(screen.getByText('SearchQuery')).toBeInTheDocument()
    expect(screen.getByText(/2026-10-04T09:30:00/)).toBeInTheDocument()
    expect(screen.getByText(/unrepresentable numpy/)).toHaveAttribute('title', 'array([1, 2])')
    expect(screen.getByText(/tools/)).toBeInTheDocument()
  })

  it('truncates long strings until asked', () => {
    render(<StateInspector state={state} loading={false} />)
    fireEvent.click(screen.getByRole('button', { name: 'Show all' }))
    expect(screen.getByText('x'.repeat(1000))).toBeInTheDocument()
  })

  it('shows loading and errors', () => {
    const { rerender } = render(<StateInspector state={null} loading />)
    expect(screen.getByText('Loading state...')).toBeInTheDocument()
    rerender(<StateInspector state={null} loading={false} error="boom" />)
    expect(screen.getByRole('alert')).toHaveTextContent('boom')
  })
})
