import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type CheckpointRow, type CheckpointState, type ForkRequest, type ForkResult, type Graph, type Health, type ThreadSummary } from './api'
import { DiffPanel } from './components/DiffPanel'
import { ForkEditor } from './components/ForkEditor'
import { StateInspector } from './components/StateInspector'
import { ThreadList } from './components/ThreadList'
import { Timeline } from './components/Timeline'

type Mode = 'state' | 'diff' | 'fork'

const keyOf = (tid: string, cid: string) => `${tid}|${cid}`
let timelineMarked = false

function initialParams() {
  const p = new URLSearchParams(window.location.search)
  return { thread: p.get('thread'), cp: p.get('cp') }
}

export function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [graph, setGraph] = useState<Graph | null>(null)
  const [threads, setThreads] = useState<ThreadSummary[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [threadId, setThreadId] = useState<string | null>(() => initialParams().thread)
  const [rows, setRows] = useState<{ threadId: string; rows: CheckpointRow[] } | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [compareId, setCompareId] = useState<string | null>(null)
  const [mode, setMode] = useState<Mode>('state')
  const [states, setStates] = useState<Record<string, CheckpointState>>({})
  const [stateErrors, setStateErrors] = useState<Record<string, string>>({})
  const pendingCp = useRef<string | null>(initialParams().cp)
  const requested = useRef(new Set<string>())

  const reloadThreads = useCallback(async () => {
    const list = await api.threads()
    setThreads(list)
    return list
  }, [])

  // first load: health, threads and (when forks are possible) the graph
  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const h = await api.health()
        if (!alive) return
        setHealth(h)
        const list = await reloadThreads()
        if (!alive) return
        setThreadId((cur) => cur ?? list[0]?.thread_id ?? null)
        if (h.graph) setGraph(await api.graph())
      } catch (e) {
        if (alive) setLoadError((e as Error).message)
      }
    })()
    return () => {
      alive = false
    }
  }, [reloadThreads])

  // rows of the selected thread
  useEffect(() => {
    if (threadId === null) return
    let alive = true
    api
      .checkpoints(threadId)
      .then((list) => {
        if (!alive) return
        setRows({ threadId, rows: list })
        const wanted = pendingCp.current
        pendingCp.current = null
        setSelectedId(wanted && list.some((r) => r.checkpoint_id === wanted) ? wanted : (list[list.length - 1]?.checkpoint_id ?? null))
        setCompareId(null)
        setLoadError(null)
      })
      .catch((e: Error) => alive && setLoadError(e.message))
    return () => {
      alive = false
    }
  }, [threadId])

  // the perf test reads this mark: once per page load, after the first rows paint
  useEffect(() => {
    if (rows === null || timelineMarked) return
    timelineMarked = true
    requestAnimationFrame(() => performance.mark('fr:timeline-ready'))
  }, [rows])

  const current = rows && rows.threadId === threadId ? rows.rows : null
  const selectedRow = useMemo(() => current?.find((r) => r.checkpoint_id === selectedId) ?? null, [current, selectedId])
  const baseId = compareId ?? selectedRow?.parent_id ?? null
  const baseRow = useMemo(() => current?.find((r) => r.checkpoint_id === baseId) ?? null, [current, baseId])

  // lazy state fetching with a cache
  const want = useCallback(
    (tid: string, cid: string | null) => {
      if (cid === null) return
      const k = keyOf(tid, cid)
      if (requested.current.has(k)) return
      requested.current.add(k)
      api
        .state(tid, cid)
        .then((s) => {
          setStates((prev) => ({ ...prev, [k]: s }))
          setStateErrors(({ [k]: _gone, ...rest }) => rest)
        })
        .catch((e: Error) => {
          requested.current.delete(k)
          setStateErrors((prev) => ({ ...prev, [k]: e.message }))
        })
    },
    [],
  )
  useEffect(() => {
    if (threadId === null || current === null) return
    want(threadId, selectedId)
    if (mode === 'diff') want(threadId, baseId)
  }, [threadId, current, selectedId, baseId, mode, want])

  // keep the url in sync
  useEffect(() => {
    if (threadId === null || selectedId === null) return
    const p = new URLSearchParams({ thread: threadId, cp: selectedId })
    window.history.replaceState(null, '', `?${p.toString()}`)
  }, [threadId, selectedId])

  const canFork = Boolean(health?.graph && graph)

  const step = useCallback(
    (delta: number) => {
      if (!current || selectedId === null) return
      const i = current.findIndex((r) => r.checkpoint_id === selectedId)
      const next = current[Math.min(current.length - 1, Math.max(0, i + delta))]
      if (next) setSelectedId(next.checkpoint_id)
    },
    [current, selectedId],
  )

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const t = e.target as HTMLElement | null
      if (t && ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName)) return
      if (e.key === 'j') step(1)
      else if (e.key === 'k') step(-1)
      else if (e.key === 'd') setMode((m) => (m === 'diff' ? 'state' : 'diff'))
      else if (e.key === 'f' && canFork) setMode('fork')
      else if (e.key === 'Escape') {
        setMode('state')
        setCompareId(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [step, canFork])

  const onSelectRow = (cid: string, opts: { shift: boolean }) => {
    if (opts.shift) {
      setCompareId(cid === selectedId ? null : cid)
      setMode('diff')
    } else {
      setSelectedId(cid)
    }
  }

  const onFork = async (req: ForkRequest): Promise<ForkResult> => {
    const res = await api.fork(req)
    await reloadThreads()
    return res
  }

  const openThread = (tid: string, cid: string | null) => {
    pendingCp.current = cid
    setMode('state')
    if (tid === threadId) {
      setSelectedId(cid)
    } else {
      setThreadId(tid)
    }
  }

  const selectedState = threadId && selectedId ? (states[keyOf(threadId, selectedId)] ?? null) : null
  const stateError = threadId && selectedId ? (stateErrors[keyOf(threadId, selectedId)] ?? null) : null
  const baseState = threadId && baseId ? (states[keyOf(threadId, baseId)] ?? null) : null
  const label = (r: CheckpointRow | null) => (r ? `step ${r.step ?? '-'}` : '')

  return (
    <div className="app">
      <header className="app-header">
        <h1>flight-recorder</h1>
        <span className="source">{health?.source ?? ''}</span>
        <span className={canFork ? 'chip chip-tag' : 'chip chip-warn'}>{canFork ? 'graph loaded' : 'read only'}</span>
        <span className="hints">j/k step  d diff  f fork  shift+click compare  esc back</span>
      </header>
      <main className="panes">
        <section className="pane" aria-label="Threads">
          <h2 className="pane-title">Threads</h2>
          <ThreadList threads={threads} selected={threadId} onSelect={(tid) => openThread(tid, null)} />
        </section>
        <section className="pane" aria-label="Timeline">
          <h2 className="pane-title">Timeline</h2>
          <select className="thread-select" aria-label="Thread" value={threadId ?? ''} onChange={(e) => openThread(e.target.value, null)}>
            {threads.map((t) => (
              <option key={t.thread_id} value={t.thread_id}>{t.thread_id}</option>
            ))}
          </select>
          {loadError ? <div className="error" role="alert">{loadError}</div> : null}
          {current ? (
            <div className="timeline-wrap">
              <Timeline rows={current} selectedId={selectedId} compareId={compareId} onSelect={onSelectRow} />
            </div>
          ) : loadError ? null : (
            <p className="empty">Loading checkpoints...</p>
          )}
        </section>
        <section className="pane" aria-label="Details">
          <div className="tabs">
            {(['state', 'diff', 'fork'] as const).map((m) => (
              <button
                key={m}
                type="button"
                aria-pressed={mode === m}
                disabled={m === 'fork' && !canFork}
                title={m === 'fork' && !canFork ? 'Start with --graph module:attr to fork' : undefined}
                onClick={() => setMode(m)}
              >
                {m === 'state' ? 'State' : m === 'diff' ? 'Diff' : 'Fork'}
              </button>
            ))}
          </div>
          {mode === 'state' ? <StateInspector state={selectedState} loading={selectedId !== null && selectedState === null} error={stateError} /> : null}
          {mode === 'diff' ? (
            baseId === null ? (
              <p className="empty">No parent</p>
            ) : (
              <DiffPanel before={baseState} after={selectedState} beforeLabel={label(baseRow)} afterLabel={label(selectedRow)} />
            )
          ) : null}
          {mode === 'fork' && canFork && selectedRow && selectedState && graph ? (
            <ForkEditor
              key={`${threadId}|${selectedId}`}
              threadId={threadId!}
              row={selectedRow}
              state={selectedState}
              nodes={graph.nodes}
              onFork={onFork}
              onOpenThread={openThread}
            />
          ) : null}
          {mode === 'fork' && (!selectedState || !selectedRow) ? <p className="empty">Loading state...</p> : null}
        </section>
      </main>
    </div>
  )
}
