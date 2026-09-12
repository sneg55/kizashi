import { BacktestPanel } from '../components/BacktestPanel'
import { Section } from '../components/Section'
import { SiteFooter } from '../components/SiteFooter'
import { TopBar } from '../components/TopBar'
import { useReport } from '../lib/use-report'
import { BuiltOn } from './landing/BuiltOn'
import { Hero } from './landing/Hero'
import { Rule } from './landing/Rule'
import { WhatItDoes } from './landing/WhatItDoes'

export function Landing() {
  const { state } = useReport()

  return (
    <>
      <TopBar current="landing" />
      <main className="mx-auto max-w-[75rem] px-5 sm:px-8">
        <Hero report={state.status === 'ready' ? state.report : null} />
        <Rule />
        {state.status === 'ready' ? (
          <>
            <WhatItDoes report={state.report} />
            <Section
              title="The answer key"
              align="center"
              lead="The IRS publishes every revocation it has already made. Running the same formula backwards over that list scores it against an answer key nobody has to guess at."
            >
              <BacktestPanel backtest={state.report.backtest} />
            </Section>
          </>
        ) : null}
        {state.status === 'loading' ? (
          <Section title="Current run">
            <p className="m-0 text-muted">Reading the latest run.</p>
          </Section>
        ) : null}
        {state.status === 'error' ? (
          <Section title="Current run">
            <p className="m-0 max-w-[62ch] text-muted">
              No run is readable from here. Start the API with <code>kizashi serve</code>, or build
              the site with a report at <code>/data/report.json</code>.
            </p>
          </Section>
        ) : null}
        <BuiltOn />
      </main>
      <SiteFooter />
    </>
  )
}
