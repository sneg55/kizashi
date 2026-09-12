import { useId, useState } from 'react'
import { formatCount } from '../lib/format'
import {
  CLAMP_MONTHS,
  residualPeak,
  shortTickLabel,
  tickLabel,
  toBuckets,
  topResiduals,
} from '../lib/histogram'
import type { Bucket } from '../lib/histogram'

const PLOT_HEIGHT = 128
const LABEL_BAND = 20
const HEADROOM = 16
const BASELINE = LABEL_BAND + PLOT_HEIGHT
const BAR_MAX = PLOT_HEIGHT - HEADROOM
const BREAK_STUB = 6
const BREAK_GAP = 6
const SPIKE_LABELS = 3
const MIN_LABEL_GAP = 4

type Anchor = 'start' | 'middle' | 'end'

function anchorFor(index: number, total: number): Anchor {
  if (index === 0) return 'start'
  if (index === total - 1) return 'end'
  return 'middle'
}

function anchoredX(index: number, total: number, slot: number): string {
  if (index === 0) return '0%'
  if (index === total - 1) return '100%'
  return `${index * slot + slot / 2}%`
}

export function Histogram({ histogram }: { histogram: Record<string, number> }) {
  const buckets = toBuckets(histogram)
  const [hovered, setHovered] = useState<Bucket | null>(null)
  const describedBy = useId()

  if (buckets.length === 0) return null

  const zeroCount = buckets.find((bucket) => bucket.month === 0)?.count ?? 0
  const residual = residualPeak(buckets)
  const broken = residual > 0 && zeroCount > residual * 1.5
  const scalePeak = Math.max(broken ? residual : Math.max(zeroCount, residual), 1)

  const slot = 100 / buckets.length
  const barWidth = Math.max(slot - slot * 0.28, slot * 0.4)
  const readout = hovered ?? buckets.find((bucket) => bucket.month === 0) ?? buckets[0]
  const tickStep = buckets.length > 28 ? 12 : 6

  const labelled = new Set<number>()
  const placedIndexes: number[] = []
  for (const spike of topResiduals(buckets, SPIKE_LABELS)) {
    const index = buckets.indexOf(spike)
    if (placedIndexes.some((taken) => Math.abs(taken - index) < MIN_LABEL_GAP)) continue
    labelled.add(spike.month)
    placedIndexes.push(index)
  }

  return (
    <figure className="m-0">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 text-micro text-muted">
        <span>Date the IRS recorded minus the predicted date, in months</span>
        {readout ? (
          <span className="data text-tiny font-medium text-ink">
            {tickLabel(readout.month)} months: {formatCount(readout.count)} organizations
          </span>
        ) : null}
      </figcaption>

      <svg
        width="100%"
        height={BASELINE}
        className="mt-3 block"
        role="img"
        aria-label="Distribution of the difference between the predicted and recorded revocation dates"
        aria-describedby={describedBy}
        onMouseLeave={() => setHovered(null)}
      >
        <line
          x1="0%"
          x2="100%"
          y1={BASELINE - BAR_MAX}
          y2={BASELINE - BAR_MAX}
          className="stroke-rule-strong"
          strokeWidth={1}
        />
        {buckets.map((bucket, index) => {
          const isZero = bucket.month === 0
          const brokenBar = broken && isZero
          const height = brokenBar
            ? BASELINE - LABEL_BAND
            : bucket.count === 0
              ? 0
              : Math.max((bucket.count / scalePeak) * BAR_MAX, 3)
          const top = BASELINE - height
          const isHovered = hovered?.month === bucket.month
          const isSpike = labelled.has(bucket.month)
          const showLabel = isSpike || (brokenBar && bucket.count > 0)
          const fill = isHovered
            ? 'fill-accent'
            : isZero
              ? 'fill-ink'
              : isSpike
                ? 'fill-flag'
                : 'fill-accent-mist'
          const anchor = anchorFor(index, buckets.length)

          return (
            <g key={bucket.month}>
              <rect
                x={`${index * slot}%`}
                y={0}
                width={`${slot}%`}
                height={BASELINE}
                fill="transparent"
                onMouseEnter={() => setHovered(bucket)}
              />
              {height > 0 ? (
                <rect
                  x={`${index * slot + (slot - barWidth) / 2}%`}
                  y={top}
                  width={`${barWidth}%`}
                  height={height}
                  rx={3}
                  className={fill}
                  pointerEvents="none"
                />
              ) : null}
              {brokenBar ? (
                <rect
                  x={`${index * slot + (slot - barWidth) / 2}%`}
                  y={LABEL_BAND + BREAK_STUB}
                  width={`${barWidth}%`}
                  height={BREAK_GAP}
                  className="fill-sheet"
                  pointerEvents="none"
                />
              ) : null}
              {showLabel ? (
                <text
                  x={anchoredX(index, buckets.length, slot)}
                  y={brokenBar ? LABEL_BAND - 6 : top - 5}
                  textAnchor={anchor}
                  className="data fill-ink text-[0.75rem] font-medium"
                  pointerEvents="none"
                >
                  {formatCount(bucket.count)}
                </text>
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
              className={`data absolute text-micro ${
                index === 0
                  ? 'left-0'
                  : index === buckets.length - 1
                    ? 'right-0'
                    : '-translate-x-1/2'
              } ${bucket.month === 0 ? 'text-ink' : 'text-muted'}`}
              style={
                index === 0 || index === buckets.length - 1
                  ? undefined
                  : { left: `${index * slot + slot / 2}%` }
              }
            >
              {shortTickLabel(bucket.month)}
            </span>
          ) : null,
        )}
      </div>

      {broken ? (
        <p className="m-0 mt-5 max-w-[62ch] text-micro text-muted">
          Bars are scaled to the largest bucket away from zero, {formatCount(scalePeak)}. The zero
          bucket is taller than the plot, so it is drawn broken and carries its own count. The two
          end buckets hold every case {CLAMP_MONTHS} months or further out.
        </p>
      ) : null}

      <p id={describedBy} className="sr-only">
        {buckets
          .filter((bucket) => bucket.count > 0)
          .map((bucket) => `${tickLabel(bucket.month)}: ${bucket.count}`)
          .join('. ')}
      </p>
    </figure>
  )
}
