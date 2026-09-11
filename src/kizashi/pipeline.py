import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

from kizashi.classify import Classification, Cls, classify_portfolio
from kizashi.gate import AlertGate, AlertStore
from kizashi.graph import GRAPH_TASK, PipelineState, build_graph
from kizashi.ledger import Brief, GateEvent, Report, Surfaced, make_run_id, write_report
from kizashi.model import make_model, model_descriptor
from kizashi.portfolio import Portfolio
from kizashi.sources import (
    BMF_URLS,
    POSTCARD_URL,
    REVOCATION_URL,
    BmfRow,
    PostcardRow,
    RevocationRow,
    SourceMeta,
    fetch,
    read_bmf,
    read_postcards,
    read_revocations,
)

FORCE_EIN_ENV = "KIZASHI_DEMO_FORCE_EIN"


def slugify(name: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in name)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "portfolio"


def _force_row(classes: dict[str, Classification]) -> dict | None:
    ein = "".join(ch for ch in os.environ.get(FORCE_EIN_ENV, "") if ch.isdigit())
    if not ein:
        return None
    c = classes.get(ein)
    if c is None:
        return {"ein": ein, "name": "", "predicted_revocation": "", "message": "Please review this organization."}
    return {
        "ein": ein,
        "name": c.name,
        "predicted_revocation": c.predicted_revocation.isoformat() if c.predicted_revocation else "",
        "message": f"Note for the grants lead: please review {c.name} against the IRS record.",
    }


def _alert_for(ein: str, events: list[GateEvent]) -> tuple[str | None, str | None]:
    mine = [e for e in events if e.ein == ein]
    for e in mine:
        if e.decision == "allowed":
            return "sent", e.reason
    if mine:
        return "suppressed", mine[-1].reason
    return None, None


def load_sources(
    data_dir: Path,
) -> tuple[dict[str, BmfRow], dict[str, PostcardRow], dict[str, RevocationRow], list[SourceMeta]]:
    regions = sorted(int(p.stem[2:]) for p in data_dir.glob("eo*.csv"))
    bmf: dict[str, BmfRow] = {}
    for region in regions:
        bmf.update(read_bmf(data_dir / f"eo{region}.csv"))
    pcs = read_postcards(data_dir / "data-download-epostcard.txt")
    revs = read_revocations(data_dir / "data-download-revocation.txt")
    metas = [fetch(BMF_URLS[r], data_dir / f"eo{r}.csv") for r in regions]
    metas.append(fetch(POSTCARD_URL, data_dir / "data-download-epostcard.zip"))
    metas.append(fetch(REVOCATION_URL, data_dir / "data-download-revocation.zip"))
    return bmf, pcs, revs, metas


def run_pipeline_with_sources(
    portfolio: Portfolio,
    as_of: date,
    bmf: dict[str, BmfRow],
    pcs: dict[str, PostcardRow],
    revs: dict[str, RevocationRow],
    sources: list[SourceMeta],
    out_dir: Path,
    state_dir: Path,
    with_model: bool = True,
    slug: str | None = None,
) -> Report:
    classifications = classify_portfolio(portfolio.eins, as_of, bmf, pcs, revs)
    classes = {c.ein: c for c in classifications}
    surfaced_rows = [c for c in classifications if c.cls == Cls.SURFACE]

    run_id = make_run_id(datetime.now(timezone.utc), slug or slugify(portfolio.name))
    store = AlertStore(state_dir / "alerts.json")
    events: list[GateEvent] = []
    gate = AlertGate(classes, store, run_id, events)
    state = PipelineState()

    if with_model and surfaced_rows:
        graph = build_graph(classifications, make_model(), gate, state, _force_row(classes))
        graph(GRAPH_TASK)

    briefs = state.brief_set.by_ein()
    surfaced = []
    for c in surfaced_rows:
        b = briefs.get(c.ein)
        status, reason = _alert_for(c.ein, events)
        surfaced.append(
            Surfaced(
                classification=c,
                days_left=(c.predicted_revocation - as_of).days if c.predicted_revocation else 0,
                brief=Brief(
                    headline=b.headline,
                    what_happens_if_missed=b.what_happens_if_missed,
                    next_filing_needed=b.next_filing_needed,
                )
                if b
                else None,
                outreach=b.outreach if b else None,
                alert_status=status,
                alert_reason=reason,
                brief_source=state.brief_set.sources.get(c.ein),
            )
        )

    backtest_path = out_dir / "backtest.json"
    backtest = json.loads(backtest_path.read_text()) if backtest_path.exists() else None

    report = Report(
        run_id=run_id,
        as_of=as_of,
        portfolio=portfolio,
        sources=sources,
        model=model_descriptor() if with_model else None,
        classifications=classifications,
        surfaced=surfaced,
        gate_events=events,
        backtest=backtest,
    )
    write_report(report, out_dir)
    return report


def run_pipeline(
    portfolio: Portfolio,
    as_of: date,
    data_dir: Path,
    out_dir: Path,
    state_dir: Path,
    with_model: bool = True,
    slug: str | None = None,
) -> Report:
    bmf, pcs, revs, sources = load_sources(data_dir)
    return run_pipeline_with_sources(
        portfolio=portfolio,
        as_of=as_of,
        bmf=bmf,
        pcs=pcs,
        revs=revs,
        sources=sources,
        out_dir=out_dir,
        state_dir=state_dir,
        with_model=with_model,
        slug=slug,
    )
