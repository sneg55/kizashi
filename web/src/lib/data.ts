import { IS_STATIC, PORTFOLIO_CSV } from './site'
import type { Report } from './types'

export const LIVE_ENDPOINT = '/api/runs/latest'
export const FIXTURE_ENDPOINT = '/data/report.json'

async function readJson(endpoint: string): Promise<Report> {
  const response = await fetch(endpoint)
  if (!response.ok) throw new Error(`${endpoint} responded ${response.status}`)
  return (await response.json()) as Report
}

export async function loadReport(): Promise<Report> {
  if (!IS_STATIC) {
    try {
      return await readJson(LIVE_ENDPOINT)
    } catch {
      return readJson(FIXTURE_ENDPOINT)
    }
  }
  return readJson(FIXTURE_ENDPOINT)
}

export async function runSweep(): Promise<Report> {
  const response = await fetch('/api/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ portfolio_csv: PORTFOLIO_CSV, with_model: true }),
  })
  if (!response.ok) throw new Error(`Sweep failed with status ${response.status}`)
  return (await response.json()) as Report
}

export async function dismissOrg(ein: string, predictedRevocation: string): Promise<void> {
  const response = await fetch(`/api/orgs/${ein}/dismiss`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ predicted_revocation: predictedRevocation }),
  })
  if (!response.ok) throw new Error(`Dismiss failed with status ${response.status}`)
}

export async function restoreOrg(ein: string, predictedRevocation: string): Promise<void> {
  const response = await fetch(`/api/orgs/${ein}/restore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ predicted_revocation: predictedRevocation }),
  })
  if (!response.ok) throw new Error(`Restore failed with status ${response.status}`)
}
