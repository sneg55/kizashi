import { formatCount } from '../lib/format'

export function Chip({
  active,
  label,
  count,
  accent = false,
  onClick,
}: {
  active: boolean
  label: string
  count: number
  accent?: boolean
  onClick: () => void
}) {
  const resting = accent
    ? 'border-flag/40 text-flag hover:border-flag'
    : 'border-rule text-ink-soft hover:border-rule-strong hover:text-ink'

  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`flex cursor-pointer items-baseline gap-1.5 border px-2.5 py-1 text-micro transition-colors ${
        active ? 'border-ink bg-ink text-ground' : resting
      }`}
    >
      <span>{label}</span>
      <span className="data opacity-70">{formatCount(count)}</span>
    </button>
  )
}

export function Toggle({
  active,
  label,
  onClick,
}: {
  active: boolean
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`cursor-pointer border px-2.5 py-1 text-micro transition-colors ${
        active
          ? 'border-ink bg-ink text-ground'
          : 'border-rule text-ink-soft hover:border-rule-strong hover:text-ink'
      }`}
    >
      {label}
    </button>
  )
}
