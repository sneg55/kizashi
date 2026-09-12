import type { ReactNode } from 'react'

export function Section({
  title,
  id,
  count,
  children,
}: {
  title: string
  id?: string
  count?: number
  children: ReactNode
}) {
  return (
    <section id={id} className="border-t border-rule py-12 sm:py-16">
      <div className="grid gap-6 md:grid-cols-[11rem_1fr] md:gap-10">
        <div className="md:pt-1">
          <h2 className="m-0 text-tiny font-medium text-ink-soft">{title}</h2>
          {count === undefined ? null : (
            <p className="data m-0 mt-0.5 text-micro text-ink-soft">{count.toLocaleString('en-US')}</p>
          )}
        </div>
        <div className="min-w-0">{children}</div>
      </div>
    </section>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-0.5 border-b border-rule py-2">
      <dt className="text-tiny text-ink-soft">{label}</dt>
      <dd className="data text-tiny text-ink">{children}</dd>
    </div>
  )
}
