import json
import logging
from dataclasses import dataclass, field
from typing import Any

from strands.agent import AgentResult
from strands.multiagent import GraphBuilder, MultiAgentBase, MultiAgentResult, Status
from strands.multiagent.base import NodeResult
from strands.telemetry.metrics import EventLoopMetrics

from kizashi.agents import BriefBatch, BriefOut, BriefSet, brief_payload, dispatch_alerts, dispatch_rows, write_briefs
from kizashi.classify import Classification, Cls
from kizashi.delivery import Deliverer, DryRunDelivery
from kizashi.gate import AlertGate

logger = logging.getLogger(__name__)

GRAPH_TASK = "Classify the portfolio against the IRS record, brief what surfaces, and dispatch the alerts."


@dataclass
class PipelineState:
    brief_set: BriefSet = field(default_factory=BriefSet)
    alerts: list[dict] = field(default_factory=list)
    holds: list[dict] = field(default_factory=list)


def _text_result(node_id: str, text: str) -> MultiAgentResult:
    agent_result = AgentResult(
        stop_reason="end_turn",
        message={"role": "assistant", "content": [{"text": text}]},
        metrics=EventLoopMetrics(),
        state={},
    )
    return MultiAgentResult(
        status=Status.COMPLETED,
        results={node_id: NodeResult(result=agent_result, status=Status.COMPLETED, execution_count=1)},
        execution_count=1,
    )


def _input_text(task: Any) -> str:
    if isinstance(task, str):
        return task
    if isinstance(task, list):
        parts = []
        for block in task:
            if isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(task)


def _briefs_from_text(text: str) -> dict[str, BriefOut]:
    start = text.find('{"briefs"')
    end = text.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        return {b.ein: b for b in BriefBatch.model_validate_json(text[start : end + 1]).briefs}
    except Exception:
        logger.warning("dispatch node could not parse the brief node output", exc_info=True)
        return {}


class ClassifierNode(MultiAgentBase):
    def __init__(self, classifications: list[Classification]) -> None:
        super().__init__()
        self.id = "classify"
        self.classifications = classifications
        self.surfaced = [c for c in classifications if c.cls == Cls.SURFACE]

    async def invoke_async(self, task: Any, invocation_state: dict | None = None, **kwargs: Any) -> MultiAgentResult:
        payload = brief_payload(self.surfaced)
        return _text_result(self.id, json.dumps(payload, indent=1) if payload else "[]")


class BriefNode(MultiAgentBase):
    def __init__(self, model: Any, surfaced: list[Classification], state: PipelineState) -> None:
        super().__init__()
        self.id = "brief"
        self.model = model
        self.surfaced = surfaced
        self.state = state

    async def invoke_async(self, task: Any, invocation_state: dict | None = None, **kwargs: Any) -> MultiAgentResult:
        self.state.brief_set = write_briefs(self.model, self.surfaced)
        return _text_result(self.id, BriefBatch(briefs=self.state.brief_set.briefs).model_dump_json())


class DispatchNode(MultiAgentBase):
    def __init__(
        self,
        model: Any,
        surfaced: list[Classification],
        gate: AlertGate,
        state: PipelineState,
        force_row: dict | None = None,
        deliverer: Deliverer | None = None,
    ) -> None:
        super().__init__()
        self.id = "dispatch"
        self.model = model
        self.surfaced = surfaced
        self.gate = gate
        self.state = state
        self.force_row = force_row
        self.deliverer = deliverer if deliverer is not None else DryRunDelivery()

    async def invoke_async(self, task: Any, invocation_state: dict | None = None, **kwargs: Any) -> MultiAgentResult:
        briefs = _briefs_from_text(_input_text(task)) or self.state.brief_set.by_ein()
        rows = dispatch_rows(self.surfaced, briefs)
        if self.force_row is not None:
            rows.append(self.force_row)
        dispatch_alerts(self.model, rows, self.gate, self.state.alerts, self.deliverer, self.state.holds)
        summary = {
            "attempted": len(rows),
            "sent": len(self.state.alerts),
            "held": len(self.state.holds),
            "gate_events": len(self.gate.events),
        }
        return _text_result(self.id, json.dumps(summary))


def build_graph(
    classifications: list[Classification],
    model: Any,
    gate: AlertGate,
    state: PipelineState | None = None,
    force_row: dict | None = None,
    deliverer: Deliverer | None = None,
):
    pipeline_state = state if state is not None else PipelineState()
    classifier = ClassifierNode(classifications)
    brief = BriefNode(model, classifier.surfaced, pipeline_state)
    dispatch = DispatchNode(model, classifier.surfaced, gate, pipeline_state, force_row, deliverer)
    builder = GraphBuilder()
    builder.add_node(classifier, "classify")
    builder.add_node(brief, "brief")
    builder.add_node(dispatch, "dispatch")
    builder.add_edge("classify", "brief", condition=lambda state: bool(classifier.surfaced))
    builder.add_edge("brief", "dispatch")
    builder.set_entry_point("classify")
    builder.set_max_node_executions(3)
    return builder.build()
