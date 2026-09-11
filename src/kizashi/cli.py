import argparse
import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path

from kizashi.backtest import backtest_to_dict, run_backtest
from kizashi.classify import Cls, classify_portfolio
from kizashi.ledger import Report, Surfaced, make_run_id, report_to_dict, write_report
from kizashi.portfolio import build_portfolio_from_bmf, load_portfolio_csv
from kizashi.sources import (
    BMF_URLS,
    POSTCARD_URL,
    REVOCATION_URL,
    fetch,
    read_bmf,
    read_postcards,
    read_revocations,
)

DATA_RAW = Path("data/raw")
POSTCARD_DEST = DATA_RAW / "data-download-epostcard.zip"
REVOCATION_DEST = DATA_RAW / "data-download-revocation.zip"


def _regions_present() -> list[int]:
    return sorted(int(p.stem[2:]) for p in DATA_RAW.glob("eo*.csv"))


def _load_bmf(regions: list[int]) -> dict:
    bmf: dict = {}
    for region in regions:
        bmf.update(read_bmf(DATA_RAW / f"eo{region}.csv"))
    return bmf


def _source_metas(regions: list[int]) -> list:
    metas = [fetch(BMF_URLS[r], DATA_RAW / f"eo{r}.csv") for r in regions]
    metas.append(fetch(POSTCARD_URL, POSTCARD_DEST))
    metas.append(fetch(REVOCATION_URL, REVOCATION_DEST))
    return metas


def cmd_fetch(args: argparse.Namespace) -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    regions = list(range(1, 5)) if args.all_regions else [int(x) for x in args.regions.split(",")]
    metas = [fetch(BMF_URLS[r], DATA_RAW / f"eo{r}.csv", force=args.force) for r in regions]
    metas.append(fetch(POSTCARD_URL, POSTCARD_DEST, force=args.force))
    metas.append(fetch(REVOCATION_URL, REVOCATION_DEST, force=args.force))
    for m in metas:
        print(f"{m.name}\t{m.last_modified}\t{m.rows}")


def cmd_portfolio(args: argparse.Namespace) -> None:
    regions = _regions_present()
    bmf = _load_bmf(regions)
    portfolio = build_portfolio_from_bmf(bmf, args.state, args.zip3)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ein"])
        for ein in portfolio.eins:
            writer.writerow([ein])
    print(f"{portfolio.name}: {len(portfolio.eins)} EINs written to {out}")


def cmd_classify(args: argparse.Namespace) -> None:
    regions = _regions_present()
    bmf = _load_bmf(regions)
    pcs = read_postcards(DATA_RAW / "data-download-epostcard.txt")
    revs = read_revocations(DATA_RAW / "data-download-revocation.txt")
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()

    if args.portfolio:
        portfolio_path = Path(args.portfolio)
        portfolio = load_portfolio_csv(portfolio_path, portfolio_path.stem)
        slug = portfolio_path.stem
    else:
        portfolio = build_portfolio_from_bmf(bmf, args.state, args.zip3)
        slug = f"{args.state.lower()}-{args.zip3}"

    classifications = classify_portfolio(portfolio.eins, as_of, bmf, pcs, revs)
    surfaced = []
    for c in classifications:
        if c.cls == Cls.SURFACE:
            days_left = (c.predicted_revocation - as_of).days
            surfaced.append(Surfaced(classification=c, days_left=days_left, brief=None, outreach=None, alert_status=None, alert_reason=None))

    run_id = make_run_id(datetime.now(timezone.utc), slug)
    sources = _source_metas(regions)
    report = Report(
        run_id=run_id,
        as_of=as_of,
        portfolio=portfolio,
        sources=sources,
        model=None,
        classifications=classifications,
        surfaced=surfaced,
        gate_events=[],
        backtest=None,
    )
    out_dir = Path(args.out)
    path = write_report(report, out_dir)
    summary = report_to_dict(report)["summary"]
    print(f"wrote {path}")
    print(json.dumps(summary))


def cmd_backtest(args: argparse.Namespace) -> None:
    pcs = read_postcards(DATA_RAW / "data-download-epostcard.txt")
    revs = read_revocations(DATA_RAW / "data-download-revocation.txt")
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    misses_out = Path(args.misses) if args.misses else None
    result = run_backtest(revs, pcs, start, end, misses_out)
    postcard_meta = fetch(POSTCARD_URL, POSTCARD_DEST)
    revocation_meta = fetch(REVOCATION_URL, REVOCATION_DEST)
    source_dates = {"revocation": revocation_meta.last_modified, "990n": postcard_meta.last_modified}
    d = backtest_to_dict(result, source_dates)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, indent=2))
    print(f"n={d['n']} exact={d['exact']} exact_rate={d['exact_rate']:.4f} same_month={d['same_month']} same_month_rate={d['same_month_rate']:.4f}")
    print(f"source dates: revocation={source_dates['revocation']} 990n={source_dates['990n']}")


def cmd_reconcile(args: argparse.Namespace) -> None:
    bmf = read_bmf(DATA_RAW / "eo1.csv")
    pcs = read_postcards(DATA_RAW / "data-download-epostcard.txt")
    agree = bmf_later = postcard_later = one_missing = 0
    for ein, b in bmf.items():
        if b.filing_req != "02":
            continue
        pc = pcs.get(ein)
        pc_end = pc.period_end if pc else None
        b_end = b.tax_period_end
        if pc_end is None or b_end is None:
            one_missing += 1
        elif pc_end == b_end:
            agree += 1
        elif b_end > pc_end:
            bmf_later += 1
        else:
            postcard_later += 1
    print(f"agree={agree} bmf_later={bmf_later} postcard_later={postcard_later} one_missing={one_missing}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kizashi")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch_p = sub.add_parser("fetch")
    fetch_p.add_argument("--regions", default="1")
    fetch_p.add_argument("--all-regions", action="store_true")
    fetch_p.add_argument("--force", action="store_true")
    fetch_p.set_defaults(func=cmd_fetch)

    portfolio_p = sub.add_parser("portfolio")
    portfolio_p.add_argument("--state", required=True)
    portfolio_p.add_argument("--zip3", required=True)
    portfolio_p.add_argument("--out", required=True)
    portfolio_p.set_defaults(func=cmd_portfolio)

    classify_p = sub.add_parser("classify")
    classify_p.add_argument("--portfolio")
    classify_p.add_argument("--state")
    classify_p.add_argument("--zip3")
    classify_p.add_argument("--as-of")
    classify_p.add_argument("--out", required=True)
    classify_p.set_defaults(func=cmd_classify)

    backtest_p = sub.add_parser("backtest")
    backtest_p.add_argument("--start", default="2021-01-01")
    backtest_p.add_argument("--end", default="2026-12-31")
    backtest_p.add_argument("--out", default="data/runs/backtest.json")
    backtest_p.add_argument("--misses", default="data/runs/backtest-misses.csv")
    backtest_p.set_defaults(func=cmd_backtest)

    reconcile_p = sub.add_parser("reconcile")
    reconcile_p.set_defaults(func=cmd_reconcile)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
