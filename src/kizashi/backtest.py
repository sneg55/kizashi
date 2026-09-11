import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from kizashi.dates import due_date, period_ends_after
from kizashi.sources import PostcardRow, RevocationRow


@dataclass
class BacktestResult:
    window: str
    n: int
    exact: int
    same_month: int
    histogram_months: dict[int, int]
    misses_path: Path | None


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def run_backtest(
    revs: dict[str, RevocationRow],
    pcs: dict[str, PostcardRow],
    start: date,
    end: date,
    misses_out: Path | None = None,
) -> BacktestResult:
    n = 0
    exact = 0
    same_month = 0
    histogram: dict[int, int] = {}
    misses: list[dict] = []

    for rev in revs.values():
        if rev.revocation_date.year == 2020:
            continue
        if not (start <= rev.revocation_date <= end):
            continue
        pc = pcs.get(rev.ein)
        if pc is None or pc.period_end is None or pc.period_end > rev.revocation_date:
            continue
        predicted = due_date(period_ends_after(pc.period_end, 3)[2])
        n += 1
        is_exact = predicted == rev.revocation_date
        if is_exact:
            exact += 1
        if predicted.year == rev.revocation_date.year and predicted.month == rev.revocation_date.month:
            same_month += 1
        delta_months = _clamp(
            (rev.revocation_date.year - predicted.year) * 12 + (rev.revocation_date.month - predicted.month),
            -24,
            24,
        )
        histogram[delta_months] = histogram.get(delta_months, 0) + 1
        if not is_exact:
            misses.append(
                {
                    "ein": rev.ein,
                    "name": pc.name,
                    "state": rev.state,
                    "period_end": pc.period_end.isoformat(),
                    "predicted": predicted.isoformat(),
                    "actual": rev.revocation_date.isoformat(),
                    "delta_months": delta_months,
                }
            )

    misses_path = None
    if misses_out is not None:
        misses_out.parent.mkdir(parents=True, exist_ok=True)
        with open(misses_out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ein", "name", "state", "period_end", "predicted", "actual", "delta_months"])
            writer.writeheader()
            writer.writerows(misses)
        misses_path = misses_out

    window = f"revocations dated {start.isoformat()} to {end.isoformat()}"
    return BacktestResult(window=window, n=n, exact=exact, same_month=same_month, histogram_months=histogram, misses_path=misses_path)


def backtest_to_dict(b: BacktestResult, source_dates: dict[str, str]) -> dict:
    return {
        "window": b.window,
        "n": b.n,
        "exact": b.exact,
        "exact_rate": (b.exact / b.n) if b.n else 0.0,
        "same_month": b.same_month,
        "same_month_rate": (b.same_month / b.n) if b.n else 0.0,
        "histogram_months": {str(k): v for k, v in sorted(b.histogram_months.items())},
        "source_dates": source_dates,
    }
