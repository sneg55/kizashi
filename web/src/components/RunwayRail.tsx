import { buildRunway } from '../lib/dates'
import type { RunwayMark } from '../lib/dates'

const TICK_STYLE: Record<RunwayMark['kind'], string> = {
  filed: 'h-2.5 w-2.5 translate-y-[3px] bg-ink',
  missed: 'h-4 w-[1.5px] bg-ink',
  upcoming: 'h-3 w-px bg-rule-strong',
  today: 'h-5 w-px bg-ink-soft',
  revocation: 'h-9 w-[3px] translate-y-[6px] bg-flag',
}

const VALUE_STYLE: Record<RunwayMark['kind'], string> = {
  filed: 'text-ink',
  missed: 'text-ink',
  upcoming: 'text-ink-soft',
  today: 'text-ink-soft',
  revocation: 'text-flag',
}

export function RunwayRail({
  lastFiledEnd,
  asOf,
  predictedRevocation,
  animate = false,
}: {
  lastFiledEnd: string | null
  asOf: string
  predictedRevocation: string | null
  animate?: boolean
}) {
  const runway = buildRunway(lastFiledEnd, asOf, predictedRevocation)
  if (!runway) return null

  const today = runway.marks.find((mark) => mark.kind === 'today')?.offset ?? 1
  const firstMissed = runway.marks.find((mark) => mark.kind === 'missed')?.offset ?? today
  const segments = [
    { key: 'filed', left: 0, width: firstMissed, className: 'bg-rule-strong' },
    { key: 'missed', left: firstMissed, width: Math.max(today - firstMissed, 0), className: 'bg-ink' },
    { key: 'left', left: today, width: Math.max(1 - today, 0), className: 'bg-flag' },
  ]

  return (
    <div className={animate ? 'rail-draw' : undefined}>
      <div className="px-1">
        <div className="relative h-10">
          {segments.map((segment) =>
            segment.width > 0 ? (
              <div
                key={segment.key}
                className={`absolute bottom-2 h-0.5 ${segment.className}`}
                style={{ left: `${segment.left * 100}%`, width: `${segment.width * 100}%` }}
              />
            ) : null,
          )}
          {runway.marks.map((mark) => (
            <span
              key={`${mark.kind}-${mark.date}`}
              className={`absolute bottom-2 -translate-x-1/2 ${TICK_STYLE[mark.kind]}`}
              style={{ left: `${mark.offset * 100}%` }}
            />
          ))}
        </div>
      </div>

      <dl className="mt-2 grid grid-cols-2 gap-x-5 gap-y-3 border-t border-rule pt-3 sm:grid-cols-5">
        {runway.marks.map((mark) => (
          <div key={`label-${mark.kind}-${mark.date}`}>
            <dt className="text-micro text-ink-soft">{mark.label}</dt>
            <dd className={`data mt-0.5 text-tiny ${VALUE_STYLE[mark.kind]}`}>{mark.date}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
