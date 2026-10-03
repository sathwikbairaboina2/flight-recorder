// Typed client for the sidecar REST API (spec: REST table). Same origin; Vite proxies /api in dev.
import type { Json } from './lib/diff'

export type Origin = 'source' | 'scratch'
export interface ThreadSummary {
  thread_id: string
  origin: Origin
  checkpoint_count: number
  first_at: string | null
  last_at: string | null
  namespaces: string[]
  fork_of: { thread_id: string; checkpoint_id: string } | null
}
export interface CheckpointRow {
  checkpoint_id: string
  parent_id: string | null
  step: number | null
  source: string | null
  next: string[]
  writes_from: string[]
  created_at: string
  state_bytes: number
  origin: Origin
}
export interface PendingWrite {
  task_id: string
  channel: string
  value: Json
}
export interface CheckpointState {
  checkpoint_id: string
  values: { [channel: string]: Json }
  next: string[]
  pending_writes: PendingWrite[]
  metadata: Json
}
export interface Health {
  ok: boolean
  version: string
  graph: boolean
  source: string
}
export interface Graph {
  nodes: string[]
  edges: { source: string; target: string; conditional: boolean }[]
}
export interface ForkRequest {
  thread_id: string
  checkpoint_id: string
  values: { [channel: string]: Json }
  as_node: string | null
}
export interface ForkResult {
  fork_id: string
  thread_id: string
  base_checkpoint_id: string
  head_checkpoint_id: string
  status: 'done' | 'interrupted' | 'error'
  events: { node: string; update: Json }[]
  error: string | null
  elapsed_ms: number
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // keep statusText
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

const enc = encodeURIComponent

export const api = {
  health: () => call<Health>('/api/health'),
  threads: () => call<ThreadSummary[]>('/api/threads'),
  checkpoints: (threadId: string, ns = '') => call<CheckpointRow[]>(`/api/threads/${enc(threadId)}/checkpoints?ns=${enc(ns)}`),
  state: (threadId: string, checkpointId: string, ns = '') =>
    call<CheckpointState>(`/api/threads/${enc(threadId)}/checkpoints/${enc(checkpointId)}?ns=${enc(ns)}`),
  graph: () => call<Graph>('/api/graph'),
  fork: (req: ForkRequest) =>
    call<ForkResult>('/api/forks', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(req) }),
}
