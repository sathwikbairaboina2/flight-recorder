import { useVirtualizer } from '@tanstack/react-virtual'
import { useEffect, useMemo, useRef } from 'react'
import type { CheckpointRow } from '../api'
import { formatBytes, relativeTime } from '../lib/format'
import { computeLanes, laneCount } from '../lib/lanes'

interface Props {
  rows: CheckpointRow[]
  selectedId: string | null
  compareId: string | null
  onSelect: (checkpointId: string, opts: { shift: boolean }) => void
}

const ROW_HEIGHT = 36
const LANE_WIDTH = 14

export function Timeline({ rows, selectedId, compareId, onSelect }: Props) {
  const parentRef = useRef<HTMLDivElement>(null)
  const lanes = useMemo(() => computeLanes(rows), [rows])
  const lanesTotal = Math.max(1, laneCount(lanes))
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
    // jsdom has no layout, so give the virtualizer a window to start from
    initialRect: { width: 800, height: 600 },
  })

  useEffect(() => {
    if (selectedId === null) return
    const index = rows.findIndex((r) => r.checkpoint_id === selectedId)
    if (index >= 0) virtualizer.scrollToIndex(index, { align: 'auto' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, rows])

  if (rows.length === 0) return <p className="empty">This thread has no checkpoints.</p>
  const first = rows[0].created_at

  return (
    <div ref={parentRef} className="timeline" data-testid="timeline" data-count={rows.length} role="listbox" aria-label="Checkpoints">
      <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
        {virtualizer.getVirtualItems().map((item) => {
          const row = rows[item.index]
          const lane = lanes.get(row.checkpoint_id) ?? { lane: 0, branchFrom: null }
          const selected = row.checkpoint_id === selectedId
          const compare = row.checkpoint_id === compareId
          return (
            <div
              key={row.checkpoint_id}
              data-testid="timeline-row"
              data-checkpoint-id={row.checkpoint_id}
              data-lane={lane.lane}
              data-origin={row.origin}
              data-compare={compare ? 'true' : undefined}
              role="option"
              aria-selected={selected}
              className="tl-row"
              style={{ position: 'absolute', top: 0, left: 0, right: 0, height: ROW_HEIGHT, transform: `translateY(${item.start}px)` }}
              onClick={(e) => onSelect(row.checkpoint_id, { shift: e.shiftKey })}
            >
              <span className="tl-gutter" style={{ width: lanesTotal * LANE_WIDTH }} aria-hidden="true">
                <span className="tl-dot" data-origin={row.origin} style={{ left: lane.lane * LANE_WIDTH + 4 }} />
                {lane.branchFrom ? <span className="tl-branch" style={{ left: 0, width: lane.lane * LANE_WIDTH + 4 }} /> : null}
              </span>
              <span className="tl-step">{row.step ?? '-'}</span>
              <span className="chip chip-source">{row.source ?? 'unknown'}</span>
              <span className="tl-nodes">
                {row.writes_from.map((n) => (
                  <span key={`w-${n}`} className="chip chip-node">{n}</span>
                ))}
                <span className="tl-arrow" aria-hidden="true">{'->'}</span>
                {row.next.length === 0 ? <span className="tl-end">end</span> : null}
                {row.next.map((n) => (
                  <span key={`n-${n}`} className="chip chip-next">{n}</span>
                ))}
              </span>
              <span className="tl-time">{relativeTime(row.created_at, first)}</span>
              <span className="tl-size">{formatBytes(row.state_bytes)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
