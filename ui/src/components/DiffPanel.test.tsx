import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { CheckpointState } from '../api'
import { DiffPanel } from './DiffPanel'

const st = (values: CheckpointState['values']): CheckpointState => ({ checkpoint_id: 'x', values, next: [], pending_writes: [], metadata: null })

describe('DiffPanel', () => {
  it('shows the dropped date filter as one replace', () => {
    const before = st({ messages: [{ __lc_message__: 'ai', id: 'ai-plan', tool_calls: [{ args: { depart_after: null } }] }] })
    const after = st({ messages: [{ __lc_message__: 'ai', id: 'ai-plan', tool_calls: [{ args: { depart_after: '2026-11-01' } }] }] })
    render(<DiffPanel before={before} after={after} beforeLabel="step 1" afterLabel="fork step 2" />)
    const ops = screen.getAllByTestId('diff-op')
    expect(ops).toHaveLength(1)
    expect(ops[0]).toHaveAttribute('data-op', 'replace')
    expect(ops[0]).toHaveTextContent('messages[id=ai-plan].tool_calls[0].args.depart_after')
    expect(ops[0]).toHaveTextContent('"2026-11-01"')
    expect(screen.getByText('1 change')).toBeInTheDocument()
  })

  it('says when nothing changed or a side is loading', () => {
    const { rerender } = render(<DiffPanel before={st({ a: 1 })} after={st({ a: 1 })} beforeLabel="a" afterLabel="b" />)
    expect(screen.getByText('No changes')).toBeInTheDocument()
    rerender(<DiffPanel before={null} after={st({ a: 1 })} beforeLabel="a" afterLabel="b" />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders moves', () => {
    const m = (ids: string[]) => st({ messages: ids.map((id) => ({ id })) })
    render(<DiffPanel before={m(['a', 'b'])} after={m(['b', 'a'])} beforeLabel="a" afterLabel="b" />)
    expect(screen.getAllByTestId('diff-op').every((o) => o.getAttribute('data-op') === 'move')).toBe(true)
  })
})
