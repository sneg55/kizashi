import { Link } from 'react-router'
import { BacktestPanel } from '../components/BacktestPanel'
import { GateFeed } from '../components/GateFeed'
import { LedgerExcerpt } from '../components/LedgerExcerpt'
import { RunwayRail } from '../components/RunwayRail'
import { Section } from '../components/Section'
import { SiteFooter } from '../components/SiteFooter'
import { TopBar } from '../components/TopBar'
import { formatCount, formatEin } from '../lib/format'
import { IRS_RULE_URL, REPO_URL } from '../lib/site'
import { pickSubject, quietCount } from '../lib/subject'
import type { Report } from '../lib/types'
import { useReport } from '../lib/use-report'

const HERO =
  'A background agent that watches the public IRS record for the nonprofits you fund, and says nothing until one of them is about to lose its status.'

const RULE_STATEMENTS = [
  'Every exempt organization owes an annual return or notice, due on the fifteenth day of the fifth month after its tax year ends.',
  'Miss three in a row and the exemption is revoked on the third due date, automatically.',
  'There is no hearing and no warning. The IRS posts the revocation months after it takes effect, which is why the date has to be computed rather than read.',
]

const BUILT_ON = [
  { name: 'Strands Agents SDK', role: 'the graph, the two agents, and the hook that owns the outbound call' },
  { name: 'Amazon Bedrock via the Mantle endpoint', role: 'the model that writes each brief from the record' },
  { name: 'Amazon Bedrock AgentCore Runtime', role: 'the monthly run, off a schedule, with nobody watching' },
]

function Hero({ report }: { report: Report | null }) {
  return (
    <div className="py-14 sm:py-20">
      <h1 className="m-0 max-w-[30ch] font-display text-[clamp(1.6rem,3.4vw,2.55rem)] leading-[1.2] font-normal tracking-[-0.02em] text-pretty text-ink">
        {HERO}
      </h1>
      <div className="mt-9 flex flex-wrap items-center gap-3">
        <Link
          to="/app"
          className="bg-ink px-4 py-2.5 text-tiny text-ground no-underline transition-opacity hover:opacity-85"
        >
          Open the live report
        </Link>
        <a
          href={REPO_URL}
          className="border border-rule-strong px-4 py-2.5 text-tiny text-ink no-underline transition-colors hover:border-ink"
        >
          View source
        </a>
      </div>
      {report ? (
        <p className="m-0 mt-7 flex flex-wrap gap-x-6 gap-y-1 text-micro text-ink-soft">
          <span>{report.portfolio.name}</span>
          <span className="data">run {report.as_of}</span>
          <span className="data">
            {formatCount(report.summary.surface)} of {formatCount(report.portfolio.count)} surfaced
          </span>
        </p>
      ) : null}
    </div>
  )
}

function LandingBody({ report }: { report: Report }) {
  const subject = pickSubject(report)
  const quiet = quietCount(report)
  const excerpt = report.ledger.filter((row) => row.class !== 'SURFACE').slice(0, 6)
  const gateEvents = [...report.gate_events].sort((a, b) =>
    a.decision === b.decision ? 0 : a.decision === 'allowed' ? 1 : -1,
  )

  return (
    <>
      <Section title="The rule">
        <div className="max-w-[62ch]">
          {RULE_STATEMENTS.map((statement, index) => (
            <p
              key={statement}
              className={`m-0 py-4 text-pretty ${index === 0 ? '' : 'border-t border-rule'} ${
                index === 1 ? 'text-ink' : 'text-ink-soft'
              }`}
            >
              {statement}
            </p>
          ))}
          <p className="m-0 border-t border-rule pt-4 text-tiny">
            <a href={IRS_RULE_URL} className="text-ink-soft hover:text-ink">
              Automatic revocation of exemption, irs.gov
            </a>
          </p>
        </div>
      </Section>

      <Section title="What it does">
        <div className="space-y-12">
          <div>
            <h3 className="m-0 font-display text-[1.35rem] leading-snug font-normal text-ink">
              It computes the date
            </h3>
            {subject ? (
              <div className="mt-5 max-w-[46rem]">
                <p className="m-0 flex flex-wrap items-baseline gap-x-3 text-tiny text-ink-soft">
                  <span className="text-ink">{subject.name}</span>
                  <span className="data">{formatEin(subject.ein)}</span>
                  {subject.place ? <span>{subject.place}</span> : null}
                </p>
                <div className="mt-5">
                  <RunwayRail
                    lastFiledEnd={subject.lastFiledEnd}
                    asOf={report.as_of}
                    predictedRevocation={subject.predictedRevocation}
                    animate
                  />
                </div>
                {subject.evidence.length > 0 ? (
                  <ol className="m-0 mt-7 list-none space-y-2 p-0">
                    {subject.evidence.map((line, index) => (
                      <li
                        key={line}
                        className={`text-tiny ${
                          index === subject.evidence.length - 1 ? 'text-ink' : 'text-ink-soft'
                        }`}
                      >
                        {line}
                      </li>
                    ))}
                  </ol>
                ) : null}
              </div>
            ) : (
              <p className="mt-4 max-w-[62ch] text-ink-soft">
                No organization in this run has a filing record to measure from.
              </p>
            )}
          </div>

          <div>
            <h3 className="m-0 font-display text-[1.35rem] leading-snug font-normal text-ink">
              It stays quiet
            </h3>
            <p className="mt-3 max-w-[62ch] text-ink-soft">
              {formatCount(quiet)} of {formatCount(report.portfolio.count)} organizations in this
              run produced nothing to send. Each one is written down with the reason, so the silence
              can be checked.
            </p>
            <div className="mt-5 max-w-[46rem]">
              <LedgerExcerpt rows={excerpt} />
            </div>
          </div>

          <div>
            <h3 className="m-0 font-display text-[1.35rem] leading-snug font-normal text-ink">
              It asks before it speaks
            </h3>
            <p className="mt-3 max-w-[62ch] text-ink-soft">
              The dispatcher can call one tool. A deterministic hook reads the classification before
              the call lands and cancels it when the record does not support an alert.
            </p>
            <div className="mt-5 max-w-[46rem]">
              <GateFeed events={gateEvents} limit={4} />
            </div>
          </div>
        </div>
      </Section>

      <Section title="The answer key">
        <p className="mt-0 mb-8 max-w-[62ch] text-ink-soft">
          The IRS publishes every revocation it has already made. Running the same formula backwards
          over that list scores it against an answer key nobody has to guess at.
        </p>
        <BacktestPanel backtest={report.backtest} />
      </Section>
    </>
  )
}

export function Landing() {
  const { state } = useReport()

  return (
    <div className="mx-auto max-w-[72rem] px-4 sm:px-8">
      <TopBar current="landing" />
      <main>
        <Hero report={state.status === 'ready' ? state.report : null} />

        {state.status === 'ready' ? <LandingBody report={state.report} /> : null}
        {state.status === 'loading' ? (
          <Section title="Current run">
            <p className="m-0 text-ink-soft">Reading the latest run.</p>
          </Section>
        ) : null}
        {state.status === 'error' ? (
          <Section title="Current run">
            <p className="m-0 max-w-[62ch] text-ink-soft">
              No run is readable from here. Start the API with{' '}
              <code className="data text-tiny text-ink">kizashi serve</code>, or build the site with
              a report at <code className="data text-tiny text-ink">/data/report.json</code>.
            </p>
          </Section>
        ) : null}

        <Section title="Built on">
          <dl className="m-0 max-w-[46rem]">
            {BUILT_ON.map((item) => (
              <div
                key={item.name}
                className="grid gap-x-8 gap-y-1 border-b border-rule py-4 sm:grid-cols-[19rem_1fr]"
              >
                <dt className="text-ink">{item.name}</dt>
                <dd className="m-0 text-tiny text-ink-soft">{item.role}</dd>
              </div>
            ))}
          </dl>
        </Section>
      </main>
      <SiteFooter />
    </div>
  )
}
