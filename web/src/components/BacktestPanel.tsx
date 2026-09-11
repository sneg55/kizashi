import { formatCount, formatRate } from '../lib/format'
import type { Backtest } from '../lib/types'
import { Histogram } from './Histogram'
import { Field } from './Section'

export function BacktestPanel({ backtest }: { backtest: Backtest | null }) {
  if (!backtest) {
    return (
      <p className="max-w-[62ch] text-ink-soft">
        This run carries no backtest. Score the formula against the published revocation list with{' '}
        <code className="data text-tiny text-ink">kizashi backtest</code> and the number appears
        here.
      </p>
    )
  }

  const exactRate = formatRate(backtest.exact, backtest.n)
  const sameMonthRate = formatRate(backtest.same_month, backtest.n)

  return (
    <div>
      {exactRate ? (
        <p className="max-w-[26ch] font-display text-[2rem] leading-[1.15] font-normal tracking-[-0.015em] text-balance text-ink">
          <span className="data text-[1.9rem] tracking-[-0.02em]">{exactRate}</span> of revocations
          landed on the date the formula predicted.
        </p>
      ) : (
        <p className="max-w-[46ch] font-display text-[1.6rem] leading-[1.25] text-balance text-ink">
          No revocation in this window joined to a filing record, so there is nothing to score yet.
        </p>
      )}

      <dl className="mt-8 max-w-[44rem]">
        <Field label="Revocations scored">{formatCount(backtest.n)}</Field>
        <Field label="Exact date">
          {formatCount(backtest.exact)}
          {exactRate ? ` (${exactRate})` : ''}
        </Field>
        <Field label="Same month">
          {formatCount(backtest.same_month)}
          {sameMonthRate ? ` (${sameMonthRate})` : ''}
        </Field>
        <Field label="Window">
          <span className="font-sans">{backtest.window}</span>
        </Field>
        {Object.entries(backtest.source_dates).map(([source, date]) => (
          <Field key={source} label={`Source file, ${source}`}>
            {date}
          </Field>
        ))}
      </dl>

      {backtest.n > 0 ? (
        <div className="mt-10 max-w-[44rem]">
          <Histogram histogram={backtest.histogram_months} />
        </div>
      ) : null}
    </div>
  )
}
