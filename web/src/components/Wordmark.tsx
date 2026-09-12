import { Link } from 'react-router'

export function Wordmark({ to = '/' }: { to?: string }) {
  return (
    <Link
      to={to}
      className="font-display text-[1.25rem] leading-none font-medium tracking-[-0.02em] text-ink no-underline"
    >
      Kiza
      <span className="underline decoration-accent decoration-2 underline-offset-[5px]">shi</span>
    </Link>
  )
}
