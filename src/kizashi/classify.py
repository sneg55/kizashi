from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable

from kizashi.dates import add_years, due_date, last_day_of_month, period_ends_after
from kizashi.sources import BmfRow, PostcardRow, RevocationRow


class Cls(str, Enum):
    SURFACE = "SURFACE"
    WATCH = "WATCH"
    CURRENT = "CURRENT"
    EXCLUDED = "EXCLUDED"
    DEAD = "DEAD"
    PAST_DUE = "PAST_DUE"
    NEVER_FILED = "NEVER_FILED"


@dataclass(frozen=True)
class Classification:
    ein: str
    name: str
    city: str
    state: str
    cls: Cls
    reason: str
    last_filed_end: date | None
    last_filed_source: str | None
    unfiled_past_due: int | None
    predicted_revocation: date | None
    reinstated: bool
    sources_used: tuple[str, ...]
    evidence: tuple[str, ...]


def _sources_used(bmf: BmfRow | None, pc: PostcardRow | None, rev: RevocationRow | None) -> tuple[str, ...]:
    used = []
    if bmf is not None:
        used.append("bmf")
    if pc is not None:
        used.append("990n")
    if rev is not None:
        used.append("revocation")
    return tuple(used)


def _identity(ein: str, bmf: BmfRow | None, pc: PostcardRow | None, rev: RevocationRow | None) -> tuple[str, str, str]:
    if bmf is not None:
        return bmf.name, bmf.city, bmf.state
    if pc is not None:
        return pc.name, pc.city, pc.state
    if rev is not None:
        return rev.name, rev.city, rev.state
    return "", "", ""


def _excluded(ein, name, city, state, reason, sources_used) -> Classification:
    return Classification(
        ein=ein,
        name=name,
        city=city,
        state=state,
        cls=Cls.EXCLUDED,
        reason=reason,
        last_filed_end=None,
        last_filed_source=None,
        unfiled_past_due=None,
        predicted_revocation=None,
        reinstated=False,
        sources_used=sources_used,
        evidence=(),
    )


def _is_reinstated(rev: RevocationRow, pc: PostcardRow | None, bmf: BmfRow | None) -> bool:
    if rev.reinstatement_date and rev.reinstatement_date > rev.revocation_date:
        return True
    if pc is not None and pc.period_end is not None and pc.period_end > rev.revocation_date:
        return True
    if bmf is not None and bmf.tax_period_end is not None and bmf.tax_period_end > rev.revocation_date:
        return True
    return False


def _ruling_based_last_filed_end(bmf: BmfRow) -> date | None:
    if bmf.ruling is None:
        return None
    ruling_year = bmf.ruling.year
    ruling_month = bmf.ruling.month
    acct_month = bmf.acct_pd if bmf.acct_pd else 12
    if acct_month >= ruling_month:
        first_period_end = last_day_of_month(ruling_year, acct_month)
    else:
        first_period_end = last_day_of_month(ruling_year + 1, acct_month)
    return add_years(first_period_end, -1)


def _build_evidence(source: str, last_filed_end: date, ends: list[date], dues: list[date], predicted: date) -> tuple[str, ...]:
    if source == "990n":
        first = f"Last 990-N on record covers the tax period ending {last_filed_end.isoformat()}"
    elif source == "bmf":
        first = f"Last return on record covers the tax period ending {last_filed_end.isoformat()}"
    else:
        first = f"No 990-N on record; exemption ruling implies a first period ending {last_filed_end.isoformat()}"
    return (
        first,
        f"Return for the period ending {ends[0].isoformat()} was due {dues[0].isoformat()} and is not on record",
        f"Return for the period ending {ends[1].isoformat()} was due {dues[1].isoformat()} and is not on record",
        f"Third consecutive missed due date is {predicted.isoformat()}; revocation is automatic on that date",
    )


def classify_org(ein: str, as_of: date, bmf: BmfRow | None, pc: PostcardRow | None, rev: RevocationRow | None) -> Classification:
    name, city, state = _identity(ein, bmf, pc, rev)
    sources_used = _sources_used(bmf, pc, rev)

    if bmf is None:
        return _excluded(ein, name, city, state, "not_in_bmf", sources_used)

    reinstated = False
    if rev is not None:
        if _is_reinstated(rev, pc, bmf):
            reinstated = True
        else:
            return Classification(
                ein=ein,
                name=name,
                city=city,
                state=state,
                cls=Cls.DEAD,
                reason="on_revocation_list",
                last_filed_end=None,
                last_filed_source=None,
                unfiled_past_due=None,
                predicted_revocation=None,
                reinstated=False,
                sources_used=sources_used,
                evidence=(),
            )

    if bmf.filing_req in {"06", "13"}:
        return _excluded(ein, name, city, state, "church", sources_used)
    if bmf.filing_req != "02":
        return _excluded(ein, name, city, state, "filing_req_not_990n", sources_used)
    if bmf.status != "01":
        return _excluded(ein, name, city, state, "status_not_01", sources_used)
    if bmf.affiliation == "9" and bmf.group not in {"", "0000"}:
        return _excluded(ein, name, city, state, "group_subordinate", sources_used)
    if pc is not None and pc.terminated:
        return _excluded(ein, name, city, state, "terminated", sources_used)

    if pc is not None and pc.period_end is not None and bmf.tax_period_end is not None:
        if pc.period_end >= bmf.tax_period_end:
            last_filed_end, source = pc.period_end, "990n"
        else:
            last_filed_end, source = bmf.tax_period_end, "bmf"
    elif pc is not None and pc.period_end is not None:
        last_filed_end, source = pc.period_end, "990n"
    elif bmf.tax_period_end is not None:
        last_filed_end, source = bmf.tax_period_end, "bmf"
    else:
        last_filed_end = _ruling_based_last_filed_end(bmf)
        source = "ruling"

    if last_filed_end is None:
        return Classification(
            ein=ein,
            name=name,
            city=city,
            state=state,
            cls=Cls.CURRENT,
            reason="not_yet_due",
            last_filed_end=None,
            last_filed_source=None,
            unfiled_past_due=None,
            predicted_revocation=None,
            reinstated=reinstated,
            sources_used=sources_used,
            evidence=(),
        )

    ends = period_ends_after(last_filed_end, 3)
    dues = [due_date(e) for e in ends]
    missed = sum(1 for d in dues if d <= as_of)
    predicted = dues[2]
    is_ruling_based = source == "ruling"

    if missed == 0:
        cls = Cls.CURRENT
        reason = "not_yet_due" if is_ruling_based else "filed"
        evidence = ()
    elif missed == 1:
        cls = Cls.WATCH
        reason = "one_missed"
        evidence = ()
    elif missed == 2:
        cls = Cls.NEVER_FILED if is_ruling_based else Cls.SURFACE
        reason = "two_missed"
        evidence = _build_evidence(source, last_filed_end, ends, dues, predicted)
    else:
        cls = Cls.PAST_DUE
        reason = "revocation_effective_unposted"
        evidence = ()

    return Classification(
        ein=ein,
        name=name,
        city=city,
        state=state,
        cls=cls,
        reason=reason,
        last_filed_end=last_filed_end,
        last_filed_source=source,
        unfiled_past_due=missed,
        predicted_revocation=predicted,
        reinstated=reinstated,
        sources_used=sources_used,
        evidence=evidence,
    )


def classify_portfolio(
    eins: Iterable[str],
    as_of: date,
    bmf: dict[str, BmfRow],
    pcs: dict[str, PostcardRow],
    revs: dict[str, RevocationRow],
) -> list[Classification]:
    return [classify_org(ein, as_of, bmf.get(ein), pcs.get(ein), revs.get(ein)) for ein in eins]
