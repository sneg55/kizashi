import { formatCount } from '../lib/format'

const RESTING = 'border-rule-strong bg-sheet text-ink-soft hover:border-ink hover:text-ink'
const ACTIVE = 'border-accent bg-accent text-sheet'

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
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`pill items-baseline gap-1.5 border px-3 py-1.5 text-micro font-medium ${
        active ? ACTIVE : RESTING
      }`}
    >
      <span className={!active && accent ? 'text-flag' : ''}>{label}</span>
      <span className={`data font-normal ${active ? 'text-sheet/80' : 'text-muted'}`}>
        {formatCount(count)}
      </span>
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
      className={`pill border px-3 py-1.5 text-micro font-medium ${active ? ACTIVE : RESTING}`}
    >
      {label}
    </button>
  )
}
