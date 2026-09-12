import { useMemo, useState } from 'react'
import { compareIso } from '../lib/dates'
import { classLabel, formatCount, formatEin, humanizeReason, normalizeSearch } from '../lib/format'
import { Chip, Toggle } from './LedgerControls'
import type { LedgerClass, LedgerRow } from '../lib/types'

const PAGE_SIZE = 100

type Sort = 'record' | 'soonest' | 'latest'

function countBy<T extends string>(rows: LedgerRow[], key: (row: LedgerRow) => T): Map<T, number> {
  const counts = new Map<T, number>()
  for (const row of rows) {
    const value = key(row)
    counts.set(value, (counts.get(value) ?? 0) + 1)
  }
  return counts
}

export function LedgerTable({ rows }: { rows: LedgerRow[] }) {
  const [query, setQuery] = useState('')
  const [selectedClass, setSelectedClass] = useState<LedgerClass | 'all'>('all')
  const [selectedReason, setSelectedReason] = useState<string | 'all'>('all')
  const [sort, setSort] = useState<Sort>('record')
  const [page, setPage] = useState(0)

  const classCounts = useMemo(() => countBy(rows, (row) => row.class), [rows])

  const byClass = useMemo(
    () => (selectedClass === 'all' ? rows : rows.filter((row) => row.class === selectedClass)),
    [rows, selectedClass],
  )

  const reasonCounts = useMemo(() => countBy(byClass, (row) => row.reason), [byClass])

  const filtered = useMemo(() => {
    const needle = normalizeSearch(query)
    const matched = byClass.filter((row) => {
      if (selectedReason !== 'all' && row.reason !== selectedReason) return false
      if (!needle) return true
      return (
        normalizeSearch(row.name).includes(needle) || normalizeSearch(row.ein).includes(needle)
      )
    })
    if (sort === 'record') return matched
    const direction = sort === 'soonest' ? 1 : -1
    return [...matched].sort(
      (a, b) => direction * compareIso(a.predicted_revocation, b.predicted_revocation),
    )
  }, [byClass, query, selectedReason, sort])

  const pageCount = Math.max(Math.ceil(filtered.length / PAGE_SIZE), 1)
  const current = Math.min(page, pageCount - 1)
  const visible = filtered.slice(current * PAGE_SIZE, current * PAGE_SIZE + PAGE_SIZE)

  function reset<T>(setter: (value: T) => void, value: T) {
    setter(value)
    setPage(0)
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <label className="flex-1 basis-56">
          <span className="sr-only">Search the ledger by name or EIN</span>
          <input
            type="search"
            value={query}
            onChange={(event) => reset(setQuery, event.target.value)}
            placeholder="Search by name or EIN"
            className="w-full border border-rule bg-transparent px-3 py-1.5 text-tiny text-ink placeholder:text-ink-soft focus:border-rule-strong"
          />
        </label>
        <div className="flex items-center gap-2">
          <span className="text-micro text-ink-soft">Revocation date</span>
          <Toggle
            active={sort === 'soonest'}
            label="soonest first"
            onClick={() => setSort(sort === 'soonest' ? 'record' : 'soonest')}
          />
          <Toggle
            active={sort === 'latest'}
            label="latest first"
            onClick={() => setSort(sort === 'latest' ? 'record' : 'latest')}
          />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Chip
          active={selectedClass === 'all'}
          label="every class"
          count={rows.length}
          onClick={() => {
            reset(setSelectedClass, 'all')
            setSelectedReason('all')
          }}
        />
        {[...classCounts.entries()]
          .sort((a, b) => b[1] - a[1])
          .map(([value, count]) => (
            <Chip
              key={value}
              active={selectedClass === value}
              label={classLabel(value)}
              count={count}
              accent={value === 'SURFACE'}
              onClick={() => {
                reset(setSelectedClass, value)
                setSelectedReason('all')
              }}
            />
          ))}
      </div>

      <div className="mt-2 flex flex-wrap gap-2">
        <Chip
          active={selectedReason === 'all'}
          label="every reason"
          count={byClass.length}
          onClick={() => reset(setSelectedReason, 'all')}
        />
        {[...reasonCounts.entries()]
          .sort((a, b) => b[1] - a[1])
          .map(([value, count]) => (
            <Chip
              key={value}
              active={selectedReason === value}
              label={humanizeReason(value)}
              count={count}
              onClick={() => reset(setSelectedReason, value)}
            />
          ))}
      </div>

      {filtered.length === 0 ? (
        <p className="mt-8 text-ink-soft">
          No row matches that filter. Clear the search or pick another class.
        </p>
      ) : (
        <div className="mt-7 overflow-x-auto">
          <table className="w-full border-collapse text-left sm:min-w-[46rem]">
            <thead>
              <tr className="border-b border-rule-strong text-micro text-ink-soft">
                <th scope="col" className="py-2 pr-4 font-medium">
                  Organization
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  Class
                </th>
                <th scope="col" className="hidden py-2 pr-4 font-medium sm:table-cell">
                  Reason
                </th>
                <th scope="col" className="hidden py-2 pr-4 font-medium sm:table-cell">
                  Last filed
                </th>
                <th scope="col" className="hidden py-2 pr-4 text-right font-medium sm:table-cell">
                  Returns past due
                </th>
                <th
                  scope="col"
                  className="hidden py-2 font-medium sm:table-cell"
                  aria-sort={
                    sort === 'soonest' ? 'ascending' : sort === 'latest' ? 'descending' : 'none'
                  }
                >
                  Revocation date
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.ein} className="border-b border-rule align-baseline">
                  <td className="py-2 pr-4">
                    <span className="text-tiny text-ink">{row.name}</span>{' '}
                    <span className="data ml-2 text-micro whitespace-nowrap text-ink-soft">
                      {formatEin(row.ein)}
                    </span>
                    {row.reinstated ? (
                      <>
                        {' '}
                        <span className="data ml-2 text-micro text-ink-soft">reinstated</span>
                      </>
                    ) : null}
                    <span className="data block text-micro text-ink-soft sm:hidden">
                      {humanizeReason(row.reason)}
                      {row.predicted_revocation ? (
                        <>
                          {', '}
                          <span className={row.class === 'SURFACE' ? 'text-flag' : 'text-ink'}>
                            {row.predicted_revocation}
                          </span>
                        </>
                      ) : null}
                    </span>
                  </td>
                  <td
                    className={`data py-2 pr-4 text-micro ${
                      row.class === 'SURFACE' ? 'text-flag' : 'text-ink-soft'
                    }`}
                  >
                    {classLabel(row.class)}
                  </td>
                  <td className="data hidden py-2 pr-4 text-micro text-ink-soft sm:table-cell">
                    {humanizeReason(row.reason)}
                  </td>
                  <td className="data hidden py-2 pr-4 text-micro text-ink-soft sm:table-cell">
                    {row.last_filed_end ?? (row.class === 'NEVER_FILED' ? 'none' : 'n/a')}
                  </td>
                  <td className="data hidden py-2 pr-4 text-right text-micro text-ink-soft sm:table-cell">
                    {row.unfiled_past_due ?? 'n/a'}
                  </td>
                  <td
                    className={`data hidden py-2 text-micro whitespace-nowrap sm:table-cell ${
                      row.class === 'SURFACE' ? 'text-flag' : 'text-ink'
                    }`}
                  >
                    {row.predicted_revocation ?? 'n/a'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pageCount > 1 ? (
        <div className="mt-5 flex flex-wrap items-center gap-4">
          <p className="data m-0 text-micro text-ink-soft">
            {formatCount(current * PAGE_SIZE + 1)} to{' '}
            {formatCount(current * PAGE_SIZE + visible.length)} of {formatCount(filtered.length)}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage(current - 1)}
              disabled={current === 0}
              className="cursor-pointer border border-rule px-2.5 py-1 text-micro text-ink-soft hover:border-rule-strong hover:text-ink disabled:cursor-default disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => setPage(current + 1)}
              disabled={current >= pageCount - 1}
              className="cursor-pointer border border-rule px-2.5 py-1 text-micro text-ink-soft hover:border-rule-strong hover:text-ink disabled:cursor-default disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
