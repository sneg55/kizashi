export type LedgerClass =
  | 'SURFACE'
  | 'WATCH'
  | 'CURRENT'
  | 'EXCLUDED'
  | 'DEAD'
  | 'REINSTATED'
  | 'PAST_DUE'
  | 'NEVER_FILED'

export interface PortfolioMeta {
  name: string
  source: string
  count: number
}

export interface SourceMeta {
  name: string
  url: string
  last_modified: string
  rows: number
}

export interface ModelMeta {
  provider: string
  model_id: string
  region: string
}

export interface Summary {
  surface: number
  watch: number
  current: number
  excluded: number
  dead: number
  reinstated: number
  never_filed: number
  past_due: number
  alerts_sent: number
  alerts_suppressed: number
}

export interface Brief {
  headline: string
  what_happens_if_missed: string
  next_filing_needed: string
}

export interface AlertOutcome {
  status: string
  reason: string
}

export interface SurfacedOrg {
  ein: string
  name: string
  city: string
  state: string
  last_filed_end: string | null
  last_filed_source: string | null
  unfiled_past_due: number | null
  predicted_revocation: string | null
  days_left: number | null
  evidence: string[]
  brief: Brief | null
  outreach: string | null
  alert: AlertOutcome | null
}

export interface LedgerRow {
  ein: string
  name: string
  class: LedgerClass
  reason: string
  last_filed_end: string | null
  unfiled_past_due: number | null
  predicted_revocation: string | null
  reinstated: boolean
  sources_used: string[]
}

export interface GateEvent {
  ein: string
  tool: string
  decision: string
  reason: string
}

export interface Backtest {
  window: string
  n: number
  exact: number
  exact_rate: number
  same_month: number
  same_month_rate: number
  histogram_months: Record<string, number>
  source_dates: Record<string, string>
}

export interface Report {
  run_id: string
  as_of: string
  portfolio: PortfolioMeta
  sources: SourceMeta[]
  model: ModelMeta | null
  summary: Summary
  surfaced: SurfacedOrg[]
  ledger: LedgerRow[]
  gate_events: GateEvent[]
  backtest: Backtest | null
}
