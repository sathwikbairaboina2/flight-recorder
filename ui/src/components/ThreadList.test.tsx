import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ThreadSummary } from '../api'
import { ThreadList } from './ThreadList'

const t = (thread_id: string, extra: Partial<ThreadSummary> = {}): ThreadSummary => ({
  thread_id, origin: 'source', checkpoint_count: 5, first_at: null, last_at: null, namespaces: [''], fork_of: null, ...extra,
})

describe('ThreadList', () => {
  it('lists threads, marks the selected one and reports clicks', () => {
    const onSelect = vi.fn()
    render(
      <ThreadList
        threads={[t('lisbon-bug'), t('fork:abc', { origin: 'scratch', fork_of: { thread_id: 'lisbon-bug', checkpoint_id: 'c' } })]}
        selected="lisbon-bug"
        onSelect={onSelect}
      />,
    )
    const options = screen.getAllByRole('option')
    expect(options[0]).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText(/fork of lisbon-bug/)).toBeInTheDocument()
    fireEvent.click(options[1])
    expect(onSelect).toHaveBeenCalledWith('fork:abc')
  })
})
