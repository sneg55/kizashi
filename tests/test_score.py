from datetime import date
from pathlib import Path

from kizashi.score import months_before, score_silence
from kizashi.sources import RevocationRow, read_bmf, read_postcards, read_revocations

FIX = Path(__file__).parent / "fixtures"


def test_months_before_crosses_the_year():
    assert months_before(date(2026, 3, 11), 6) == date(2025, 9, 11)
    assert months_before(date(2026, 9, 11), 6) == date(2026, 3, 11)


def test_score_hides_later_revocations_from_the_classifier_and_scores_them():
    bmf = read_bmf(FIX / "bmf_small.csv")
    pcs = read_postcards(FIX / "epostcard_small.txt")
    revs = dict(read_revocations(FIX / "revocation_small.txt"))
    as_of = date(2026, 9, 12)
    list_date = date(2028, 12, 31)
    surfaced = [ein for ein, row in bmf.items() if row.filing_req == "02"][0]
    revs[surfaced] = RevocationRow(
        ein=surfaced,
        name=bmf[surfaced].name,
        city="TRENTON",
        state="NJ",
        subsection="03",
        revocation_date=date(2027, 5, 15),
        posting_date=None,
        reinstatement_date=None,
    )
    result = score_silence(bmf, pcs, revs, as_of, list_date)
    assert result.truth == 1
    assert result.universe == sum(1 for row in bmf.values() if row.filing_req == "02")
    assert result.fn == result.truth - result.tp
    assert result.cutoff == date(2028, 6, 28)
    assert sum(bucket["total"] for bucket in result.by_class.values()) == result.universe
    assert sum(bucket["revoked"] for bucket in result.by_class.values()) == 1
