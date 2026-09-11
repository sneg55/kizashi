from datetime import date
from pathlib import Path

from kizashi.classify import Cls, classify_org, classify_portfolio
from kizashi.sources import read_bmf, read_postcards, read_revocations

FIX = Path(__file__).parent / "fixtures"
AS_OF = date(2026, 9, 12)


def load():
    return read_bmf(FIX / "bmf_small.csv"), read_postcards(FIX / "epostcard_small.txt"), read_revocations(FIX / "revocation_small.txt")


def one(ein):
    bmf, pcs, revs = load()
    return classify_org(ein, AS_OF, bmf.get(ein), pcs.get(ein), revs.get(ein))


def test_two_missed_surfaces_with_third_due_date():
    c = one("223456789")
    assert c.cls == Cls.SURFACE and c.reason == "two_missed"
    assert c.last_filed_end == date(2023, 12, 31) and c.unfiled_past_due == 2
    assert c.predicted_revocation == date(2027, 5, 15)
    assert "2027-05-15" in c.evidence[-1]


def test_current_filer_is_silent():
    c = one("223456790")
    assert c.cls == Cls.CURRENT and c.reason == "filed" and c.unfiled_past_due == 0


def test_one_missed_is_watch():
    c = one("223456792")
    assert c.cls == Cls.WATCH and c.unfiled_past_due == 1 and c.predicted_revocation == date(2028, 5, 15)


def test_group_subordinate_excluded_before_runway():
    c = one("223456791")
    assert c.cls == Cls.EXCLUDED and c.reason == "group_subordinate"


def test_terminated_excluded():
    assert one("223456793").reason == "terminated"


def test_on_list_without_reinstatement_is_dead():
    c = one("223456794")
    assert c.cls == Cls.DEAD and c.reason == "on_revocation_list" and c.reinstated is False


def test_reinstated_reenters_and_classifies_from_new_record():
    c = one("223456795")
    assert c.reinstated is True and c.cls == Cls.WATCH


def test_church_and_non_990n_filers_excluded():
    assert one("223456796").reason == "church"
    assert one("223456798").reason == "filing_req_not_990n"


def test_never_filed_uses_ruling_date():
    c = one("223456797")
    assert c.cls == Cls.PAST_DUE and c.last_filed_source == "ruling"
    assert c.last_filed_end == date(2021, 12, 31)


def test_missing_from_bmf():
    assert one("999999999").reason == "not_in_bmf"


def test_portfolio_preserves_order_and_counts():
    bmf, pcs, revs = load()
    out = classify_portfolio(["223456789", "223456790", "999999999"], AS_OF, bmf, pcs, revs)
    assert [c.ein for c in out] == ["223456789", "223456790", "999999999"]
