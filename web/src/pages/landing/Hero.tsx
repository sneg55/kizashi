import { Link } from 'react-router'
import { RunwayRail } from '../../components/RunwayRail'
import { formatCount, formatEin } from '../../lib/format'
import { REPO_URL } from '../../lib/site'
import { pickSubject } from '../../lib/subject'
import type { Report } from '../../lib/types'

const HERO =
  'A background agent that watches the public IRS record for the nonprofits you fund, and says nothing until one of them is about to lose its status.'

function SubjectCard({ report }: { report: Report }) {
  const subject = pickSubject(report)
  if (!subject) return null
  const daysLeft = report.surfaced.find((org) => org.ein === subject.ein)?.days_left ?? null

  return (
    <div className="card rotate-[-1.5deg] p-6 shadow-float sm:p-8" aria-label="Example organization on the revocation path">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <div className="min-w-0">
          <p className="m-0 font-display text-tiny font-medium [overflow-wrap:anywhere] text-ink">
            {subject.name}
          </p>
          <p className="m-0 mt-1 flex flex-wrap gap-x-3 text-micro text-muted">
            {subject.place ? <span>{subject.place}</span> : null}
            <span className="data">{formatEin(subject.ein)}</span>
          </p>
        </div>
        {daysLeft !== null ? (
          <p className="m-0 rounded-full bg-flag-wash px-3 py-1 font-display text-micro font-medium text-ink">
            {formatCount(daysLeft)} days left
          </p>
        ) : null}
      </div>
      <div className="mt-6">
        <RunwayRail
          lastFiledEnd={subject.lastFiledEnd}
          asOf={report.as_of}
          predictedRevocation={subject.predictedRevocation}
          animate
        />
      </div>
    </div>
  )
}

export function Hero({ report }: { report: Report | null }) {
  return (
    <div className="grid items-center gap-14 py-16 sm:py-24 lg:grid-cols-[1.1fr_0.9fr] lg:gap-20">
      <div>
        <h1 className="m-0 max-w-[22ch] font-display text-[clamp(2.25rem,3.9vw,3.5rem)] leading-[1.08] font-light tracking-[-0.035em] text-balance text-ink">
          {HERO}
        </h1>
        <p className="m-0 mt-8 max-w-[44ch] text-lead text-pretty text-muted">
          Three public IRS files, one date rule, and a ledger of every organization it chose not to
          mention.
        </p>
        <div className="mt-9 flex flex-wrap items-center gap-4">
          <Link to="/app" className="pill pill-primary">
            Open the live report
          </Link>
          <a href={REPO_URL} className="ghost-link text-base">
            View source ›
          </a>
        </div>
        {report ? (
          <p className="m-0 mt-10 flex flex-wrap gap-x-6 gap-y-1 text-micro text-muted">
            <span className="min-w-0 [overflow-wrap:anywhere]">{report.portfolio.name}</span>
            <span className="data">run {report.as_of}</span>
            <span className="data">
              {formatCount(report.summary.surface)} of {formatCount(report.portfolio.count)} surfaced
            </span>
          </p>
        ) : null}
      </div>
      {report ? (
        <div className="px-2 sm:px-6 lg:px-0">
          <SubjectCard report={report} />
        </div>
      ) : null}
    </div>
  )
}
