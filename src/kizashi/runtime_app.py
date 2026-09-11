from datetime import date
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from kizashi.ledger import report_to_dict
from kizashi.pipeline import run_pipeline
from kizashi.portfolio import load_portfolio_csv

DEFAULT_PORTFOLIO = "data/demo/portfolio-nj-086.csv"
DATA_DIR = Path("data/raw")
RUNS_DIR = Path("data/runs")
STATE_DIR = Path("data/state")

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict | None = None, context: object = None) -> dict:
    body = payload or {}
    portfolio_path = Path(body.get("portfolio_csv") or DEFAULT_PORTFOLIO)
    portfolio = load_portfolio_csv(portfolio_path, portfolio_path.stem)
    as_of = date.fromisoformat(body["as_of"]) if body.get("as_of") else date.today()
    report = run_pipeline(
        portfolio=portfolio,
        as_of=as_of,
        data_dir=DATA_DIR,
        out_dir=RUNS_DIR,
        state_dir=STATE_DIR,
        with_model=bool(body.get("with_model", True)),
        slug=portfolio_path.stem,
    )
    d = report_to_dict(report)
    return {
        "run_id": d["run_id"],
        "as_of": d["as_of"],
        "portfolio": d["portfolio"],
        "model": d["model"],
        "summary": d["summary"],
    }


if __name__ == "__main__":
    app.run()
