import type { ReactNode } from 'react'

export function Section({
  title,
  id,
  children,
}: {
  title: string
  id?: string
  children: ReactNode
}) {
  return (
    <section id={id} className="border-t border-rule py-12 sm:py-16">
      <div className="grid gap-6 md:grid-cols-[11rem_1fr] md:gap-10">
        <h2 className="text-tiny font-medium text-ink-soft md:pt-1">{title}</h2>
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
