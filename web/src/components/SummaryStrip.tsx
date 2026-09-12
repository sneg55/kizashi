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
    <div className="card p-6 sm:p-8">
      <dl className="m-0 flex flex-wrap gap-x-10 gap-y-5">
        {shown.map((item) => (
          <div key={item.key} className="min-w-[4.5rem]">
            <dd
              className={`data m-0 font-display text-[2rem] leading-none font-light tracking-[-0.025em] ${
                item.key === 'surface' ? 'text-flag' : 'text-ink'
              }`}
            >
              {formatCount(summary[item.key])}
            </dd>
            <dt className="mt-2 text-micro text-muted">{item.label}</dt>
          </div>
        ))}
      </dl>
      <p className="m-0 mt-6 flex flex-wrap gap-x-7 gap-y-1 border-t border-rule pt-5 text-tiny text-muted">
        <span>
          <span className="data font-medium text-ink">{formatCount(summary.alerts_sent)}</span>{' '}
          alerts sent
        </span>
        <span>
          <span className="data font-medium text-ink">
            {formatCount(summary.alerts_suppressed)}
          </span>{' '}
          suppressed by the gate
        </span>
        {summary.reinstated > 0 ? (
          <span>
            <span className="data font-medium text-ink">{formatCount(summary.reinstated)}</span>{' '}
            reinstated after an earlier revocation, counted in the classes above
          </span>
        ) : null}
      </p>
    </div>
  )
}
