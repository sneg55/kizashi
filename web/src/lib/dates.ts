export interface CalendarDate {
  year: number
  month: number
  day: number
}

const DAY_MS = 86_400_000

export function parseIso(value: string | null | undefined): CalendarDate | null {
  if (!value) return null
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) return null
  const [, y, m, d] = match
  if (!y || !m || !d) return null
  return { year: Number(y), month: Number(m), day: Number(d) }
}

export function toIso(date: CalendarDate): string {
  const month = String(date.month).padStart(2, '0')
  const day = String(date.day).padStart(2, '0')
  return `${date.year}-${month}-${day}`
}

export function lastDayOfMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate()
}

export function addYears(date: CalendarDate, count: number): CalendarDate {
  const year = date.year + count
  return { year, month: date.month, day: Math.min(date.day, lastDayOfMonth(year, date.month)) }
}

export function dueDate(periodEnd: CalendarDate): CalendarDate {
  const shifted = periodEnd.month + 5
  const year = periodEnd.year + Math.floor((shifted - 1) / 12)
  const month = ((shifted - 1) % 12) + 1
  return { year, month, day: 15 }
}

export function periodEndsAfter(lastEnd: CalendarDate, count: number): CalendarDate[] {
  return Array.from({ length: count }, (_, index) => addYears(lastEnd, index + 1))
}

export function epoch(date: CalendarDate): number {
  return Date.UTC(date.year, date.month - 1, date.day)
}

export function daysBetween(from: CalendarDate, to: CalendarDate): number {
  return Math.round((epoch(to) - epoch(from)) / DAY_MS)
}

export function compareIso(a: string | null, b: string | null): number {
  if (a === b) return 0
  if (a === null) return 1
  if (b === null) return -1
  return a < b ? -1 : 1
}

export type RunwayMarkKind = 'filed' | 'missed' | 'upcoming' | 'revocation' | 'today'

export interface RunwayMark {
  kind: RunwayMarkKind
  date: string
  label: string
  offset: number
}

export interface Runway {
  marks: RunwayMark[]
  span: number
}

export function buildRunway(
  lastFiledEnd: string | null,
  asOf: string,
  predictedRevocation: string | null,
): Runway | null {
  const filed = parseIso(lastFiledEnd)
  const today = parseIso(asOf)
  if (!filed || !today) return null

  const ends = periodEndsAfter(filed, 3)
  const dues = ends.map(dueDate)
  const final = parseIso(predictedRevocation) ?? dues[2] ?? null
  if (!final) return null

  const marks: RunwayMark[] = [
    { kind: 'filed', date: toIso(filed), label: 'Last filed period', offset: 0 },
  ]

  dues.slice(0, 2).forEach((due, index) => {
    const end = ends[index]
    if (!end) return
    marks.push({
      kind: epoch(due) <= epoch(today) ? 'missed' : 'upcoming',
      date: toIso(due),
      label: `Return for ${toIso(end)} due`,
      offset: 0,
    })
  })

  marks.push({ kind: 'today', date: toIso(today), label: 'Run date', offset: 0 })
  marks.push({ kind: 'revocation', date: toIso(final), label: 'Status revoked', offset: 0 })

  const start = epoch(filed)
  const finish = epoch(final)
  const span = Math.max(finish - start, 1)

  const positioned = marks
    .map((mark) => {
      const point = parseIso(mark.date)
      const offset = point ? (epoch(point) - start) / span : 0
      return { ...mark, offset: Math.min(Math.max(offset, 0), 1) }
    })
    .sort((a, b) => a.offset - b.offset)

  return { marks: positioned, span: Math.round(span / DAY_MS) }
}
