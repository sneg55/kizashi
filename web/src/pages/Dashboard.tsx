import { useState } from 'react'
import { BacktestPanel } from '../components/BacktestPanel'
import { GateFeed } from '../components/GateFeed'
import { LedgerTable } from '../components/LedgerTable'
import { Section } from '../components/Section'
import { SiteFooter } from '../components/SiteFooter'
import { SummaryStrip } from '../components/SummaryStrip'
import { SurfacedCard } from '../components/SurfacedCard'
import { TopBar } from '../components/TopBar'
import { runSweep } from '../lib/data'
import { formatCount } from '../lib/format'
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
    <div className="py-10">
      <div className="flex flex-wrap items-start justify-between gap-x-8 gap-y-5">
        <div className="min-w-0">
          <h1 className="m-0 font-display text-[clamp(1.75rem,3vw,2.25rem)] leading-tight font-normal tracking-[-0.015em] text-ink">
            {report.portfolio.name}
          </h1>
          <p className="data m-0 mt-2 text-micro text-ink-soft">{report.portfolio.source}</p>
        </div>
        {IS_STATIC ? null : (
          <div className="flex flex-col items-start gap-2">
            <button
              type="button"
              onClick={onSweep}
              disabled={sweep === 'running'}
              className="cursor-pointer bg-ink px-4 py-2.5 text-tiny text-ground transition-opacity hover:opacity-85 disabled:cursor-default disabled:opacity-60"
            >
              {sweep === 'running' ? 'Running the sweep' : 'Run sweep'}
            </button>
            {sweep === 'failed' ? (
              <p className="m-0 max-w-[28ch] text-micro text-ink">
                The sweep did not start. Check that the API is running on port 8000.
              </p>
            ) : null}
          </div>
        )}
      </div>

      <dl className="mt-8 flex flex-wrap gap-x-10 gap-y-4">
        <Meta label="Organizations">{formatCount(report.portfolio.count)}</Meta>
        <Meta label="Run date">{report.as_of}</Meta>
        <Meta label="Run">{report.run_id}</Meta>
        <Meta label="Model">
          {report.model ? `${report.model.model_id}, ${report.model.region}` : 'not used this run'}
        </Meta>
        {report.sources.map((source) => (
          <Meta key={source.name} label={source.name}>
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
      <dt className="text-micro text-ink-soft">{label}</dt>
      <dd className="data m-0 mt-0.5 truncate text-tiny text-ink">{children}</dd>
    </div>
  )
}

function Surfaced({ report }: { report: Report }) {
  if (report.surfaced.length === 0) {
    return (
      <div className="max-w-[62ch]">
        <p className="m-0 font-display text-[1.5rem] leading-snug text-balance text-ink">
          Nothing to send this month.
        </p>
        <p className="m-0 mt-3 text-ink-soft">
          No organization in this portfolio has missed two annual filings with a third due date
          still ahead of it. The ledger below records what every one of them did instead.
        </p>
      </div>
    )
  }

  return (
    <div>
      {report.surfaced.map((org, index) => (
        <SurfacedCard key={org.ein} org={org} asOf={report.as_of} animate={index === 0} />
      ))}
    </div>
  )
}

export function Dashboard() {
  const { state, replace } = useReport()

  return (
    <div className="mx-auto max-w-[72rem] px-4 sm:px-8">
      <TopBar current="app" />

      {state.status === 'loading' ? (
        <main className="py-20">
          <p className="m-0 text-ink-soft">Reading the latest run.</p>
        </main>
      ) : null}

      {state.status === 'error' ? (
        <main className="py-20">
          <p className="m-0 max-w-[62ch] font-display text-[1.5rem] leading-snug text-ink">
            No run is readable from here.
          </p>
          <p className="m-0 mt-3 max-w-[62ch] text-ink-soft">
            Start the API with <code className="data text-tiny text-ink">kizashi serve</code>, or
            export a report to <code className="data text-tiny text-ink">/data/report.json</code>{' '}
            and reload.
          </p>
        </main>
      ) : null}

      {state.status === 'ready' ? (
        <main>
          <RunHeader report={state.report} onReplace={replace} />
          <SummaryStrip summary={state.report.summary} />
          <Section title="Surfaced">
            <Surfaced report={state.report} />
          </Section>
          <Section title="Ledger">
            <p className="mt-0 mb-6 max-w-[62ch] text-ink-soft">
              Every organization in the portfolio, with the reason it produced nothing to send.
            </p>
            <LedgerTable rows={state.report.ledger} />
          </Section>
          <Section title="Gate">
            <p className="mt-0 mb-6 max-w-[62ch] text-ink-soft">
              Every attempt on the outbound tool, allowed or cancelled, with the reason the hook
              recorded.
            </p>
            <div className="max-w-[52rem]">
              <GateFeed events={state.report.gate_events} />
            </div>
          </Section>
          <Section title="Backtest">
            <BacktestPanel backtest={state.report.backtest} />
          </Section>
        </main>
      ) : null}

      <SiteFooter />
    </div>
  )
}
