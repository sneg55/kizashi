import { useId, useState } from 'react'
import { formatCount } from '../lib/format'
import { tickLabel, toBuckets } from '../lib/histogram'
import type { Bucket } from '../lib/histogram'

const PLOT_HEIGHT = 128

export function Histogram({ histogram }: { histogram: Record<string, number> }) {
  const buckets = toBuckets(histogram)
  const [hovered, setHovered] = useState<Bucket | null>(null)
  const describedBy = useId()

  if (buckets.length === 0) return null

  const peak = Math.max(...buckets.map((bucket) => bucket.count), 1)
  const slot = 100 / buckets.length
  const barWidth = Math.max(slot - slot * 0.28, slot * 0.4)
  const readout = hovered ?? buckets.find((bucket) => bucket.month === 0) ?? buckets[0]
  const tickStep = buckets.length > 28 ? 12 : 6

  return (
    <figure className="m-0">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 text-micro text-ink-soft">
        <span>Predicted date minus the date the IRS recorded, in months</span>
        {readout ? (
          <span className="data text-tiny text-ink">
            {tickLabel(readout.month)} months, {formatCount(readout.count)} organizations
          </span>
        ) : null}
      </figcaption>

      <svg
        width="100%"
        height={PLOT_HEIGHT}
        className="mt-3 block"
        role="img"
        aria-label="Distribution of the difference between the predicted and recorded revocation dates"
        aria-describedby={describedBy}
        onMouseLeave={() => setHovered(null)}
      >
        {buckets.map((bucket, index) => {
          const height = bucket.count === 0 ? 0 : Math.max((bucket.count / peak) * PLOT_HEIGHT, 2)
          const emphasised = bucket.month === 0 || hovered?.month === bucket.month
          return (
            <g key={bucket.month}>
              <rect
                x={`${index * slot}%`}
                y={0}
                width={`${slot}%`}
                height={PLOT_HEIGHT}
                fill="transparent"
                onMouseEnter={() => setHovered(bucket)}
              />
              {height > 0 ? (
                <rect
                  x={`${index * slot + (slot - barWidth) / 2}%`}
                  y={PLOT_HEIGHT - height}
                  width={`${barWidth}%`}
                  height={height}
                  rx={2}
                  className={emphasised ? 'fill-ink' : 'fill-ink-soft'}
                  pointerEvents="none"
                />
              ) : null}
            </g>
          )
        })}
      </svg>

      <div className="h-px bg-rule-strong" />

      <div className="relative mt-1.5 h-4">
        {buckets.map((bucket, index) =>
          bucket.month % tickStep === 0 ? (
            <span
              key={`tick-${bucket.month}`}
              className={`data absolute -translate-x-1/2 text-micro ${
                bucket.month === 0 ? 'text-ink' : 'text-ink-soft'
              }`}
              style={{ left: `${index * slot + slot / 2}%` }}
            >
              {tickLabel(bucket.month)}
            </span>
          ) : null,
        )}
      </div>

      <p id={describedBy} className="sr-only">
        {buckets
          .filter((bucket) => bucket.count > 0)
          .map((bucket) => `${tickLabel(bucket.month)} months: ${bucket.count}`)
          .join('. ')}
      </p>
    </figure>
  )
}
