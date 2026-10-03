import type { CheckpointState } from '../api'
import { orderChannels } from '../lib/tags'
import { JsonTree } from './JsonTree'

interface Props {
  state: CheckpointState | null
  loading: boolean
  error?: string | null
}

export function StateInspector({ state, loading, error }: Props) {
  if (error) return <div className="error" role="alert">{error}</div>
  if (loading || state === null) return <p className="empty">{loading ? 'Loading state...' : 'Select a checkpoint.'}</p>
  const { user, internal } = orderChannels(state.values)
  return (
    <div className="inspector" data-testid="inspector" data-checkpoint-id={state.checkpoint_id}>
      <div className="next-line">
        <span className="label">Next</span>
        {state.next.length === 0 ? (
          <span className="muted">end of run</span>
        ) : (
          state.next.map((n) => (
            <span key={n} className="chip chip-next">{n}</span>
          ))
        )}
      </div>
      {user.map((k) => (
        <section key={k} className="channel">
          <h3>{k}</h3>
          <JsonTree value={state.values[k]} depth={0} />
        </section>
      ))}
      {internal.length > 0 ? (
        <details className="channel">
          <summary>Internal channels</summary>
          {internal.map((k) => (
            <section key={k}>
              <h3>{k}</h3>
              <JsonTree value={state.values[k]} depth={2} />
            </section>
          ))}
        </details>
      ) : null}
      {state.pending_writes.length > 0 ? (
        <section className="channel">
          <h3>Pending writes</h3>
          {state.pending_writes.map((w, i) => (
            <div key={`${w.task_id}-${i}`} className="entry">
              <span className="key">{w.channel}</span>
              <JsonTree value={w.value} depth={1} />
            </div>
          ))}
        </section>
      ) : null}
    </div>
  )
}
