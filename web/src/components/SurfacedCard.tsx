import { useId, useState } from 'react'
import { dismissOrg } from '../lib/data'
import { formatCount, formatEin } from '../lib/format'
import { IS_STATIC } from '../lib/site'
import type { SurfacedOrg } from '../lib/types'
import { RunwayRail } from './RunwayRail'

type DismissState = 'idle' | 'pending' | 'done' | 'failed'

const BRIEF_SOURCE_LABEL: Record<string, string> = {
  model: 'brief written by the model from the record',
  fallback: 'brief built from the record without the model',
}

function Panel({ org, asOf }: { org: SurfacedOrg; asOf: string }) {
  const [dismiss, setDismiss] = useState<DismissState>('idle')
  const canDismiss = !IS_STATIC && org.predicted_revocation !== null
  const briefSource = org.brief_source ? BRIEF_SOURCE_LABEL[org.brief_source] : null

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
    <div className="pt-6 pb-8">
      <RunwayRail
        lastFiledEnd={org.last_filed_end}
        asOf={asOf}
        predictedRevocation={org.predicted_revocation}
        animate
      />

      {org.brief ? (
        <div className="mt-8 max-w-[64ch]">
          <p className="m-0 font-display text-[1.25rem] leading-snug text-pretty text-ink">
            {org.brief.headline}
          </p>
          <p className="m-0 mt-3 text-tiny text-ink-soft">{org.brief.what_happens_if_missed}</p>
          <p className="m-0 mt-2 text-tiny text-ink-soft">{org.brief.next_filing_needed}</p>
          {briefSource ? (
            <p className="data m-0 mt-3 text-micro text-ink-soft">{briefSource}</p>
          ) : null}
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
          <p className="data m-0 flex flex-wrap items-baseline gap-x-2 text-micro text-ink-soft">
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
    </div>
  )
}

export function SurfacedCard({
  org,
  asOf,
  defaultOpen = false,
}: {
  org: SurfacedOrg
  asOf: string
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const panelId = useId()
  const place = [org.city, org.state].filter(Boolean).join(', ')

  return (
    <div className="border-b border-rule last:border-b-0">
      <h3 className="m-0">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls={panelId}
          className="grid w-full cursor-pointer grid-cols-[1rem_1fr] items-baseline gap-x-3 py-3.5 text-left sm:grid-cols-[1rem_1fr_auto_7rem] sm:gap-x-6"
        >
          <span className="data text-tiny text-ink-soft" aria-hidden="true">
            {open ? '−' : '+'}
          </span>
          <span className="min-w-0">
            <span className="block text-tiny [overflow-wrap:anywhere] text-ink">{org.name}</span>
            <span className="mt-0.5 flex flex-wrap items-baseline gap-x-3 text-micro text-ink-soft">
              {place ? <span>{place}</span> : null}
              <span className="data">{formatEin(org.ein)}</span>
            </span>
          </span>
          <span className="data col-start-2 text-micro text-ink-soft sm:col-start-3 sm:text-right">
            {org.days_left === null ? 'no date' : `${formatCount(org.days_left)} days`}
          </span>
          <span className="data col-start-2 text-tiny whitespace-nowrap text-flag sm:col-start-4 sm:text-right">
            {org.predicted_revocation ?? 'none'}
          </span>
        </button>
      </h3>
      <div id={panelId} hidden={!open}>
        {open ? <Panel org={org} asOf={asOf} /> : null}
      </div>
    </div>
  )
}
