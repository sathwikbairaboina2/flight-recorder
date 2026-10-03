// Structural diff over bridged JSON (ADR 0006). Pure: no DOM, no React.

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json }
export type PathSeg = string | number | { id: string }
export type Path = PathSeg[]
export type DiffOp =
  | { op: 'add'; path: Path; value: Json }
  | { op: 'remove'; path: Path; value: Json }
  | { op: 'replace'; path: Path; before: Json; after: Json }
  | { op: 'move'; from: Path; to: Path }

const isObj = (v: Json): v is { [key: string]: Json } => typeof v === 'object' && v !== null && !Array.isArray(v)

function keyOf(v: Json): string | null {
  return isObj(v) && typeof v.id === 'string' ? v.id : null
}

/** An array is keyed when every element is an object with a unique string `id`. Empty arrays are not keyed. */
export function isKeyed(arr: Json[]): boolean {
  if (arr.length === 0) return false
  const seen = new Set<string>()
  for (const v of arr) {
    const k = keyOf(v)
    if (k === null || seen.has(k)) return false
    seen.add(k)
  }
  return true
}

export function deepEqual(a: Json, b: Json): boolean {
  if (a === b) return true
  if (Array.isArray(a)) {
    if (!Array.isArray(b) || a.length !== b.length) return false
    return a.every((v, i) => deepEqual(v, b[i]))
  }
  if (isObj(a)) {
    if (!isObj(b)) return false
    const ka = Object.keys(a)
    if (ka.length !== Object.keys(b).length) return false
    return ka.every((k) => Object.prototype.hasOwnProperty.call(b, k) && deepEqual(a[k], b[k]))
  }
  return false
}

export function diff(a: Json, b: Json, path: Path = []): DiffOp[] {
  if (deepEqual(a, b)) return []
  if (isObj(a) && isObj(b)) {
    const ops: DiffOp[] = []
    for (const k of Object.keys(a)) {
      if (!Object.prototype.hasOwnProperty.call(b, k)) ops.push({ op: 'remove', path: [...path, k], value: a[k] })
      else ops.push(...diff(a[k], b[k], [...path, k]))
    }
    for (const k of Object.keys(b)) {
      if (!Object.prototype.hasOwnProperty.call(a, k)) ops.push({ op: 'add', path: [...path, k], value: b[k] })
    }
    return ops
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    return isKeyed(a) && isKeyed(b) ? diffKeyed(a, b, path) : diffIndexed(a, b, path)
  }
  return [{ op: 'replace', path, before: a, after: b }]
}

function diffIndexed(a: Json[], b: Json[], path: Path): DiffOp[] {
  const ops: DiffOp[] = []
  const common = Math.min(a.length, b.length)
  for (let i = 0; i < common; i++) ops.push(...diff(a[i], b[i], [...path, i]))
  for (let i = a.length - 1; i >= b.length; i--) ops.push({ op: 'remove', path: [...path, i], value: a[i] })
  for (let i = a.length; i < b.length; i++) ops.push({ op: 'add', path: [...path, i], value: b[i] })
  return ops
}

function diffKeyed(a: Json[], b: Json[], path: Path): DiffOp[] {
  const ops: DiffOp[] = []
  const bIds = new Set(b.map((v) => keyOf(v) as string))
  const aById = new Map(a.map((v) => [keyOf(v) as string, v]))
  // 1. nested changes and removals, addressed by id
  for (const v of a) {
    const id = keyOf(v) as string
    if (!bIds.has(id)) ops.push({ op: 'remove', path: [...path, { id }], value: v })
  }
  for (const v of b) {
    const id = keyOf(v) as string
    const before = aById.get(id)
    if (before !== undefined) ops.push(...diff(before, v, [...path, { id }]))
  }
  // 2. additions at their final index, left to right
  const cur: string[] = a.map((v) => keyOf(v) as string).filter((id) => bIds.has(id))
  b.forEach((v, i) => {
    const id = keyOf(v) as string
    if (!aById.has(id)) {
      ops.push({ op: 'add', path: [...path, i], value: v })
      cur.splice(i, 0, id)
    }
  })
  // 3. moves that fix the order left to right
  b.forEach((v, i) => {
    const id = keyOf(v) as string
    if (cur[i] !== id) {
      const from = cur.indexOf(id)
      cur.splice(from, 1)
      cur.splice(i, 0, id)
      ops.push({ op: 'move', from: [...path, { id }], to: [...path, i] })
    }
  })
  return ops
}

function clone<T extends Json>(v: T): T {
  return structuredClone(v)
}

// defineProperty, not assignment, so a key named __proto__ stays an own data property
function setOwn(obj: Record<string, Json>, key: string, value: Json): void {
  Object.defineProperty(obj, key, { value, writable: true, enumerable: true, configurable: true })
}

function locate(container: Json, seg: PathSeg): string | number {
  if (typeof seg === 'object') {
    if (!Array.isArray(container)) throw new Error('id segment on a non-array')
    const idx = container.findIndex((v) => keyOf(v) === seg.id)
    if (idx < 0) throw new Error(`no element with id ${seg.id}`)
    return idx
  }
  return seg
}

function parentOf(root: Json, path: Path): [Json, string | number] {
  let node = root
  for (const seg of path.slice(0, -1)) {
    const k = locate(node, seg)
    node = (node as Record<string | number, Json>)[k]
  }
  return [node, locate(node, path[path.length - 1])]
}

/** Replay ops on a copy of `a`. Throws on ops that do not fit. */
export function apply(a: Json, ops: DiffOp[]): Json {
  let root = clone(a)
  for (const o of ops) {
    if (o.op === 'move') {
      const [arr, from] = parentOf(root, o.from)
      const [, to] = parentOf(root, o.to)
      const list = arr as Json[]
      const [item] = list.splice(from as number, 1)
      list.splice(to as number, 0, item)
      continue
    }
    if (o.path.length === 0) {
      if (o.op === 'replace') root = clone(o.after)
      else throw new Error(`${o.op} at the root`)
      continue
    }
    const [parent, key] = parentOf(root, o.path)
    if (Array.isArray(parent)) {
      const i = key as number
      if (o.op === 'add') parent.splice(i, 0, clone(o.value))
      else if (o.op === 'remove') parent.splice(i, 1)
      else parent[i] = clone(o.after)
    } else {
      const obj = parent as Record<string, Json>
      if (o.op === 'remove') delete obj[key as string]
      else setOwn(obj, key as string, clone(o.op === 'add' ? o.value : o.after))
    }
  }
  return root
}

/** Human-readable path, e.g. messages[id=ai-plan].tool_calls[0].args.depart_after */
export function formatPath(path: Path): string {
  let out = ''
  for (const seg of path) {
    if (typeof seg === 'number') out += `[${seg}]`
    else if (typeof seg === 'object') out += `[id=${seg.id}]`
    else out += out === '' ? seg : `.${seg}`
  }
  return out === '' ? '(root)' : out
}
