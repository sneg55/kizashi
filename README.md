# Kizashi

A background agent, built with the Strands Agents SDK, that watches the public IRS filing record for a portfolio of small nonprofits and surfaces only the ones on the statutory path to automatic revocation of tax-exempt status, with the date it happens and the evidence. Every organization it stays silent on is written to a ledger with the reason.

Built for the AWS Agents for Humans Hackathon, Good Neighbor track. Created during the submission period; no pre-existing code.

## The rule it watches

An exempt organization that fails to file its annual return or notice for three consecutive years loses its exemption automatically, effective on the due date of the third return. There is no hearing and no advance notice. The IRS publishes the revocations months later. Small all-volunteer organizations, the ones a community foundation or fiscal sponsor funds by the hundred, are the ones this happens to.

Kizashi computes the date from the public record instead of waiting for the list.

## What it does

1. Loads three public IRS bulk files: the Exempt Organizations Business Master File, the Form 990-N e-Postcard download, and the Automatic Revocation List.
2. For every organization in a portfolio, finds the last return on record, projects the next three due dates, counts how many have already passed, and computes the date revocation becomes automatic.
3. Applies exclusions a person would apply: group-ruling subordinates, churches, terminated organizations, organizations that are not 990-N filers, organizations already on the revocation list, organizations that were reinstated.
4. Writes one ledger row per organization with its class and the reason it was, or was not, surfaced.
5. For the few that are surfaced, a Strands agent writes a brief and an outreach note from the evidence, and a second agent dispatches alerts through a `send_alert` tool.
6. A deterministic hook on that tool cancels any alert whose organization is not in the surfaced class, whose date does not match the record, or which has already been sent. Every cancellation is logged with its reason.

## Built with Strands Agents SDK

- `strands.multiagent.GraphBuilder` assembles the pipeline: a custom `MultiAgentBase` node runs the deterministic classifier and never calls a model, then a brief agent with pydantic structured output, then a dispatch agent that owns the `send_alert` tool.
- `strands.hooks.BeforeToolCallEvent` is the gate. It reads the ledger and the alert history and sets `cancel_tool` with a reason string when the call is not allowed. `AfterToolCallEvent` records the sends.
- The model is served by Amazon Bedrock through the Mantle endpoint, using the `OpenAIModel` provider with `bedrock_mantle_config`, which mints a short-term Bedrock API key per request from the AWS session. The default model is `google.gemma-4-31b`.
- The runtime entrypoint is a `BedrockAgentCoreApp`, invoked at `/invocations` with a portfolio path and an as-of date.

## Architecture

![architecture](docs/architecture.png)

```mermaid
flowchart LR
  P[Portfolio CSV] --> G
  subgraph G[Strands Graph]
    A[load_sources] --> B[classify<br/>custom MultiAgentBase node<br/>deterministic]
    B --> C{any SURFACE?}
    C -- no --> L[ledger_writer]
    C -- yes --> D[brief<br/>Agent, structured output]
    D --> E[dispatch<br/>Agent with send_alert tool]
    E --> L
  end
  H[BeforeToolCallEvent hook<br/>cancel_tool unless SURFACE<br/>and not previously alerted] -. gates .-> E
  M[(Alert history<br/>AlertStore)] <--> H
  L --> R[Report: surfaced, ledger, gate events, backtest]
  G --> RT[AgentCore Runtime<br/>scheduled invoke]
```

## Run it

```bash
uv sync --extra dev
uv run kizashi fetch
uv run kizashi portfolio --state NJ --zip3 086 --out data/demo/portfolio-nj-086.csv
uv run kizashi classify --portfolio data/demo/portfolio-nj-086.csv --out data/runs/
uv run kizashi backtest --out data/runs/backtest.json
uv run kizashi run --portfolio data/demo/portfolio-nj-086.csv --out data/runs/
uv run kizashi serve --port 8000
uv run python src/kizashi/runtime_app.py
```

`classify` is the deterministic pass with no model. `run` adds the brief agent, the dispatch agent and the gate. `serve` exposes the API and the built web app. The last line runs the AgentCore runtime contract locally on port 8080.

Web app:

```bash
cd web && pnpm install && pnpm dev
```

The landing page is at `/`, the dashboard at `/app`. Tests: `uv run pytest -q`.

## Backtest

`uv run kizashi backtest` over revocations dated 2021-01-01 to 2026-12-31, joined to the 990-N file, with 2020 excluded and refiled rows dropped: n=152249, exact=133844, exact_rate=0.8791, same_month=133844, same_month_rate=0.8791. Source file dates: revocation list 2026-09-11, 990-N file 2026-09-07.

The residual is not noise. The histogram of actual minus predicted, in months and clamped to plus or minus 24, has three spikes away from zero: +24 or more (8631 rows) and +12 (4194 rows), organizations the IRS revoked one or more filing years later than the postcard record implies, usually because a later 990 or 990-EZ is not in the postcard file; and -24 or less (4192 rows), organizations whose last postcard on record postdates an earlier revocation. All three are labelled in the web app's histogram.

## Demo portfolio

`uv run kizashi portfolio --state NJ --zip3 086` then `uv run kizashi classify --portfolio data/demo/portfolio-nj-086.csv --as-of 2026-09-12`, 886 EINs: surface=38, watch=151, current=456, excluded=215, dead=11, reinstated=99, never_filed=14, past_due=1, alerts_sent=0, alerts_suppressed=0.

## Live run with the model and the gate

`KIZASHI_DEMO_FORCE_EIN=010579647 uv run kizashi run --portfolio data/demo/portfolio-nj-086.csv --name "Mercer County NJ small nonprofits"` on 2026-09-11 with a fresh alert history, model `google.gemma-4-31b` on Bedrock Mantle in us-east-1: briefs model=38 fallback=0; alerts_sent=38, alerts_suppressed=1. The suppressed one is the forced negative control, cancelled by the hook with `class=WATCH, not an alert condition`. A second run over the same portfolio without clearing the alert history yields alerts_sent=0 and alerts_suppressed=38, each cancelled with `already alerted for <date>`. This run is the report the web app ships with.

## Runtime

`uv run python src/kizashi/runtime_app.py` starts the AgentCore runtime contract locally on port 8080; `POST /invocations` with `{"portfolio_csv": "data/demo/portfolio-nj-086.csv", "with_model": false}` returns the run summary. Deploying it to a hosted AgentCore Runtime is blocked on this AWS account by a zero agents-per-account quota, so the hosted step is not part of this submission.

## Source agreement

`uv run kizashi reconcile`, BMF `TAX_PERIOD` against the last 990-N `Tax Period End` for `eo1.csv` filing-requirement-02 organizations: agree=97114, bmf_later=6639, postcard_later=1107, one_missing=25741.

## Data handling

Public organizational data only. The 990-N file's principal-officer name and address fields are never read into memory, never rendered, and never sent to a model. No credentials, no scraping behind a login. The only outbound side effect is an alert message, and the hook owns that gate. Alert text states what is on the record and the statutory date; it does not give tax advice. Every report carries the source file dates so a reader can see how stale the record is.

## License

MIT.
