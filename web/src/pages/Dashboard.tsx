import { useEffect, useState } from 'react'
import { useLocation } from 'react-router'
import { BacktestPanel } from '../components/BacktestPanel'
import { GateFeed } from '../components/GateFeed'
import { LedgerTable } from '../components/LedgerTable'
import { Section } from '../components/Section'
import { SilencePanel } from '../components/SilencePanel'
import { SiteFooter } from '../components/SiteFooter'
import { SummaryStrip } from '../components/SummaryStrip'
import { SurfacedCard } from '../components/SurfacedCard'
import { TopBar } from '../components/TopBar'
import { runSweep } from '../lib/data'
import { compareIso } from '../lib/dates'
import { formatCount, sourceLabel } from '../lib/format'
import { IS_STATIC } from '../lib/site'
import type { Report } from '../lib/types'
import { useReport } from '../lib/use-report'

type SweepState = 'idle' | 'running' | 'failed'

function RunHeader({
  report,
  onReplace,
}: {
  report: Report
  onReplace: (next: Report) => void
}) {
  const [sweep, setSweep] = useState<SweepState>('idle')

  async function onSweep() {
    setSweep('running')
    try {
      onReplace(await runSweep())
      setSweep('idle')
    } catch {
      setSweep('failed')
    }
  }

  return (
    <div className="py-14 sm:py-20">
      <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-6">
        <div className="min-w-0">
          <p className="m-0 text-micro text-muted">
            portfolio <span className="data text-ink-soft">{report.portfolio.source}</span>
          </p>
          <h1 className="m-0 mt-3 font-display text-[clamp(2.25rem,5vw,3.5rem)] leading-[1.05] font-light tracking-[-0.035em] [overflow-wrap:anywhere] text-balance text-ink">
            {report.portfolio.name}
          </h1>
        </div>
        {IS_STATIC ? null : (
          <div className="flex flex-col items-start gap-3 sm:items-end">
            <button
              type="button"
              onClick={onSweep}
              disabled={sweep === 'running'}
              className="pill pill-primary disabled:cursor-default disabled:opacity-60"
            >
              {sweep === 'running' ? 'Running the sweep' : 'Run sweep'}
            </button>
            {sweep === 'running' ? (
              <p className="m-0 max-w-[34ch] text-micro text-muted sm:text-right">
                Classifying {formatCount(report.portfolio.count)} organizations, writing briefs with
                the model and dispatching through the gate. The page updates when the run finishes.
              </p>
            ) : null}
            {sweep === 'failed' ? (
              <p className="m-0 max-w-[30ch] text-micro text-ink sm:text-right">
                The sweep did not start. Check that the API is running on port 8000.
              </p>
            ) : null}
          </div>
        )}
      </div>

      <dl className="m-0 mt-10 flex flex-wrap gap-x-10 gap-y-5 border-t border-rule pt-6">
        <Meta label="Organizations">{formatCount(report.portfolio.count)}</Meta>
        <Meta label="Run date">{report.as_of}</Meta>
        <Meta label="Run">{report.run_id}</Meta>
        <Meta label="Model">
          {report.model ? `${report.model.model_id}, ${report.model.region}` : 'not used this run'}
        </Meta>
        {report.sources.map((source) => (
          <Meta key={source.name} label={`${sourceLabel(source.name)}, dated`}>
            {source.last_modified}
          </Meta>
        ))}
      </dl>
    </div>
  )
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-micro text-muted">{label}</dt>
      <dd className="data m-0 mt-1 text-tiny font-medium [overflow-wrap:anywhere] text-ink">{children}</dd>
    </div>
  )
}

function Surfaced({ report }: { report: Report }) {
  if (report.surfaced.length === 0) {
    return (
      <div className="card max-w-[62ch] p-8">
        <p className="m-0 font-display text-[1.5rem] leading-snug font-light text-balance text-ink">
          Nothing to send this month.
        </p>
        <p className="m-0 mt-3 text-muted">
          No organization in this portfolio has missed two annual filings with a third due date
          still ahead of it. The ledger below records what every one of them did instead.
        </p>
      </div>
    )
  }

  const ordered = [...report.surfaced].sort(
    (a, b) =>
      compareIso(a.predicted_revocation, b.predicted_revocation) ||
      (a.days_left ?? Number.MAX_SAFE_INTEGER) - (b.days_left ?? Number.MAX_SAFE_INTEGER) ||
      a.name.localeCompare(b.name),
  )

  return (
    <div key={report.run_id} className="card overflow-hidden">
      {ordered.map((org, index) => (
        <SurfacedCard key={org.ein} org={org} asOf={report.as_of} defaultOpen={index === 0} />
      ))}
    </div>
  )
}

export function Dashboard() {
  const { state, replace } = useReport()
  const { hash } = useLocation()

  useEffect(() => {
    if (state.status !== 'ready' || !hash) return
    document.getElementById(hash.slice(1))?.scrollIntoView()
  }, [state.status, hash])

  return (
    <>
      <TopBar current="app" />
      <main className="mx-auto max-w-[75rem] px-5 sm:px-8">
        {state.status === 'loading' ? (
          <p className="m-0 py-20 text-muted">Reading the latest run.</p>
        ) : null}

        {state.status === 'error' ? (
          <div className="py-20">
            <p className="m-0 max-w-[62ch] font-display text-[1.5rem] leading-snug font-light text-ink">
              No run is readable from here.
            </p>
            <p className="m-0 mt-3 max-w-[62ch] text-muted">
              Start the API with <code>kizashi serve</code>, or export a report to{' '}
              <code>/data/report.json</code> and reload.
            </p>
          </div>
        ) : null}

        {state.status === 'ready' ? (
          <>
            <RunHeader report={state.report} onReplace={replace} />
            <SummaryStrip summary={state.report.summary} />
            <Section title="Surfaced" count={state.report.surfaced.length}>
              <Surfaced report={state.report} />
            </Section>
            <Section
              title="Ledger"
              id="ledger"
              lead="Every organization in the portfolio, with the reason it produced nothing to send."
            >
              <LedgerTable rows={state.report.ledger} />
            </Section>
            <Section
              title="Gate"
              id="gate"
              lead="Every attempt on the outbound tool, allowed or cancelled, with the reason the hook recorded."
            >
              <div className="card max-w-[52rem] px-6 py-2 sm:px-8">
                <GateFeed events={state.report.gate_events} />
              </div>
            </Section>
            <Section title="Backtest" id="backtest">
              <BacktestPanel backtest={state.report.backtest} />
            </Section>
            <Section
              title="Scoring the silence"
              id="silence"
              lead="The classifier rerun at a date two years back, with every later revocation hidden from it, against what the IRS has posted since."
            >
              <SilencePanel silence={state.report.silence} />
            </Section>
          </>
        ) : null}
      </main>
      <SiteFooter />
    </>
  )
}
