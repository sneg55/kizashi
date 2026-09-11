import json
from datetime import date
from pathlib import Path

from kizashi.classify import classify_portfolio
from kizashi.ledger import Report, report_to_dict
from kizashi.portfolio import Portfolio, build_portfolio_from_bmf, load_portfolio_csv
from kizashi.sources import read_bmf, read_postcards, read_revocations

FIX = Path(__file__).parent / "fixtures"
AS_OF = date(2026, 9, 12)

ALL_EINS = [
    "223456789",
    "223456790",
    "223456791",
    "223456792",
    "223456793",
    "223456794",
    "223456795",
    "223456796",
    "223456797",
    "223456798",
]


def load():
    return read_bmf(FIX / "bmf_small.csv"), read_postcards(FIX / "epostcard_small.txt"), read_revocations(FIX / "revocation_small.txt")


def build_report():
    bmf, pcs, revs = load()
    classifications = classify_portfolio(ALL_EINS, AS_OF, bmf, pcs, revs)
    portfolio = Portfolio(name="fixture", source="fixture", eins=ALL_EINS)
    return Report(
        run_id="2026-09-12T00-00-00Z-fixture",
        as_of=AS_OF,
        portfolio=portfolio,
        sources=[],
        model=None,
        classifications=classifications,
        surfaced=[],
        gate_events=[],
        backtest=None,
    )


def test_report_to_dict_shape_and_summary():
    r = build_report()
    d = report_to_dict(r)
    assert set(d.keys()) == {
        "run_id",
        "as_of",
        "portfolio",
        "sources",
        "model",
        "summary",
        "surfaced",
        "ledger",
        "gate_events",
        "backtest",
    }
    assert d["summary"]["surface"] == 1
    assert d["summary"]["reinstated"] == 1
    assert d["ledger"][0]["predicted_revocation"] == "2027-05-15"
    json.dumps(d)


def test_build_portfolio_from_bmf():
    bmf, _, _ = load()
    p = build_portfolio_from_bmf(bmf, "NJ", "086")
    assert set(p.eins) == {
        "223456789",
        "223456790",
        "223456791",
        "223456792",
        "223456793",
        "223456794",
        "223456795",
        "223456797",
    }


def test_load_portfolio_csv_dedupes_and_keeps_order():
    p = load_portfolio_csv(FIX / "portfolio_small.csv", "fixture portfolio")
    assert p.eins == ["223456789", "223456790"]
