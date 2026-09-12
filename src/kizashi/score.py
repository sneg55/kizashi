from dataclasses import dataclass, field
from datetime import date

from kizashi.classify import Classification, Cls, classify_portfolio
from kizashi.sources import BmfRow, PostcardRow, RevocationRow

POSITIVE_CLASSES = {Cls.SURFACE}
DEFAULT_LAG_MONTHS = 6


@dataclass
class SilenceScore:
    as_of: date
    list_date: date
    cutoff: date
    universe: int
    truth: int
    positives: int
    tp: int
    fp: int
    fn: int
    refiled_after_revocation: int
    lag_excluded: int
    by_class: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def precision(self) -> float:
        return self.tp / self.positives if self.positives else 0.0

    @property
    def recall(self) -> float:
        return self.tp / self.truth if self.truth else 0.0

    @property
    def recall_excluding_refiled(self) -> float:
        denominator = self.truth - self.refiled_after_revocation
        return self.tp / denominator if denominator else 0.0


def months_before(d: date, months: int) -> date:
    month = d.month - months
    year = d.year
    while month < 1:
        month += 12
        year -= 1
    return date(year, month, min(d.day, 28))


def score_silence(
    bmf: dict[str, BmfRow],
    pcs: dict[str, PostcardRow],
    revs: dict[str, RevocationRow],
    as_of: date,
    list_date: date,
    lag_months: int = DEFAULT_LAG_MONTHS,
) -> SilenceScore:
    universe = sorted(ein for ein, row in bmf.items() if row.filing_req == "02")
    universe_set = set(universe)
    known = {ein: r for ein, r in revs.items() if r.revocation_date <= as_of}
    truth = {
        ein: r for ein, r in revs.items() if ein in universe_set and as_of < r.revocation_date <= list_date
    }
    cutoff = months_before(list_date, lag_months)
    rows: list[Classification] = classify_portfolio(universe, as_of, bmf, pcs, known)

    by_class: dict[str, dict[str, int]] = {}
    tp = fp = positives = lag_excluded = 0
    for c in rows:
        bucket = by_class.setdefault(c.cls.value, {"total": 0, "revoked": 0})
        bucket["total"] += 1
        revoked = c.ein in truth
        if revoked:
            bucket["revoked"] += 1
        if c.cls not in POSITIVE_CLASSES or c.predicted_revocation is None:
            continue
        if c.predicted_revocation > cutoff:
            lag_excluded += 1
            continue
        positives += 1
        if revoked:
            tp += 1
        else:
            fp += 1

    refiled = sum(
        1
        for ein, r in truth.items()
        if (pc := pcs.get(ein)) is not None and pc.period_end is not None and pc.period_end > r.revocation_date
    )
    return SilenceScore(
        as_of=as_of,
        list_date=list_date,
        cutoff=cutoff,
        universe=len(universe),
        truth=len(truth),
        positives=positives,
        tp=tp,
        fp=fp,
        fn=len(truth) - tp,
        refiled_after_revocation=refiled,
        lag_excluded=lag_excluded,
        by_class=by_class,
    )


def score_to_dict(s: SilenceScore) -> dict:
    return {
        "as_of": s.as_of.isoformat(),
        "list_date": s.list_date.isoformat(),
        "cutoff": s.cutoff.isoformat(),
        "universe": s.universe,
        "truth": s.truth,
        "positives": s.positives,
        "tp": s.tp,
        "fp": s.fp,
        "fn": s.fn,
        "precision": s.precision,
        "recall": s.recall,
        "recall_excluding_refiled": s.recall_excluding_refiled,
        "refiled_after_revocation": s.refiled_after_revocation,
        "lag_excluded": s.lag_excluded,
        "by_class": s.by_class,
    }
