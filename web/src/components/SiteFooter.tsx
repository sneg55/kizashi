import { displayUrl } from '../lib/format'
import { LIVE_URL, REPO_URL } from '../lib/site'

export function SiteFooter() {
  return (
    <footer className="border-t border-rule py-10 text-tiny text-ink-soft">
      <p className="m-0 max-w-[62ch]">
        Built for the AWS Agents for Humans Hackathon, Good Neighbor track.
      </p>
      <p className="m-0 mt-3 flex flex-wrap gap-x-6 gap-y-1">
        <span>MIT licence</span>
        <a href={REPO_URL} className="hover:text-ink">
          {displayUrl(REPO_URL)}
        </a>
        {LIVE_URL ? (
          <a href={LIVE_URL} className="hover:text-ink">
            {displayUrl(LIVE_URL)}
          </a>
        ) : null}
      </p>
    </footer>
  )
}
