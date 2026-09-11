import { useState } from 'react'
import { dismissOrg } from '../lib/data'
import { formatCount, formatEin } from '../lib/format'
import { IS_STATIC } from '../lib/site'
import type { SurfacedOrg } from '../lib/types'
import { RunwayRail } from './RunwayRail'

type DismissState = 'idle' | 'pending' | 'done' | 'failed'

export function SurfacedCard({
  org,
  asOf,
  animate,
}: {
  org: SurfacedOrg
  asOf: string
  animate: boolean
}) {
  const [dismiss, setDismiss] = useState<DismissState>('idle')
  const place = [org.city, org.state].filter(Boolean).join(', ')
  const canDismiss = !IS_STATIC && org.predicted_revocation !== null

  async function onDismiss() {
    if (!org.predicted_revocation) return
    setDismiss('pending')
    try {
      await dismissOrg(org.ein, org.predicted_revocation)
      setDismiss('done')
    } catch {
      setDismiss('failed')
    }
  }

  return (
    <article className="border-t border-rule py-9 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2">
        <div>
          <h3 className="m-0 font-display text-[1.5rem] leading-tight font-normal text-ink">
            {org.name}
          </h3>
          <p className="m-0 mt-1 flex flex-wrap items-baseline gap-x-4 text-tiny text-ink-soft">
            {place ? <span>{place}</span> : null}
            <span className="data">EIN {formatEin(org.ein)}</span>
          </p>
        </div>
        {org.days_left !== null ? (
          <p className="m-0 text-tiny text-ink-soft">
            <span className="data text-[1.05rem] text-flag">{formatCount(org.days_left)}</span> days
            from the run date
          </p>
        ) : null}
      </div>

      <div className="mt-7">
        <RunwayRail
          lastFiledEnd={org.last_filed_end}
          asOf={asOf}
          predictedRevocation={org.predicted_revocation}
          animate={animate}
        />
      </div>

      {org.brief ? (
        <div className="mt-8 max-w-[64ch]">
          <p className="m-0 font-display text-[1.25rem] leading-snug text-pretty text-ink">
            {org.brief.headline}
          </p>
          <p className="m-0 mt-3 text-tiny text-ink-soft">{org.brief.what_happens_if_missed}</p>
          <p className="m-0 mt-2 text-tiny text-ink-soft">{org.brief.next_filing_needed}</p>
        </div>
      ) : (
        <ol className="m-0 mt-8 max-w-[64ch] list-none space-y-1.5 p-0">
          {org.evidence.map((line) => (
            <li key={line} className="text-tiny text-ink-soft">
              {line}
            </li>
          ))}
        </ol>
      )}

      <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3">
        {org.alert ? (
          <p className="data m-0 flex items-baseline gap-2 text-micro text-ink-soft">
            <span className="whitespace-nowrap text-ink">alert {org.alert.status}</span>
            <span>{org.alert.reason}</span>
          </p>
        ) : null}
        {canDismiss ? (
          <button
            type="button"
            onClick={onDismiss}
            disabled={dismiss === 'pending' || dismiss === 'done'}
            className="cursor-pointer border border-rule-strong px-3 py-1.5 text-micro text-ink-soft transition-colors hover:border-ink hover:text-ink disabled:cursor-default disabled:border-rule disabled:text-ink-soft"
          >
            {dismiss === 'done'
              ? 'Dismissed for this date'
              : dismiss === 'pending'
                ? 'Dismissing'
                : 'Dismiss'}
          </button>
        ) : null}
        {dismiss === 'failed' ? (
          <p className="m-0 text-micro text-ink">
            The dismiss did not reach the API. Check that the server is running and try again.
          </p>
        ) : null}
      </div>

      {org.outreach ? (
        <details className="group mt-6 border-t border-rule pt-4">
          <summary className="cursor-pointer list-none text-tiny text-ink-soft marker:content-[''] hover:text-ink">
            <span className="group-open:hidden">Read the drafted note</span>
            <span className="hidden group-open:inline">Hide the drafted note</span>
          </summary>
          <p className="m-0 mt-4 max-w-[64ch] text-tiny whitespace-pre-wrap text-ink">
            {org.outreach}
          </p>
        </details>
      ) : null}
    </article>
  )
}
