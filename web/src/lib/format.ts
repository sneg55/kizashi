export function formatEin(ein: string): string {
  const digits = ein.replace(/\D/g, '')
  if (digits.length !== 9) return ein
  return `${digits.slice(0, 2)}-${digits.slice(2)}`
}

export function formatCount(value: number): string {
  return value.toLocaleString('en-US')
}

export function formatRate(numerator: number, denominator: number): string | null {
  if (denominator <= 0) return null
  return `${((numerator / denominator) * 100).toFixed(1)}%`
}

export function humanizeReason(reason: string): string {
  return reason.replace(/_/g, ' ')
}

export function displayUrl(url: string): string {
  try {
    const parsed = new URL(url)
    return `${parsed.host}${parsed.pathname}`.replace(/\/$/, '')
  } catch {
    return url
  }
}

export function normalizeSearch(value: string): string {
  return value.replace(/[-\s]/g, '').toLowerCase()
}
