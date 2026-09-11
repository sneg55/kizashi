import { compareIso } from './dates'
import type { Report } from './types'

export interface RunwaySubject {
  ein: string
  name: string
  place: string | null
  lastFiledEnd: string | null
  predictedRevocation: string | null
  evidence: string[]
  surfaced: boolean
}

export function pickSubject(report: Report): RunwaySubject | null {
  const surfaced = [...report.surfaced].sort((a, b) =>
    compareIso(a.predicted_revocation, b.predicted_revocation),
  )
  const first = surfaced[0]
  if (first) {
    return {
      ein: first.ein,
      name: first.name,
      place: [first.city, first.state].filter(Boolean).join(', ') || null,
      lastFiledEnd: first.last_filed_end,
      predictedRevocation: first.predicted_revocation,
      evidence: first.evidence,
      surfaced: true,
    }
  }

  const candidates = report.ledger
    .filter((row) => row.last_filed_end !== null && row.predicted_revocation !== null)
    .sort((a, b) => compareIso(a.predicted_revocation, b.predicted_revocation))
  const next = candidates[0]
  if (!next) return null

  return {
    ein: next.ein,
    name: next.name,
    place: null,
    lastFiledEnd: next.last_filed_end,
    predictedRevocation: next.predicted_revocation,
    evidence: [],
    surfaced: false,
  }
}

export function quietCount(report: Report): number {
  return Math.max(report.portfolio.count - report.summary.surface, 0)
}
