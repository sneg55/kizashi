# Kizashi

A background agent, built with the Strands Agents SDK, that watches the public IRS filing record for a portfolio of small nonprofits and surfaces only the ones on the statutory path to automatic revocation of tax-exempt status, with the date it happens and the evidence. Every organization it stays silent on is written to a ledger with the reason.

Built for the AWS Agents for Humans Hackathon, Good Neighbor track. Created during the submission period; no pre-existing code.

## Backtest

`uv run kizashi backtest` over revocations dated 2021-01-01 to 2026-12-31, joined to the 990-N file, with 2020 excluded and refiled rows dropped: n=152249, exact=133844, exact_rate=0.8791, same_month=133844, same_month_rate=0.8791. Source file dates: revocation list 2026-09-11, 990-N file 2026-09-07.

## Demo portfolio

`uv run kizashi portfolio --state NJ --zip3 086` then `uv run kizashi classify --portfolio data/demo/portfolio-nj-086.csv --as-of 2026-09-12`, 886 EINs: surface=38, watch=151, current=456, excluded=215, dead=11, reinstated=99, never_filed=14, past_due=1, alerts_sent=0, alerts_suppressed=0.

## Source agreement

`uv run kizashi reconcile`, BMF `TAX_PERIOD` against the last 990-N `Tax Period End` for `eo1.csv` filing-requirement-02 organizations: agree=97114, bmf_later=6639, postcard_later=1107, one_missing=25741.
