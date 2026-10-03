import { useState } from 'react'
import type { Json } from '../lib/diff'
import { isMessage, isObj, tagOf, typeName, type Obj } from '../lib/tags'
import { MessageCard } from './MessageCard'

const STRING_LIMIT = 400

function LongString({ value }: { value: string }) {
  const [all, setAll] = useState(false)
  if (value.length <= STRING_LIMIT) return <span className="str">{value}</span>
  return (
    <span>
      <span className="str">{all ? value : `${value.slice(0, STRING_LIMIT)}...`}</span>{' '}
      {all ? null : (
        <button type="button" className="link" onClick={() => setAll(true)}>
          Show all
        </button>
      )}
    </span>
  )
}

function Entries({ entries, depth }: { entries: [string, Json][]; depth: number }) {
  return (
    <div className="children">
      {entries.map(([k, v]) => (
        <div key={k} className="entry">
          <span className="key">{k}</span>
          <JsonTree value={v} depth={depth + 1} />
        </div>
      ))}
    </div>
  )
}

function Tagged({ value, depth }: { value: Obj; depth: number }) {
  const tag = tagOf(value)!
  const body = value[tag]
  switch (tag) {
    case '__pydantic__':
    case '__object__': {
      const name = typeName(String(body))
      const inner = value.fields ?? value.args ?? {}
      return (
        <span className="tagged">
          <span className="chip chip-tag">{name}</span>
          <JsonTree value={inner} depth={depth} />
        </span>
      )
    }
    case '__set__':
      return (
        <span className="tagged">
          <span className="chip chip-tag">set</span>
          <JsonTree value={body} depth={depth} />
        </span>
      )
    case '__bytes__':
      return <span className="chip chip-tag">{`bytes ${String(body).length} base64 chars`}</span>
    case '__map__': {
      const pairs = Array.isArray(body) ? (body as Json[][]) : []
      return (
        <span className="tagged">
          <span className="chip chip-tag">map</span>
          <div className="children">
            {pairs.map(([k, v], i) => (
              <div key={i} className="entry">
                <span className="key">
                  <JsonTree value={k} depth={depth + 1} />
                </span>
                <JsonTree value={v} depth={depth + 1} />
              </div>
            ))}
          </div>
        </span>
      )
    }
    case '__unrepresentable__':
      return (
        <span className="chip chip-warn" title={String(value.repr ?? '')}>
          {`unrepresentable ${String(body)}`}
        </span>
      )
    default:
      return <span className="chip chip-tag">{`${tag.replaceAll('_', '')} ${String(body)}`}</span>
  }
}

export function JsonTree({ value, depth = 0 }: { value: Json; depth?: number }) {
  if (value === null) return <span className="null">null</span>
  if (typeof value === 'string') return <LongString value={value} />
  if (typeof value === 'number' || typeof value === 'boolean') return <span className="num">{String(value)}</span>
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="null">[]</span>
    return (
      <details open={depth < 2}>
        <summary>{`list of ${value.length}`}</summary>
        <div className="children">
          {value.map((v, i) =>
            isMessage(v) ? (
              <MessageCard key={i} message={v} />
            ) : (
              <div key={i} className="entry">
                <span className="key">{i}</span>
                <JsonTree value={v} depth={depth + 1} />
              </div>
            ),
          )}
        </div>
      </details>
    )
  }
  if (isObj(value)) {
    if (isMessage(value)) return <MessageCard message={value} />
    if (tagOf(value)) return <Tagged value={value} depth={depth} />
    const entries = Object.entries(value) as [string, Json][]
    if (entries.length === 0) return <span className="null">{'{}'}</span>
    return (
      <details open={depth < 2}>
        <summary>{`${entries.length} keys`}</summary>
        <Entries entries={entries} depth={depth} />
      </details>
    )
  }
  return null
}
