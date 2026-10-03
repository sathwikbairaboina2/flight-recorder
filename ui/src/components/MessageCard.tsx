import type { Json } from '../lib/diff'
import type { Obj } from '../lib/tags'
import { JsonTree } from './JsonTree'

export function MessageCard({ message }: { message: Obj }) {
  const role = String(message.__lc_message__)
  const content = message.content as Json | undefined
  const calls = Array.isArray(message.tool_calls) ? (message.tool_calls as Obj[]) : []
  return (
    <div className="message" data-testid="message" data-role={role}>
      <div className="message-head">
        <span className="chip chip-source">{role}</span>
        {typeof message.id === 'string' ? <span className="msg-id">{message.id}</span> : null}
      </div>
      {typeof content === 'string' && content !== '' ? <div className="msg-content">{content}</div> : null}
      {Array.isArray(content) ? <JsonTree value={content} depth={2} /> : null}
      {calls.map((c, i) => (
        <div key={i} className="tool-call">
          <span className="chip chip-node">{String(c.name)}</span>
          <JsonTree value={(c.args ?? {}) as Json} depth={1} />
        </div>
      ))}
      {typeof message.tool_call_id === 'string' ? <div className="msg-id">{`tool_call_id ${message.tool_call_id}`}</div> : null}
    </div>
  )
}
