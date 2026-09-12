import { formatCount } from '../lib/format'
import type { Summary } from '../lib/types'

const CLASS_ORDER: { key: keyof Summary; label: string }[] = [
  { key: 'surface', label: 'surfaced' },
  { key: 'watch', label: 'watch' },
  { key: 'current', label: 'current' },
  { key: 'excluded', label: 'excluded' },
  { key: 'dead', label: 'dead' },
  { key: 'past_due', label: 'past due' },
  { key: 'never_filed', label: 'never filed' },
]

export function SummaryStrip({ summary }: { summary: Summary }) {
  const shown = CLASS_ORDER.filter((item) => item.key === 'surface' || summary[item.key] > 0)

  return (
    <div className="border-y border-rule py-5">
      <p className="m-0 flex flex-wrap gap-x-7 gap-y-2">
        {shown.map((item) => (
          <span
            key={item.key}
            className={`flex items-baseline gap-1.5 ${
              item.key === 'surface' ? 'text-flag' : 'text-ink'
            }`}
          >
            <span className="data text-[1.05rem]">{formatCount(summary[item.key])}</span>
            <span className={`text-tiny ${item.key === 'surface' ? 'text-flag' : 'text-ink-soft'}`}>
              {item.label}
            </span>
          </span>
        ))}
      </p>
      <p className="m-0 mt-3 flex flex-wrap gap-x-7 gap-y-1 text-tiny text-ink-soft">
        <span>
          <span className="data text-ink">{formatCount(summary.alerts_sent)}</span> alerts sent
        </span>
        <span>
          <span className="data text-ink">{formatCount(summary.alerts_suppressed)}</span> suppressed
          by the gate
        </span>
        {summary.reinstated > 0 ? (
          <span>
            <span className="data text-ink">{formatCount(summary.reinstated)}</span> reinstated after
            an earlier revocation, counted in the classes above
          </span>
        ) : null}
      </p>
    </div>
  )
}
