import { Link } from 'react-router'
import { REPO_URL } from '../lib/site'
import { Wordmark } from './Wordmark'

const LINK = 'font-display text-tiny text-ink no-underline transition-colors hover:text-accent'

export function TopBar({ current }: { current: 'landing' | 'app' }) {
  return (
    <header className="sticky top-0 z-20 border-b border-rule bg-sheet/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[75rem] items-center justify-between gap-6 px-5 sm:px-8">
        <Wordmark />
        <nav className="flex items-center gap-5 sm:gap-7">
          {current === 'app' ? (
            <Link to="/" className={LINK}>
              About
            </Link>
          ) : null}
          <a href={REPO_URL} className={LINK}>
            Source
          </a>
          {current === 'landing' ? (
            <Link to="/app" className="pill pill-primary px-4 py-2.5 text-tiny">
              Open the live report
            </Link>
          ) : null}
        </nav>
      </div>
    </header>
  )
}
