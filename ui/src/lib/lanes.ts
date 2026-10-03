// Branch lanes for the timeline. Pure. Lane 0 is the chain ending at the newest checkpoint.

export interface LaneInput {
  checkpoint_id: string
  parent_id: string | null
}
export interface Lane {
  lane: number
  /** parent checkpoint id when this row starts a branch off another lane, else null */
  branchFrom: string | null
}

export function computeLanes(rows: LaneInput[]): Map<string, Lane> {
  const byId = new Map(rows.map((r) => [r.checkpoint_id, r]))
  const hasChild = new Set<string>()
  for (const r of rows) if (r.parent_id && byId.has(r.parent_id)) hasChild.add(r.parent_id)
  // checkpoint ids are uuid6, so string order is time order; newest leaf first
  const leaves = rows
    .filter((r) => !hasChild.has(r.checkpoint_id))
    .map((r) => r.checkpoint_id)
    .sort()
    .reverse()
  const out = new Map<string, Lane>()
  let next = 0
  for (const leaf of leaves) {
    const lane = next++
    let id: string | null = leaf
    let top: string | null = null
    while (id !== null && byId.has(id) && !out.has(id)) {
      out.set(id, { lane, branchFrom: null })
      top = id
      const parent: string | null = byId.get(id)!.parent_id
      id = parent
    }
    if (top !== null && id !== null && out.has(id)) out.set(top, { lane, branchFrom: id })
  }
  return out
}

export function laneCount(lanes: Map<string, Lane>): number {
  let max = -1
  for (const l of lanes.values()) max = Math.max(max, l.lane)
  return max + 1
}
