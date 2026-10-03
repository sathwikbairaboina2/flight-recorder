import type { ThreadSummary } from '../api'

interface Props {
  threads: ThreadSummary[]
  selected: string | null
  onSelect: (threadId: string) => void
}

export function ThreadList({ threads, selected, onSelect }: Props) {
  if (threads.length === 0) {
    return <p className="empty">No threads in this database yet. Run your graph with a SqliteSaver, then reload.</p>
  }
  return (
    <div className="thread-list" role="listbox" aria-label="Threads">
      {threads.map((t) => (
        <div
          key={t.thread_id}
          role="option"
          tabIndex={0}
          aria-selected={t.thread_id === selected}
          data-origin={t.origin}
          className="thread"
          onClick={() => onSelect(t.thread_id)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              onSelect(t.thread_id)
            }
          }}
        >
          <span className="thread-id">{t.thread_id}</span>
          <span className="thread-meta">
            {t.checkpoint_count} checkpoints
            {t.fork_of ? <span className="chip chip-fork">fork of {t.fork_of.thread_id}</span> : null}
          </span>
        </div>
      ))}
    </div>
  )
}
