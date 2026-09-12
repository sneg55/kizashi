import { classLabel, formatCount, formatRate } from '../lib/format'
import type { SilenceScore } from '../lib/types'
import { Field } from './Section'

const CLASS_ORDER = ['SURFACE', 'WATCH', 'CURRENT', 'PAST_DUE', 'NEVER_FILED', 'EXCLUDED', 'DEAD']

function monthLabel(iso: string): string {
  const year = Number(iso.slice(0, 4))
  const month = Number(iso.slice(5, 7))
  return new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

export function SilencePanel({ silence }: { silence: SilenceScore | null | undefined }) {
  if (!silence) {
    return (
      <p className="max-w-[62ch] text-muted">
        This run carries no silence score. Rerun the classifier at a past date with{' '}
        <code>kizashi score --as-of</code> and the outcome by class appears here.
      </p>
    )
  }

  const precision = formatRate(silence.tp, silence.positives)
  const rows = CLASS_ORDER.flatMap((cls) => {
    const bucket = silence.by_class[cls]
    return bucket ? [{ cls, total: bucket.total, revoked: bucket.revoked }] : []
  })

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <div className="card p-6 sm:p-8">
        <p className="data m-0 font-display text-[clamp(3rem,7vw,4.5rem)] leading-none font-light tracking-[-0.05em] text-accent">
          {precision ?? 'n/a'}
        </p>
        <p className="m-0 mt-4 max-w-[30ch] font-display text-lead leading-snug font-normal text-balance text-ink">
          of the organizations it would have surfaced in {monthLabel(silence.as_of)} were revoked
          by the IRS in the two years since.
        </p>
        <dl className="m-0 mt-8">
          <Field label="Surfaced then">{formatCount(silence.positives)}</Field>
          <Field label="Revoked since">{formatCount(silence.tp)}</Field>
          <Field label="Still standing">{formatCount(silence.fp)}</Field>
          <Field label="Revocations since, all classes">{formatCount(silence.truth)}</Field>
          <Field label="Caught by surfacing">{formatRate(silence.tp, silence.truth) ?? 'n/a'}</Field>
          <Field label="Refiled after revocation, invisible in the latest-only file">
            {formatCount(silence.refiled_after_revocation)}
          </Field>
          <Field label="Organizations classified">{formatCount(silence.universe)}</Field>
          <Field label="Revocation list dated">{silence.list_date}</Field>
        </dl>
      </div>

      <div className="card p-6 sm:p-8">
        <p className="m-0 text-micro text-muted">
          Outcome by class, classified as of {silence.as_of} against revocations posted through{' '}
          {silence.list_date}
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-rule-strong font-display text-micro font-medium text-muted">
                <th scope="col" className="py-2.5 pr-4 font-medium">
                  Class then
                </th>
                <th scope="col" className="py-2.5 pr-4 text-right font-medium">
                  Organizations
                </th>
                <th scope="col" className="py-2.5 pr-4 text-right font-medium">
                  Revoked since
                </th>
                <th scope="col" className="py-2.5 text-right font-medium">
                  Share
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.cls} className="border-b border-rule">
                  <td
                    className={`data py-2.5 pr-4 text-tiny font-medium ${row.cls === 'SURFACE' ? 'text-flag' : 'text-ink'}`}
                  >
                    {classLabel(row.cls)}
                  </td>
                  <td className="data py-2.5 pr-4 text-right text-tiny text-ink-soft">
                    {formatCount(row.total)}
                  </td>
                  <td className="data py-2.5 pr-4 text-right text-tiny text-ink">
                    {formatCount(row.revoked)}
                  </td>
                  <td className="data py-2.5 text-right text-tiny text-ink-soft">
                    {formatRate(row.revoked, row.total) ?? 'n/a'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="m-0 mt-5 max-w-[62ch] text-micro text-muted">
          Precision runs high because an organization that filed since would not look delinquent in
          today's latest-only file, and recall is conditional on the organization still being in
          the Business Master File. Watch and current rows revoked since had not yet missed two
          returns when this was scored.
        </p>
      </div>
    </div>
  )
}
