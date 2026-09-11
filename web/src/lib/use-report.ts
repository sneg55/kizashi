import { useEffect, useState } from 'react'
import { loadReport } from './data'
import type { Report } from './types'

export type ReportState =
  | { status: 'loading' }
  | { status: 'ready'; report: Report }
  | { status: 'error'; message: string }

export function useReport(): {
  state: ReportState
  replace: (report: Report) => void
} {
  const [state, setState] = useState<ReportState>({ status: 'loading' })

  useEffect(() => {
    let active = true
    loadReport()
      .then((report) => {
        if (active) setState({ status: 'ready', report })
      })
      .catch((cause: unknown) => {
        if (!active) return
        setState({
          status: 'error',
          message: cause instanceof Error ? cause.message : 'The report could not be read.',
        })
      })
    return () => {
      active = false
    }
  }, [])

  return {
    state,
    replace: (report: Report) => setState({ status: 'ready', report }),
  }
}
