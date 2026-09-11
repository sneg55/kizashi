import { formatEin } from '../lib/format'
import type { GateEvent } from '../lib/types'

function isAllowed(decision: string): boolean {
  return decision.toLowerCase() === 'allowed'
}

export function GateFeed({ events, limit }: { events: GateEvent[]; limit?: number }) {
  if (events.length === 0) {
    return (
      <p className="max-w-[62ch] text-ink-soft">
        The gate logged nothing this run. It writes a row every time an agent reaches for{' '}
        <code className="data text-tiny text-ink">send_alert</code>, whether or not the call goes
        through.
      </p>
    )
  }

  const shown = limit ? events.slice(0, limit) : events

  return (
    <ul className="m-0 list-none p-0">
      {shown.map((event, index) => {
        const allowed = isAllowed(event.decision)
        return (
          <li
            key={`${event.ein}-${event.decision}-${index}`}
            className="grid grid-cols-[0.75rem_1fr] items-start gap-x-3 border-b border-rule py-3 last:border-b-0"
          >
            <span
              aria-hidden="true"
              className={`mt-[0.45rem] h-2 w-2 ${
                allowed ? 'bg-allow' : 'border border-ink-soft bg-transparent'
              }`}
            />
            <div className="min-w-0">
              <p className="data flex flex-wrap items-baseline gap-x-3 text-tiny">
                <span className={allowed ? 'text-allow' : 'text-ink-soft'}>{event.decision}</span>
                <span className="text-ink">{event.tool}</span>
                <span className="text-ink-soft">{formatEin(event.ein)}</span>
              </p>
              <p className="mt-0.5 text-tiny text-ink-soft">{event.reason}</p>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
