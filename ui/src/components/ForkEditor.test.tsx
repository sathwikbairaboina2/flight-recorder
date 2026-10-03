import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CheckpointRow, CheckpointState, ForkResult } from '../api'
import { ForkEditor } from './ForkEditor'

const row: CheckpointRow = {
  checkpoint_id: 'cp-plan', parent_id: 'cp-0', step: 1, source: 'loop', next: ['tools'], writes_from: ['plan'],
  created_at: '2026-10-04T10:00:00Z', state_bytes: 900, origin: 'source',
}
const state: CheckpointState = {
  checkpoint_id: 'cp-plan', next: ['tools'], pending_writes: [], metadata: null,
  values: { messages: [{ __lc_message__: 'ai', id: 'ai-plan', tool_calls: [{ args: { depart_after: null } }] }], results: [] },
}
const result: ForkResult = {
  fork_id: 'f1', thread_id: 'fork:f1', base_checkpoint_id: 'cp-plan', head_checkpoint_id: 'cp-head', status: 'done',
  events: [{ node: 'tools', update: {} }, { node: 'answer', update: {} }], error: null, elapsed_ms: 87.5,
}
const nodes = ['__start__', 'plan', 'tools', 'answer', '__end__']

describe('ForkEditor', () => {
  it('sends only the changed channels with the default as_node', async () => {
    const onFork = vi.fn(async () => result)
    const onOpen = vi.fn()
    render(<ForkEditor threadId="lisbon-bug" row={row} state={state} nodes={nodes} onFork={onFork} onOpenThread={onOpen} />)
    expect(screen.getByLabelText('As node')).toHaveValue('plan')
    const box = screen.getByLabelText('Fork values') as HTMLTextAreaElement
    fireEvent.change(box, { target: { value: box.value.replace('"depart_after": null', '"depart_after": "2026-11-01"') } })
    fireEvent.click(screen.getByRole('button', { name: 'Run fork' }))
    await waitFor(() => expect(screen.getByTestId('fork-result')).toHaveTextContent('done'))
    expect(onFork).toHaveBeenCalledWith({
      thread_id: 'lisbon-bug',
      checkpoint_id: 'cp-plan',
      as_node: 'plan',
      values: { messages: [{ __lc_message__: 'ai', id: 'ai-plan', tool_calls: [{ args: { depart_after: '2026-11-01' } }] }] },
    })
    expect(screen.getByTestId('fork-result')).toHaveTextContent('87.5 ms')
    fireEvent.click(screen.getByRole('button', { name: 'Open fork' }))
    expect(onOpen).toHaveBeenCalledWith('fork:f1', 'cp-head')
  })

  it('refuses invalid JSON', () => {
    const onFork = vi.fn()
    render(<ForkEditor threadId="t" row={row} state={state} nodes={nodes} onFork={onFork} onOpenThread={() => {}} />)
    fireEvent.change(screen.getByLabelText('Fork values'), { target: { value: '{ nope' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run fork' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid JSON')
    expect(onFork).not.toHaveBeenCalled()
  })

  it('does not offer __start__ or __end__', () => {
    render(<ForkEditor threadId="t" row={row} state={state} nodes={nodes} onFork={vi.fn()} onOpenThread={() => {}} />)
    const options = Array.from((screen.getByLabelText('As node') as HTMLSelectElement).options).map((o) => o.value)
    expect(options).toEqual(['plan', 'tools', 'answer'])
  })
})
