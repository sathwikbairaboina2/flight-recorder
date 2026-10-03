export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export function relativeTime(at: string, first: string): string {
  const ms = Math.max(0, Date.parse(at) - Date.parse(first))
  if (ms < 1000) return `+${Math.round(ms)} ms`
  if (ms < 60_000) return `+${(ms / 1000).toFixed(1)} s`
  const s = Math.round(ms / 1000)
  return `+${Math.floor(s / 60)}m ${s % 60}s`
}

export function shortId(id: string): string {
  return id.slice(-8)
}
