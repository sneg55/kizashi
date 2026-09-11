from datetime import date
from pathlib import Path

from kizashi.sources import read_bmf, read_postcards, read_revocations

FIX = Path(__file__).parent / "fixtures"


def test_read_bmf_types():
    rows = read_bmf(FIX / "bmf_small.csv")
    r = rows["223456789"]
    assert r.filing_req == "02" and r.status == "01" and r.affiliation == "3"
    assert r.tax_period_end == date(2023, 12, 31) and r.acct_pd == 12 and r.ruling == date(2010, 5, 31)
    assert rows["223456791"].tax_period_end is None


def test_read_postcards_skips_blank_lines_and_officer_fields():
    rows = read_postcards(FIX / "epostcard_small.txt")
    assert set(rows) == {"223456789", "223456790", "223456793"}
    r = rows["223456789"]
    assert r.tax_year == 2023 and r.period_end == date(2023, 12, 31) and r.terminated is False
    assert rows["223456793"].terminated is True
    assert not hasattr(r, "officer")


def test_read_revocations_dates():
    rows = read_revocations(FIX / "revocation_small.txt")
    assert rows["223456794"].revocation_date == date(2024, 5, 15)
    assert rows["223456794"].reinstatement_date is None
    assert rows["223456795"].reinstatement_date == date(2023, 3, 1)
