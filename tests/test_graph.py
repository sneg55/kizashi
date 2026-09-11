import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

from strands.multiagent import GraphBuilder, MultiAgentBase, MultiAgentResult

from kizashi.classify import Cls, classify_portfolio
from kizashi.graph import ClassifierNode, _input_text, _text_result
from kizashi.ledger import report_to_dict
from kizashi.pipeline import run_pipeline_with_sources
from kizashi.portfolio import Portfolio
from kizashi.sources import read_bmf, read_postcards, read_revocations

FIX = Path(__file__).parent / "fixtures"
AS_OF = date(2026, 9, 12)
SURFACE_EIN = "223456789"
ALL_EINS = [
    "223456789",
    "223456790",
    "223456791",
    "223456792",
    "223456793",
    "223456794",
    "223456795",
    "223456796",
    "223456797",
    "223456798",
]


def load():
    return (
        read_bmf(FIX / "bmf_small.csv"),
        read_postcards(FIX / "epostcard_small.txt"),
        read_revocations(FIX / "revocation_small.txt"),
    )


def classifications():
    bmf, pcs, revs = load()
    return classify_portfolio(ALL_EINS, AS_OF, bmf, pcs, revs)


class RecorderNode(MultiAgentBase):
    def __init__(self) -> None:
        super().__init__()
        self.id = "recorder"
        self.seen = ""

    async def invoke_async(self, task: Any, invocation_state: dict | None = None, **kwargs: Any) -> MultiAgentResult:
        self.seen = _input_text(task)
        return _text_result(self.id, "recorded")


def test_run_pipeline_without_a_model(tmp_path):
    bmf, pcs, revs = load()
    portfolio = Portfolio(name="fixture portfolio", source="fixture", eins=ALL_EINS)
    report = run_pipeline_with_sources(
        portfolio=portfolio,
        as_of=AS_OF,
        bmf=bmf,
        pcs=pcs,
        revs=revs,
        sources=[],
        out_dir=tmp_path / "runs",
        state_dir=tmp_path / "state",
        with_model=False,
    )
    d = report_to_dict(report)
    assert len(d["ledger"]) == 10
    assert d["summary"]["surface"] == 1
    assert len(d["surfaced"]) == 1
    assert d["surfaced"][0]["ein"] == SURFACE_EIN
    assert d["surfaced"][0]["brief"] is None
    assert d["surfaced"][0]["brief_source"] is None
    assert d["surfaced"][0]["alert"] is None
    assert d["gate_events"] == []
    assert d["model"] is None
    assert (tmp_path / "runs" / "latest.json").exists()
    assert json.loads((tmp_path / "runs" / f"{report.run_id}.json").read_text())["run_id"] == report.run_id


def test_classifier_node_emits_the_surfaced_rows():
    node = ClassifierNode(classifications())
    result = asyncio.run(node.invoke_async("run"))
    assert result.status.value == "completed"
    assert SURFACE_EIN in str(result.results["classify"])
    assert "Third consecutive missed due date" in str(result.results["classify"])


def test_classifier_node_is_empty_when_nothing_surfaces():
    rows = [c for c in classifications() if c.cls != Cls.SURFACE]
    result = asyncio.run(ClassifierNode(rows).invoke_async("run"))
    assert str(result.results["classify"]).strip() == "[]"


def test_downstream_node_receives_the_surfaced_ein():
    classifier = ClassifierNode(classifications())
    recorder = RecorderNode()
    builder = GraphBuilder()
    builder.add_node(classifier, "classify")
    builder.add_node(recorder, "brief")
    builder.add_edge("classify", "brief", condition=lambda state: bool(classifier.surfaced))
    builder.set_entry_point("classify")
    builder.set_max_node_executions(2)
    builder.build()("go")
    assert "Inputs from previous nodes" in recorder.seen
    assert SURFACE_EIN in recorder.seen
