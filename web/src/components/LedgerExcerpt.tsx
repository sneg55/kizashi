import { classLabel, humanizeReason } from '../lib/format'
import type { LedgerRow } from '../lib/types'

export function LedgerExcerpt({ rows }: { rows: LedgerRow[] }) {
  if (rows.length === 0) {
    return <p className="text-muted">This run wrote no ledger rows.</p>
  }

  return (
    <ul className="m-0 list-none p-0">
      {rows.map((row) => (
        <li
          key={row.ein}
          className="flex flex-wrap items-baseline gap-x-5 gap-y-0.5 border-b border-rule py-3 last:border-b-0 sm:grid sm:grid-cols-[1fr_6rem_9rem]"
        >
          <span className="w-full truncate text-tiny text-ink sm:w-auto">{row.name}</span>
          <span className="data text-micro text-muted">{classLabel(row.class)}</span>
          <span className="data text-micro text-muted">{humanizeReason(row.reason)}</span>
        </li>
      ))}
    </ul>
  )
}
