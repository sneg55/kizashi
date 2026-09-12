import { buildRunway } from '../lib/dates'
import type { RunwayMark } from '../lib/dates'

const TICK_STYLE: Record<RunwayMark['kind'], string> = {
  filed: 'h-3 w-3 translate-y-[2px] rounded-full bg-ink',
  missed: 'h-4 w-[2px] rounded-full bg-ink',
  upcoming: 'h-3 w-[2px] rounded-full bg-rule-strong',
  today: 'h-5 w-[2px] rounded-full bg-accent',
  revocation: 'h-9 w-[3px] translate-y-[6px] rounded-full bg-flag',
}

const VALUE_STYLE: Record<RunwayMark['kind'], string> = {
  filed: 'text-ink',
  missed: 'text-ink',
  upcoming: 'text-muted',
  today: 'text-accent',
  revocation: 'text-ink',
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
    <div>
      <div className={`px-1 ${animate ? 'rail-draw' : ''}`}>
        <div className="relative h-10">
          {segments.map((segment) =>
            segment.width > 0 ? (
              <div
                key={segment.key}
                className={`absolute bottom-2 h-[3px] rounded-full ${segment.className}`}
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

      <dl className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(8rem,1fr))] gap-x-5 gap-y-3 border-t border-rule pt-4">
        {runway.marks.map((mark) => (
          <div key={`label-${mark.kind}-${mark.date}`}>
            <dt className="text-micro text-muted">{mark.label}</dt>
            <dd
              className={`data m-0 mt-0.5 text-tiny font-medium whitespace-nowrap ${VALUE_STYLE[mark.kind]} ${
                mark.kind === 'revocation'
                  ? 'inline-block rounded-full bg-flag-wash px-2 py-0.5'
                  : ''
              }`}
            >
              {mark.date}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
