from datetime import date
from pathlib import Path

from kizashi.backtest import run_backtest
from kizashi.sources import PostcardRow, RevocationRow, read_postcards, read_revocations

FIX = Path(__file__).parent / "fixtures"


def test_run_backtest_exact_and_off_by_one_month():
    revs = dict(read_revocations(FIX / "revocation_small.txt"))
    pcs = dict(read_postcards(FIX / "epostcard_small.txt"))

    revs["900000001"] = RevocationRow(
        ein="900000001",
        name="EXACT MATCH ORG",
        city="TRENTON",
        state="NJ",
        subsection="03",
        revocation_date=date(2024, 5, 15),
        posting_date=None,
        reinstatement_date=None,
    )
    pcs["900000001"] = PostcardRow(
        ein="900000001",
        tax_year=2020,
        name="EXACT MATCH ORG",
        terminated=False,
        period_begin=date(2020, 1, 1),
        period_end=date(2020, 12, 31),
        city="TRENTON",
        state="NJ",
    )

    revs["900000002"] = RevocationRow(
        ein="900000002",
        name="OFF BY ONE ORG",
        city="TRENTON",
        state="NJ",
        subsection="03",
        revocation_date=date(2024, 5, 15),
        posting_date=None,
        reinstatement_date=None,
    )
    pcs["900000002"] = PostcardRow(
        ein="900000002",
        tax_year=2020,
        name="OFF BY ONE ORG",
        terminated=False,
        period_begin=date(2020, 1, 1),
        period_end=date(2020, 11, 30),
        city="TRENTON",
        state="NJ",
    )

    result = run_backtest(revs, pcs, date(2021, 1, 1), date(2026, 12, 31))

    assert result.n == 2
    assert result.exact == 1
    assert result.histogram_months == {0: 1, 1: 1}
