import { displayUrl } from '../lib/format'
import { LIVE_URL, REPO_URL } from '../lib/site'

export function SiteFooter() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto flex max-w-[75rem] flex-wrap items-baseline justify-between gap-x-8 gap-y-3 px-5 py-10 text-tiny text-muted sm:px-8">
        <p className="m-0">Built for the AWS Agents for Humans Hackathon, Good Neighbor track.</p>
        <p className="m-0 flex flex-wrap gap-x-6 gap-y-1">
          <span>MIT license</span>
          <a href={REPO_URL} className="no-underline hover:text-accent">
            {displayUrl(REPO_URL)}
          </a>
          {LIVE_URL ? (
            <a href={LIVE_URL} className="no-underline hover:text-accent">
              {displayUrl(LIVE_URL)}
            </a>
          ) : null}
        </p>
      </div>
    </footer>
  )
}
