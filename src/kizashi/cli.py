import argparse
import csv
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from kizashi.backtest import backtest_to_dict, run_backtest
from kizashi.classify import Cls, classify_portfolio
from kizashi.ledger import Report, Surfaced, make_run_id, report_to_dict, write_report
from kizashi.pipeline import load_sources, run_pipeline
from kizashi.portfolio import build_portfolio_from_bmf, load_portfolio_csv
from kizashi.score import score_silence, score_to_dict
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


def cmd_run(args: argparse.Namespace) -> None:
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    portfolio_path = Path(args.portfolio)
    portfolio = load_portfolio_csv(portfolio_path, args.name or portfolio_path.stem)
    report = run_pipeline(
        portfolio=portfolio,
        as_of=as_of,
        data_dir=DATA_RAW,
        out_dir=Path(args.out),
        state_dir=Path(args.state),
        with_model=not args.no_model,
        slug=portfolio_path.stem,
    )
    d = report_to_dict(report)
    for event in d["gate_events"]:
        print(f"gate {event['decision']}\t{event['ein']}\t{event['reason']}")
    briefs = Counter(row["brief_source"] for row in d["surfaced"])
    print(f"briefs: model={briefs.get('model', 0)} fallback={briefs.get('fallback', 0)} none={briefs.get(None, 0)}")
    print(f"model: {json.dumps(d['model'])}")
    print(f"wrote {Path(args.out) / (report.run_id + '.json')}")
    print(json.dumps(d["summary"]))


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
    print(f"coverage: {json.dumps(d['coverage'])}")
    print(f"source dates: revocation={source_dates['revocation']} 990n={source_dates['990n']}")


def cmd_score(args: argparse.Namespace) -> None:
    bmf, pcs, revs, metas = load_sources(DATA_RAW)
    revocation_meta = next(m for m in metas if m.name.startswith("data-download-revocation"))
    list_date = date.fromisoformat(revocation_meta.last_modified)
    as_of = date.fromisoformat(args.as_of)
    result = score_silence(bmf, pcs, revs, as_of, list_date, args.lag_months)
    d = score_to_dict(result)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, indent=2))
    print(
        f"as_of={d['as_of']} list_date={d['list_date']} universe={d['universe']} truth={d['truth']} "
        f"positives={d['positives']} tp={d['tp']} fp={d['fp']} fn={d['fn']} "
        f"precision={d['precision']:.4f} recall={d['recall']:.4f} "
        f"recall_excluding_refiled={d['recall_excluding_refiled']:.4f} "
        f"refiled={d['refiled_after_revocation']} lag_excluded={d['lag_excluded']}"
    )
    for cls, bucket in sorted(d["by_class"].items()):
        print(f"{cls}\ttotal={bucket['total']}\trevoked={bucket['revoked']}")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    from kizashi.api import create_app

    uvicorn.run(create_app(default_as_of=date.today()), host=args.host, port=args.port)


def cmd_export(args: argparse.Namespace) -> None:
    from kizashi.api import run_files

    runs_dir = Path(args.runs)
    if args.run == "latest":
        path = runs_dir / "latest.json"
        if not path.exists():
            files = run_files(runs_dir)
            if not files:
                raise SystemExit(f"no runs in {runs_dir}")
            path = files[0]
    else:
        matches = [p for p in run_files(runs_dir) if p.stem == args.run]
        if not matches:
            raise SystemExit(f"unknown run {args.run}")
        path = matches[0]
    report = json.loads(path.read_text())
    backtest_path = runs_dir / "backtest.json"
    if backtest_path.exists():
        report["backtest"] = json.loads(backtest_path.read_text())
    silence_path = runs_dir / "silence.json"
    if silence_path.exists():
        report["silence"] = json.loads(silence_path.read_text())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"exported {report['run_id']} to {out}")


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

    run_p = sub.add_parser("run")
    run_p.add_argument("--portfolio", required=True)
    run_p.add_argument("--as-of")
    run_p.add_argument("--name")
    run_p.add_argument("--out", default="data/runs")
    run_p.add_argument("--state", default="data/state")
    run_p.add_argument("--no-model", action="store_true")
    run_p.set_defaults(func=cmd_run)

    backtest_p = sub.add_parser("backtest")
    backtest_p.add_argument("--start", default="2021-01-01")
    backtest_p.add_argument("--end", default="2026-12-31")
    backtest_p.add_argument("--out", default="data/runs/backtest.json")
    backtest_p.add_argument("--misses", default="data/runs/backtest-misses.csv")
    backtest_p.set_defaults(func=cmd_backtest)

    score_p = sub.add_parser("score")
    score_p.add_argument("--as-of", required=True)
    score_p.add_argument("--lag-months", type=int, default=6)
    score_p.add_argument("--out", default="data/runs/silence.json")
    score_p.set_defaults(func=cmd_score)

    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.set_defaults(func=cmd_serve)

    export_p = sub.add_parser("export")
    export_p.add_argument("--run", default="latest")
    export_p.add_argument("--runs", default="data/runs")
    export_p.add_argument("--out", default="web/public/data/report.json")
    export_p.set_defaults(func=cmd_export)

    reconcile_p = sub.add_parser("reconcile")
    reconcile_p.set_defaults(func=cmd_reconcile)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
