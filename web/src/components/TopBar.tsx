import { Link } from 'react-router'
import { REPO_URL } from '../lib/site'
import { ThemeToggle } from './ThemeToggle'
import { Wordmark } from './Wordmark'

export function TopBar({ current }: { current: 'landing' | 'app' }) {
  return (
    <header className="flex items-center justify-between gap-4 py-5">
      <Wordmark />
      <nav className="flex items-center gap-4 sm:gap-6">
        {current === 'app' ? (
          <Link to="/" className="text-tiny text-ink-soft no-underline hover:text-ink">
            About
          </Link>
        ) : (
          <Link to="/app" className="text-tiny text-ink-soft no-underline hover:text-ink">
            Live report
          </Link>
        )}
        <a href={REPO_URL} className="text-tiny text-ink-soft no-underline hover:text-ink">
          Source
        </a>
        <ThemeToggle />
      </nav>
    </header>
  )
}
