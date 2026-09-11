import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { expect, test, vi } from 'vitest'
import { FIXTURE_ENDPOINT, LIVE_ENDPOINT, loadReport } from './data'

const fixturePath = fileURLToPath(new URL('../../public/data/report.json', import.meta.url))
const fixture = readFileSync(fixturePath, 'utf8')

test('loadReport falls back to the bundled fixture when the api is unreachable', async () => {
  const requested: string[] = []
  vi.stubGlobal('fetch', (input: string) => {
    requested.push(input)
    if (input === LIVE_ENDPOINT) return Promise.reject(new Error('connection refused'))
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(fixture)) })
  })

  const report = await loadReport()

  expect(requested).toEqual([LIVE_ENDPOINT, FIXTURE_ENDPOINT])
  expect(report.run_id).toBe(JSON.parse(fixture).run_id)
  expect(report.ledger.length).toBe(JSON.parse(fixture).ledger.length)
  vi.unstubAllGlobals()
})

test('loadReport prefers the live run when the api answers', async () => {
  const live = { ...JSON.parse(fixture), run_id: 'live-run' }
  vi.stubGlobal('fetch', () =>
    Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(live) }),
  )

  const report = await loadReport()

  expect(report.run_id).toBe('live-run')
  vi.unstubAllGlobals()
})
