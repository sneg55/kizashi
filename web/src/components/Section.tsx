import type { ReactNode } from 'react'

export function Section({
  title,
  lead,
  id,
  count,
  align = 'start',
  children,
}: {
  title: string
  lead?: ReactNode
  id?: string
  count?: number
  align?: 'start' | 'center'
  children: ReactNode
}) {
  const centered = align === 'center'
  return (
    <section id={id} className="scroll-mt-20 py-16 sm:py-24">
      <div className={centered ? 'mx-auto max-w-[40rem] text-center' : 'max-w-[40rem]'}>
        <h2 className="m-0 font-display text-[2rem] leading-[1.15] font-light tracking-[-0.02em] text-balance text-ink sm:text-[2.5rem]">
          {title}
          {count === undefined ? null : (
            <span className="data ml-3 align-baseline text-[1.25rem] font-normal text-fog">
              {count.toLocaleString('en-US')}
            </span>
          )}
        </h2>
        {lead ? <p className="m-0 mt-4 text-lead text-pretty text-muted">{lead}</p> : null}
      </div>
      <div className="mt-10 min-w-0 sm:mt-14">{children}</div>
    </section>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-0.5 border-b border-rule py-3 last:border-b-0">
      <dt className="text-tiny text-muted">{label}</dt>
      <dd className="data m-0 text-tiny text-ink">{children}</dd>
    </div>
  )
}
