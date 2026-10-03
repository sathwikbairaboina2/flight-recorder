import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CheckpointRow } from '../api'
import { Timeline } from './Timeline'

function rows(n: number): CheckpointRow[] {
  return Array.from({ length: n }, (_, i) => ({
    checkpoint_id: `cp-${String(i).padStart(6, '0')}`,
    parent_id: i === 0 ? null : `cp-${String(i - 1).padStart(6, '0')}`,
    step: i - 1,
    source: i === 0 ? 'input' : 'loop',
    next: ['tick'],
    writes_from: i === 0 ? [] : ['tick'],
    created_at: new Date(Date.UTC(2026, 9, 4, 10, 0, 0, i)).toISOString(),
    state_bytes: 1500,
    origin: 'source',
  }))
}

describe('Timeline', () => {
  it('virtualizes: 10,000 rows render only a window', () => {
    render(<Timeline rows={rows(10_000)} selectedId={null} compareId={null} onSelect={() => {}} />)
    expect(screen.getByTestId('timeline')).toHaveAttribute('data-count', '10000')
    const rendered = screen.getAllByTestId('timeline-row').length
    expect(rendered).toBeGreaterThan(0)
    expect(rendered).toBeLessThan(100)
  })

  it('selects on click and passes shift for compare', () => {
    const onSelect = vi.fn()
    render(<Timeline rows={rows(5)} selectedId="cp-000001" compareId={null} onSelect={onSelect} />)
    const [first] = screen.getAllByTestId('timeline-row')
    fireEvent.click(first)
    fireEvent.click(first, { shiftKey: true })
    expect(onSelect).toHaveBeenNthCalledWith(1, 'cp-000000', { shift: false })
    expect(onSelect).toHaveBeenNthCalledWith(2, 'cp-000000', { shift: true })
    const selected = screen.getAllByTestId('timeline-row').find((r) => r.getAttribute('aria-selected') === 'true')
    expect(selected).toHaveAttribute('data-checkpoint-id', 'cp-000001')
  })

  it('puts an older branch on lane 1', () => {
    const base = rows(4)
    const branch: CheckpointRow = { ...base[3], checkpoint_id: 'cp-000009', parent_id: 'cp-000002', source: 'update' }
    render(<Timeline rows={[...base, branch]} selectedId={null} compareId={null} onSelect={() => {}} />)
    const byId = (id: string) => screen.getAllByTestId('timeline-row').find((r) => r.dataset.checkpointId === id)!
    expect(byId('cp-000009')).toHaveAttribute('data-lane', '0')
    expect(byId('cp-000003')).toHaveAttribute('data-lane', '1')
  })

  it('shows node chips', () => {
    render(<Timeline rows={rows(3)} selectedId={null} compareId={null} onSelect={() => {}} />)
    expect(screen.getAllByText('tick').length).toBeGreaterThan(0)
  })
})
