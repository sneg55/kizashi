import { formatEin } from '../lib/format'
import type { GateEvent } from '../lib/types'

function isAllowed(decision: string): boolean {
  return decision.toLowerCase() === 'allowed'
}

function isHeld(decision: string): boolean {
  return decision.toLowerCase() === 'held'
}

function dotClass(decision: string): string {
  if (isAllowed(decision)) return 'bg-ink'
  if (isHeld(decision)) return 'border-[1.5px] border-accent bg-accent-wash'
  return 'border-[1.5px] border-flag bg-flag-wash'
}

export function GateFeed({ events, limit }: { events: GateEvent[]; limit?: number }) {
  if (events.length === 0) {
    return (
      <p className="max-w-[62ch] text-muted">
        The gate logged nothing this run. It writes a row every time an agent reaches for{' '}
        <code>send_alert</code>, whether or not the call goes through.
      </p>
    )
  }

  const shown = limit ? events.slice(0, limit) : events

  return (
    <ul className="m-0 list-none p-0">
      {shown.map((event, index) => {
        return (
          <li
            key={`${event.ein}-${event.decision}-${index}`}
            className="grid grid-cols-[0.875rem_1fr] items-start gap-x-3 border-b border-rule py-3.5 last:border-b-0"
          >
            <span
              aria-hidden="true"
              className={`mt-[0.4rem] h-2.5 w-2.5 rounded-full ${dotClass(event.decision)}`}
            />
            <div className="min-w-0">
              <p className="data m-0 flex flex-wrap items-baseline gap-x-3 text-tiny">
                <span className="font-medium text-ink">{event.decision}</span>
                <span className="text-muted">{event.tool}</span>
                <span className="text-muted">{formatEin(event.ein)}</span>
                {event.delivery_id ? (
                  <span className="text-muted">
                    {event.channel}, {event.delivery_id}
                  </span>
                ) : null}
              </p>
              <p className="m-0 mt-0.5 text-tiny text-ink-soft">{event.reason}</p>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
