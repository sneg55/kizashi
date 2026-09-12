import json
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from kizashi.gate import AlertStore
from kizashi.ledger import report_to_dict
from kizashi.pipeline import run_pipeline
from kizashi.portfolio import load_portfolio_csv

DEFAULT_RUNS_DIR = Path("data/runs")
DEFAULT_STATE_DIR = Path("data/state")
DEFAULT_DATA_DIR = Path("data/raw")
DEFAULT_WEB_DIST = Path("web/dist")
RESERVED_RUN_FILES = {"latest.json", "backtest.json"}


class DismissBody(BaseModel):
    predicted_revocation: str


class RunBody(BaseModel):
    portfolio_csv: str = "data/demo/portfolio-nj-086.csv"
    with_model: bool = True
    as_of: str | None = None


def run_files(runs_dir: Path) -> list[Path]:
    if not runs_dir.exists():
        return []
    files = [p for p in runs_dir.glob("*.json") if p.name not in RESERVED_RUN_FILES]
    return sorted(files, key=lambda p: p.name, reverse=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def with_dismissals(report: dict, store: AlertStore) -> dict:
    for org in report.get("surfaced") or []:
        predicted = org.get("predicted_revocation")
        org["dismissed"] = bool(predicted) and store.status(org["ein"], predicted) == "dismissed"
    return report


def _index_entry(report: dict) -> dict:
    portfolio = report.get("portfolio") or {}
    return {
        "run_id": report.get("run_id"),
        "as_of": report.get("as_of"),
        "portfolio": {"name": portfolio.get("name"), "count": portfolio.get("count")},
        "summary": report.get("summary"),
    }


def create_app(
    runs_dir: Path = DEFAULT_RUNS_DIR,
    state_dir: Path = DEFAULT_STATE_DIR,
    data_dir: Path = DEFAULT_DATA_DIR,
    web_dist: Path = DEFAULT_WEB_DIST,
    default_as_of: date | None = None,
) -> FastAPI:
    app = FastAPI(title="kizashi")

    def store() -> AlertStore:
        return AlertStore(state_dir / "alerts.json")

    def annotated(report: dict) -> dict:
        for key in ("backtest", "silence"):
            path = runs_dir / f"{key}.json"
            if path.exists():
                report[key] = _load(path)
        return with_dismissals(report, store())

    @app.get("/api/runs")
    def list_runs() -> list[dict]:
        return [_index_entry(_load(p)) for p in run_files(runs_dir)]

    @app.get("/api/runs/latest")
    def latest_run() -> dict:
        latest = runs_dir / "latest.json"
        if latest.exists():
            return annotated(_load(latest))
        files = run_files(runs_dir)
        if not files:
            raise HTTPException(status_code=404, detail="no runs")
        return annotated(_load(files[0]))

    @app.get("/api/runs/{run_id}")
    def run_by_id(run_id: str) -> dict:
        for path in run_files(runs_dir):
            if path.stem == run_id:
                return annotated(_load(path))
        for path in run_files(runs_dir):
            if _load(path).get("run_id") == run_id:
                return annotated(_load(path))
        raise HTTPException(status_code=404, detail="unknown run")

    @app.get("/api/backtest")
    def backtest() -> dict:
        path = runs_dir / "backtest.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="no backtest")
        return _load(path)

    @app.post("/api/orgs/{ein}/dismiss")
    def dismiss(ein: str, body: DismissBody) -> dict:
        store().dismiss(ein, body.predicted_revocation)
        return {"ok": True}

    @app.post("/api/orgs/{ein}/restore")
    def restore(ein: str, body: DismissBody) -> dict:
        if not store().restore(ein, body.predicted_revocation):
            raise HTTPException(status_code=404, detail="no dismissal on record")
        return {"ok": True}

    @app.post("/api/runs")
    def start_run(body: RunBody) -> dict:
        portfolio_path = Path(body.portfolio_csv)
        if not portfolio_path.exists():
            raise HTTPException(status_code=404, detail="unknown portfolio")
        as_of = date.fromisoformat(body.as_of) if body.as_of else default_as_of
        if as_of is None:
            raise HTTPException(status_code=400, detail="as_of is required")
        portfolio = load_portfolio_csv(portfolio_path, portfolio_path.stem)
        report = run_pipeline(
            portfolio=portfolio,
            as_of=as_of,
            data_dir=data_dir,
            out_dir=runs_dir,
            state_dir=state_dir,
            with_model=body.with_model,
            slug=portfolio_path.stem,
        )
        return annotated(report_to_dict(report))

    @app.get("/{asset_path:path}")
    def web(asset_path: str) -> FileResponse:
        index = web_dist / "index.html"
        if not index.exists():
            raise HTTPException(status_code=404, detail="web app is not built")
        candidate = (web_dist / asset_path).resolve()
        if asset_path and candidate.is_file() and web_dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)

    return app


app = create_app()
