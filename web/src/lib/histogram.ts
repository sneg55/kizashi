export interface Bucket {
  month: number
  count: number
}

export function toBuckets(histogram: Record<string, number>): Bucket[] {
  const entries = Object.entries(histogram)
    .map(([month, count]) => ({ month: Number(month), count }))
    .filter((bucket) => Number.isFinite(bucket.month))
  if (entries.length === 0) return []

  const months = entries.map((bucket) => bucket.month)
  const low = Math.min(...months, 0)
  const high = Math.max(...months, 0)
  const counts = new Map(entries.map((bucket) => [bucket.month, bucket.count]))

  return Array.from({ length: high - low + 1 }, (_, index) => {
    const month = low + index
    return { month, count: counts.get(month) ?? 0 }
  })
}

export function tickLabel(month: number): string {
  if (month === 0) return '0'
  return month > 0 ? `+${month}` : String(month)
}
