import { deepEqual, type Json } from './diff'

type Values = { [channel: string]: Json }

/** Top-level channels of `after` that differ from `before` (new keys included, removed keys ignored). */
export function changedTopLevel(before: Values, after: Values): Values {
  const out: Values = {}
  for (const [k, v] of Object.entries(after)) {
    if (!Object.prototype.hasOwnProperty.call(before, k) || !deepEqual(before[k], v)) out[k] = v
  }
  return out
}
