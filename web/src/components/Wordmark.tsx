import { Link } from 'react-router'

export function Wordmark({ to = '/' }: { to?: string }) {
  return (
    <Link
      to={to}
      className="font-display text-[1.375rem] leading-none font-medium tracking-[-0.01em] text-ink no-underline"
    >
      Kizashi
    </Link>
  )
}
