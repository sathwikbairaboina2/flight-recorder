import type { Json } from './diff'

export const TAGS = [
  '__lc_message__', '__pydantic__', '__object__', '__set__', '__bytes__', '__datetime__', '__date__',
  '__time__', '__uuid__', '__decimal__', '__float__', '__map__', '__unrepresentable__',
] as const
export type Tag = (typeof TAGS)[number]

export type Obj = { [key: string]: Json }
export const isObj = (v: Json): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v)

export function tagOf(v: Json): Tag | null {
  if (!isObj(v)) return null
  return TAGS.find((t) => Object.prototype.hasOwnProperty.call(v, t)) ?? null
}

export function isMessage(v: Json): v is Obj {
  return tagOf(v) === '__lc_message__'
}

export function typeName(dotted: string): string {
  return dotted.slice(dotted.lastIndexOf('.') + 1)
}

/** LangGraph bookkeeping channels: `branch:to:<node>` triggers and `__start__`-style names. */
export const isInternal = (channel: string) => channel.startsWith('branch:to:') || channel.startsWith('__')

/** User channels with `messages` first then sorted, and internal channels sorted. */
export function orderChannels(values: Obj): { user: string[]; internal: string[] } {
  const keys = Object.keys(values)
  const user = keys
    .filter((k) => !isInternal(k))
    .sort((a, b) => (a === 'messages' ? -1 : b === 'messages' ? 1 : a.localeCompare(b)))
  return { user, internal: keys.filter(isInternal).sort() }
}
