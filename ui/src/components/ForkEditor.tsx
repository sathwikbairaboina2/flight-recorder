import { useMemo, useState } from 'react'
import type { CheckpointRow, CheckpointState, ForkRequest, ForkResult } from '../api'
import { changedTopLevel } from '../lib/changed'
import type { Json } from '../lib/diff'
import { orderChannels } from '../lib/tags'

interface Props {
  threadId: string
  row: CheckpointRow
  state: CheckpointState
  nodes: string[]
  onFork: (req: ForkRequest) => Promise<ForkResult>
  onOpenThread: (threadId: string, checkpointId: string) => void
}

export function ForkEditor({ threadId, row, state, nodes, onFork, onOpenThread }: Props) {
  const choices = useMemo(() => nodes.filter((n) => n !== '__start__' && n !== '__end__'), [nodes])
  const initialText = useMemo(() => {
    const out: { [k: string]: Json } = {}
    for (const k of orderChannels(state.values).user) out[k] = state.values[k]
    return JSON.stringify(out, null, 2)
  }, [state])
  const [text, setText] = useState(initialText)
  const [asNode, setAsNode] = useState(choices.includes(row.writes_from[0]) ? row.writes_from[0] : (choices[0] ?? ''))
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ForkResult | null>(null)

  async function run() {
    let parsed: { [k: string]: Json }
    try {
      parsed = JSON.parse(text) as { [k: string]: Json }
    } catch (e) {
      setError(`Invalid JSON: ${(e as Error).message}`)
      return
    }
    setError(null)
    setRunning(true)
    try {
      const res = await onFork({
        thread_id: threadId,
        checkpoint_id: row.checkpoint_id,
        values: changedTopLevel(state.values, parsed),
        as_node: asNode || null,
      })
      setResult(res)
    } catch (e) {
      setResult(null)
      setError((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="fork-editor">
      <label htmlFor="fork-values" className="label">Fork values</label>
      <textarea id="fork-values" aria-label="Fork values" spellCheck={false} value={text} onChange={(e) => setText(e.target.value)} />
      <p className="help">Only changed top-level channels are sent. The original thread is never modified.</p>
      <label htmlFor="fork-as-node" className="label">As node</label>
      <select id="fork-as-node" aria-label="As node" value={asNode} onChange={(e) => setAsNode(e.target.value)}>
        {choices.map((n) => (
          <option key={n} value={n}>{n}</option>
        ))}
      </select>
      <button type="button" className="primary" disabled={running} onClick={run}>
        {running ? 'Running...' : 'Run fork'}
      </button>
      {error ? <div className="error" role="alert">{error}</div> : null}
      {result ? (
        <div className="fork-result" data-testid="fork-result" data-status={result.status}>
          <div>
            <span className="chip chip-fork">{result.status}</span> <span>{`${result.elapsed_ms} ms`}</span>
          </div>
          <div className="fork-events">
            {result.events.map((e, i) => (
              <span key={i} className="chip chip-node">{e.node}</span>
            ))}
          </div>
          {result.error ? <div className="error">{result.error}</div> : null}
          <button type="button" onClick={() => onOpenThread(result.thread_id, result.head_checkpoint_id)}>Open fork</button>
        </div>
      ) : null}
    </div>
  )
}
