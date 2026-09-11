import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from kizashi.classify import Classification, Cls
from kizashi.portfolio import Portfolio
from kizashi.sources import SourceMeta


@dataclass
class GateEvent:
    ein: str
    tool: str
    decision: str
    reason: str


@dataclass
class Brief:
    headline: str
    what_happens_if_missed: str
    next_filing_needed: str


@dataclass
class Surfaced:
    classification: Classification
    days_left: int
    brief: Brief | None
    outreach: str | None
    alert_status: str | None
    alert_reason: str | None


@dataclass
class Report:
    run_id: str
    as_of: date
    portfolio: Portfolio
    sources: list[SourceMeta]
    model: dict | None
    classifications: list[Classification]
    surfaced: list[Surfaced]
    gate_events: list[GateEvent]
    backtest: dict | None


def make_run_id(as_of_dt: datetime, portfolio_slug: str) -> str:
    ts = as_of_dt.strftime("%Y-%m-%dT%H-%M-%S") + "Z"
    return f"{ts}-{portfolio_slug}"


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _compute_summary(classifications: list[Classification], gate_events: list[GateEvent]) -> dict:
    counts = {c.value.lower(): 0 for c in Cls}
    reinstated = 0
    for c in classifications:
        counts[c.cls.value.lower()] += 1
        if c.reinstated:
            reinstated += 1
    alerts_sent = sum(1 for g in gate_events if g.decision == "allowed")
    alerts_suppressed = sum(1 for g in gate_events if g.decision in {"cancelled", "dismissed"})
    return {
        "surface": counts["surface"],
        "watch": counts["watch"],
        "current": counts["current"],
        "excluded": counts["excluded"],
        "dead": counts["dead"],
        "reinstated": reinstated,
        "never_filed": counts["never_filed"],
        "past_due": counts["past_due"],
        "alerts_sent": alerts_sent,
        "alerts_suppressed": alerts_suppressed,
    }


def _surfaced_to_dict(s: Surfaced) -> dict:
    c = s.classification
    alert = None
    if s.alert_status is not None or s.alert_reason is not None:
        alert = {"status": s.alert_status, "reason": s.alert_reason}
    brief = None
    if s.brief is not None:
        brief = {
            "headline": s.brief.headline,
            "what_happens_if_missed": s.brief.what_happens_if_missed,
            "next_filing_needed": s.brief.next_filing_needed,
        }
    return {
        "ein": c.ein,
        "name": c.name,
        "city": c.city,
        "state": c.state,
        "last_filed_end": _iso(c.last_filed_end),
        "last_filed_source": c.last_filed_source,
        "unfiled_past_due": c.unfiled_past_due,
        "predicted_revocation": _iso(c.predicted_revocation),
        "days_left": s.days_left,
        "evidence": list(c.evidence),
        "brief": brief,
        "outreach": s.outreach,
        "alert": alert,
    }


def _ledger_row(c: Classification) -> dict:
    return {
        "ein": c.ein,
        "name": c.name,
        "class": c.cls.value,
        "reason": c.reason,
        "last_filed_end": _iso(c.last_filed_end),
        "unfiled_past_due": c.unfiled_past_due,
        "predicted_revocation": _iso(c.predicted_revocation),
        "reinstated": c.reinstated,
        "sources_used": list(c.sources_used),
    }


def report_to_dict(r: Report) -> dict:
    return {
        "run_id": r.run_id,
        "as_of": r.as_of.isoformat(),
        "portfolio": {"name": r.portfolio.name, "source": r.portfolio.source, "count": len(r.portfolio.eins)},
        "sources": [{"name": s.name, "url": s.url, "last_modified": s.last_modified, "rows": s.rows} for s in r.sources],
        "model": r.model,
        "summary": _compute_summary(r.classifications, r.gate_events),
        "surfaced": [_surfaced_to_dict(s) for s in r.surfaced],
        "ledger": [_ledger_row(c) for c in r.classifications],
        "gate_events": [{"ein": g.ein, "tool": g.tool, "decision": g.decision, "reason": g.reason} for g in r.gate_events],
        "backtest": r.backtest,
    }


def write_report(r: Report, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    d = report_to_dict(r)
    run_path = out_dir / f"{r.run_id}.json"
    run_path.write_text(json.dumps(d, indent=2))
    (out_dir / "latest.json").write_text(json.dumps(d, indent=2))
    return run_path
