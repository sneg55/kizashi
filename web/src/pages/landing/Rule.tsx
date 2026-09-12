import { Section } from '../../components/Section'
import { IRS_RULE_URL } from '../../lib/site'

export function Rule() {
  return (
    <Section title="The rule" align="center">
      <div className="mx-auto max-w-[52rem] text-center">
        <p className="m-0 text-lead text-pretty text-muted">
          Every exempt organization owes an annual return or notice, due on the fifteenth day of
          the fifth month after its tax year ends.
        </p>
        <p className="m-0 mt-8 font-display text-[clamp(1.75rem,4vw,3rem)] leading-[1.15] font-light tracking-[-0.03em] text-balance text-ink">
          Miss three in a row and the exemption is revoked on the third due date, automatically.
        </p>
        <p className="m-0 mt-8 text-lead text-pretty text-muted">
          There is no hearing and no warning. The IRS posts the revocation months after it takes
          effect, which is why the date has to be computed rather than read.
        </p>
        <p className="m-0 mt-8">
          <a href={IRS_RULE_URL} className="ghost-link text-tiny">
            Automatic revocation of exemption, irs.gov ›
          </a>
        </p>
      </div>
    </Section>
  )
}
