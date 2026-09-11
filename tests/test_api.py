import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kizashi.api import create_app
from kizashi.gate import AlertStore

SAMPLE = Path(__file__).parent.parent / "data" / "demo" / "report.sample.json"


@pytest.fixture
def client(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    sample = json.loads(SAMPLE.read_text())
    older = dict(sample, run_id="2026-09-10T09-00-00Z-nj-086")
    newer = dict(sample, run_id="2026-09-12T14-03-11Z-nj-086")
    (runs / f"{older['run_id']}.json").write_text(json.dumps(older))
    (runs / f"{newer['run_id']}.json").write_text(json.dumps(newer))
    (runs / "latest.json").write_text(json.dumps(newer))
    (runs / "backtest.json").write_text(json.dumps({"n": 2, "exact": 1}))
    app = create_app(runs_dir=runs, state_dir=tmp_path / "state", web_dist=tmp_path / "dist")
    return TestClient(app), tmp_path


def test_list_runs_is_newest_first(client):
    c, _ = client
    body = c.get("/api/runs").json()
    assert [r["run_id"] for r in body] == ["2026-09-12T14-03-11Z-nj-086", "2026-09-10T09-00-00Z-nj-086"]
    assert set(body[0]) == {"run_id", "as_of", "portfolio", "summary"}
    assert body[0]["summary"]["surface"] == 3
    assert body[0]["portfolio"]["count"] == 886


def test_latest_run_is_the_full_report(client):
    c, _ = client
    body = c.get("/api/runs/latest").json()
    assert body["run_id"] == "2026-09-12T14-03-11Z-nj-086"
    assert body["surfaced"][0]["brief_source"] == "model"
    assert body["gate_events"][1]["decision"] == "cancelled"


def test_run_by_id(client):
    c, _ = client
    body = c.get("/api/runs/2026-09-10T09-00-00Z-nj-086").json()
    assert body["run_id"] == "2026-09-10T09-00-00Z-nj-086"


def test_unknown_run_is_404(client):
    c, _ = client
    assert c.get("/api/runs/2019-01-01T00-00-00Z-nope").status_code == 404


def test_backtest(client):
    c, _ = client
    assert c.get("/api/backtest").json()["n"] == 2


def test_dismiss_writes_to_the_alert_store(client):
    c, tmp_path = client
    body = c.post("/api/orgs/223456789/dismiss", json={"predicted_revocation": "2027-05-15"})
    assert body.json() == {"ok": True}
    store = AlertStore(tmp_path / "state" / "alerts.json")
    assert store.has("223456789", "2027-05-15")


def test_run_without_an_as_of_is_rejected(client):
    c, _ = client
    body = c.post("/api/runs", json={"portfolio_csv": "data/demo/portfolio-nj-086.csv", "with_model": False})
    assert body.status_code == 400


def test_unbuilt_web_app_is_404(client):
    c, _ = client
    assert c.get("/").status_code == 404


def test_web_app_serves_index_and_assets(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>kizashi</title>")
    (dist / "assets" / "app.js").write_text("export default 1;")
    c = TestClient(create_app(runs_dir=runs, state_dir=tmp_path / "state", web_dist=dist))
    assert "kizashi" in c.get("/").text
    assert "export default" in c.get("/assets/app.js").text
    assert "kizashi" in c.get("/app").text
