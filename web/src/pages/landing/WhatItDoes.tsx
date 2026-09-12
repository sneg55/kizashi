import { Link } from 'react-router'
import { GateFeed } from '../../components/GateFeed'
import { LedgerExcerpt } from '../../components/LedgerExcerpt'
import { Section } from '../../components/Section'
import { formatCount } from '../../lib/format'
import { pickSubject, quietCount } from '../../lib/subject'
import type { Report } from '../../lib/types'

function Card({
  title,
  body,
  children,
  className = '',
}: {
  title: string
  body: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={`card flex flex-col p-6 sm:p-8 ${className}`}>
      <h3 className="m-0 font-display text-[1.5rem] leading-[1.25] font-medium tracking-[-0.02em] text-ink">
        {title}
      </h3>
      <p className="m-0 mt-3 max-w-[52ch] text-pretty text-ink-soft">{body}</p>
      <div className="mt-6 flex-1">{children}</div>
    </div>
  )
}

export function WhatItDoes({ report }: { report: Report }) {
  const subject = pickSubject(report)
  const quiet = quietCount(report)
  const excerpt = report.ledger.filter((row) => row.class !== 'SURFACE').slice(0, 6)
  const gateEvents = [...report.gate_events].sort((a, b) =>
    a.decision === b.decision ? 0 : a.decision === 'allowed' ? 1 : -1,
  )

  return (
    <Section
      title="What it does"
      align="center"
      lead="Three steps, and only the last one is allowed to speak."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="It computes the date"
          body="For every organization it finds the last return on record, projects the next three due dates, and counts how many have already passed."
          className="lg:col-span-2"
        >
          {subject && subject.evidence.length > 0 ? (
            <ol className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2">
              {subject.evidence.map((line, index) => (
                <li
                  key={line}
                  className={`rounded-[12px] px-4 py-3 text-tiny ${
                    index === subject.evidence.length - 1
                      ? 'bg-flag-wash text-ink'
                      : 'bg-ground text-ink-soft'
                  }`}
                >
                  {line}
                </li>
              ))}
            </ol>
          ) : (
            <p className="m-0 text-tiny text-muted">
              No organization in this run has a filing record to measure from.
            </p>
          )}
        </Card>

        <Card
          title="It stays quiet"
          body={`${formatCount(quiet)} of ${formatCount(report.portfolio.count)} organizations in this run produced nothing to send. Each one is written down with the reason, so the silence can be checked.`}
        >
          <LedgerExcerpt rows={excerpt} />
          <p className="m-0 mt-5">
            <Link to="/app#ledger" className="ghost-link text-tiny">
              Full ledger, {formatCount(report.portfolio.count)} rows ›
            </Link>
          </p>
        </Card>

        <Card
          title="It asks before it speaks"
          body="The dispatcher can call one tool. A deterministic hook reads the classification before the call lands and cancels it when the record does not support an alert."
        >
          <GateFeed events={gateEvents} limit={4} />
          <p className="m-0 mt-5">
            <Link to="/app#gate" className="ghost-link text-tiny">
              Every gate event, {formatCount(report.gate_events.length)} in this run ›
            </Link>
          </p>
        </Card>
      </div>
    </Section>
  )
}
