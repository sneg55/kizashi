import { formatCount, formatRate, sourceLabel } from '../lib/format'
import type { Backtest } from '../lib/types'
import { Histogram } from './Histogram'
import { Field } from './Section'

export function BacktestPanel({ backtest }: { backtest: Backtest | null }) {
  if (!backtest) {
    return (
      <p className="max-w-[62ch] text-muted">
        This run carries no backtest. Score the formula against the published revocation list with{' '}
        <code>kizashi backtest</code> and the number appears here.
      </p>
    )
  }

  const exactRate = formatRate(backtest.exact, backtest.n)

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <div className="card p-6 sm:p-8">
        {exactRate ? (
          <>
            <p className="data m-0 font-display text-[clamp(3rem,7vw,4.5rem)] leading-none font-light tracking-[-0.05em] text-accent">
              {exactRate}
            </p>
            <p className="m-0 mt-4 max-w-[26ch] font-display text-lead leading-snug font-normal text-balance text-ink">
              of revocations landed on the date the formula predicted.
            </p>
          </>
        ) : (
          <p className="m-0 max-w-[30ch] font-display text-lead leading-snug text-balance text-ink">
            No revocation in this window joined to a filing record, so there is nothing to score
            yet.
          </p>
        )}

        <dl className="m-0 mt-8">
          <Field label="Revocations scored">{formatCount(backtest.n)}</Field>
          <Field label="Exact date">
            {formatCount(backtest.exact)}
            {exactRate ? ` (${exactRate})` : ''}
          </Field>
          <Field label="Window">
            <span className="font-sans">{backtest.window}</span>
          </Field>
          {Object.entries(backtest.source_dates).map(([source, date]) => (
            <Field key={source} label={`${sourceLabel(source)}, dated`}>
              {date}
            </Field>
          ))}
        </dl>
      </div>

      {backtest.n > 0 ? (
        <div className="card p-6 sm:p-8">
          <Histogram histogram={backtest.histogram_months} />
        </div>
      ) : null}
    </div>
  )
}
