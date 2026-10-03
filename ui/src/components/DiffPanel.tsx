import { useMemo } from 'react'
import type { CheckpointState } from '../api'
import { diff, formatPath, type DiffOp, type Json } from '../lib/diff'

interface Props {
  before: CheckpointState | null
  after: CheckpointState | null
  beforeLabel: string
  afterLabel: string
}

const short = (v: Json) => {
  const s = JSON.stringify(v) ?? 'undefined'
  return s.length > 200 ? `${s.slice(0, 200)}...` : s
}

function OpRow({ op }: { op: DiffOp }) {
  if (op.op === 'move') {
    const to = op.to[op.to.length - 1]
    return (
      <div className="diff-op" data-testid="diff-op" data-op="move">
        <span className="chip chip-source">move</span>
        <span className="diff-path">{formatPath(op.from)}</span>
        <span className="muted">{`to index ${String(to)}`}</span>
      </div>
    )
  }
  return (
    <div className="diff-op" data-testid="diff-op" data-op={op.op}>
      <span className="chip chip-source">{op.op}</span>
      <span className="diff-path">{formatPath(op.path)}</span>
      {op.op === 'replace' ? (
        <span className="diff-values">
          <span className="diff-before">{short(op.before)}</span>
          <span className="muted">{'->'}</span>
          <span className="diff-after">{short(op.after)}</span>
        </span>
      ) : (
        <span className={op.op === 'add' ? 'diff-after' : 'diff-before'}>{short(op.value)}</span>
      )}
    </div>
  )
}

export function DiffPanel({ before, after, beforeLabel, afterLabel }: Props) {
  const ops = useMemo(() => (before && after ? diff(before.values, after.values) : null), [before, after])
  return (
    <div className="diff-panel" data-testid="diff-panel">
      <div className="diff-head">
        <span>{`${beforeLabel} -> ${afterLabel}`}</span>
        {ops ? <span className="muted">{ops.length === 1 ? '1 change' : `${ops.length} changes`}</span> : null}
      </div>
      {ops === null ? <p className="empty">Loading...</p> : null}
      {ops !== null && ops.length === 0 ? <p className="empty">No changes</p> : null}
      {ops?.map((op, i) => <OpRow key={i} op={op} />)}
    </div>
  )
}
