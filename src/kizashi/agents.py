import json
import logging
from dataclasses import dataclass, field
from typing import Annotated, Any, Callable

from pydantic import BaseModel
from strands import Agent, tool

from kizashi.classify import Classification
from kizashi.dates import due_date, period_ends_after
from kizashi.delivery import Deliverer, alert_subject

logger = logging.getLogger(__name__)

BRIEF_BATCH_SIZE = 8
DISPATCH_BATCH_SIZE = 8

BRIEF_SYSTEM_PROMPT = (
    "You write short factual briefs about nonprofit annual-filing status for a grantmaking intermediary. "
    "You restate the public IRS record. You never add a fact, a number or a date that is not in the input, "
    "and you never give tax advice, legal advice or an opinion about the organization. "
    "For every organization in the input produce one brief, reusing the exact EIN string you were given. "
    "headline: one sentence under fifteen words naming how many annual returns are missing and the date exempt status ends. "
    "what_happens_if_missed: two sentences stating that exempt status is revoked automatically on that date with no hearing "
    "and that the organization then appears on the IRS auto-revocation list. "
    "next_filing_needed: the tax periods that are not on record and the date they must be filed before. "
    "outreach: a note addressed to the intermediary's grants lead, naming the organization, what the record shows "
    "and the statutory date, asking them to contact the organization. Three or four sentences, no advice. "
    "review_note: null for almost every organization. Set it to one sentence only when the record itself suggests "
    "a person should check before anyone is contacted: the name reads as a post, lodge, chapter, council, auxiliary, "
    "unit or local of a national body that may file for it under a group return, or the evidence lines show the "
    "tax year end changed between filings. Name exactly what you saw. Never invent a concern."
)

BRIEF_JSON_ONLY_SUFFIX = (
    "\n\nReturn JSON only, with no prose and no code fence, shaped as "
    '{"briefs": [{"ein": "", "headline": "", "what_happens_if_missed": "", "next_filing_needed": "", "outreach": "", "review_note": null}]}'
)

DISPATCH_SYSTEM_PROMPT = (
    "You dispatch alerts for a grantmaking intermediary. Every organization in the input carries a review_note. "
    "If review_note is null, call the send_alert tool exactly once for that organization, passing its ein, "
    "its predicted_revocation and its message verbatim. "
    "If review_note is not null, do not send: call the hold_for_review tool exactly once instead, passing its ein, "
    "its predicted_revocation and the review_note as the reason, so a person checks the record first. "
    "An error result from either tool is final: never call a tool again for that organization. "
    "When every organization has been attempted, reply with the single word done and no other commentary."
)


class BriefOut(BaseModel):
    ein: str
    headline: str
    what_happens_if_missed: str
    next_filing_needed: str
    outreach: str
    review_note: str | None = None


class BriefBatch(BaseModel):
    briefs: list[BriefOut]


@dataclass
class BriefSet:
    briefs: list[BriefOut] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)

    def by_ein(self) -> dict[str, BriefOut]:
        return {b.ein: b for b in self.briefs}


def format_ein(ein: str) -> str:
    digits = "".join(ch for ch in ein if ch.isdigit()).zfill(9)
    return f"{digits[:2]}-{digits[2:]}"


def normalize_ein(ein: str) -> str:
    return "".join(ch for ch in str(ein) if ch.isdigit())


def brief_payload(rows: list[Classification]) -> list[dict]:
    return [
        {
            "ein": c.ein,
            "name": c.name,
            "city": c.city,
            "state": c.state,
            "predicted_revocation": c.predicted_revocation.isoformat() if c.predicted_revocation else None,
            "unfiled_past_due": c.unfiled_past_due,
            "evidence": list(c.evidence),
        }
        for c in rows
    ]


def make_brief_agent(model: Any) -> Agent:
    return Agent(model=model, system_prompt=BRIEF_SYSTEM_PROMPT, callback_handler=None)


def fallback_brief(c: Classification) -> BriefOut:
    predicted = c.predicted_revocation.isoformat() if c.predicted_revocation else ""
    missing = c.unfiled_past_due or 0
    if c.last_filed_end is not None:
        ends = period_ends_after(c.last_filed_end, 3)
        periods = ", ".join(e.isoformat() for e in ends[:missing])
        last_filed = c.last_filed_end.isoformat()
        first_due = due_date(ends[0]).isoformat()
    else:
        periods = ""
        last_filed = ""
        first_due = ""
    headline = f"{missing} annual returns missing on the IRS record; exempt status ends {predicted}"
    what_happens_if_missed = (
        f"Tax-exempt status is revoked automatically on {predicted}, with no hearing and no further notice. "
        "The organization then appears on the IRS auto-revocation list."
    )
    next_filing_needed = (
        f"The annual return for the tax periods ending {periods}, filed before {predicted}."
        if periods
        else f"An annual return filed before {predicted}."
    )
    outreach = (
        f"Note for the grants lead: {c.name} ({c.city}, {c.state}), EIN {format_ein(c.ein)}. "
        f"The IRS record shows the last return covering the tax period ending {last_filed}, "
        f"and no return for the periods ending {periods} (the first of which was due {first_due}). "
        f"On {predicted} the third consecutive missed due date passes and exempt status ends automatically. "
        "Please contact the organization."
    )
    return BriefOut(
        ein=c.ein,
        headline=headline,
        what_happens_if_missed=what_happens_if_missed,
        next_filing_needed=next_filing_needed,
        outreach=outreach,
        review_note=None,
    )


def _strip_fence(text: str) -> str:
    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[-1]
        if body.rstrip().endswith("```"):
            body = body.rstrip()[: -len("```")]
    start = body.find("{")
    end = body.rfind("}")
    if start != -1 and end != -1 and end > start:
        return body[start : end + 1]
    return body


def _batch_briefs(model: Any, rows: list[Classification]) -> list[BriefOut]:
    prompt = json.dumps(brief_payload(rows), indent=1)
    try:
        result = make_brief_agent(model)(prompt, structured_output_model=BriefBatch)
        parsed = result.structured_output
        if isinstance(parsed, BriefBatch) and parsed.briefs:
            return parsed.briefs
        logger.warning("structured output empty for %d rows, retrying with json only", len(rows))
    except Exception:
        logger.warning("structured output failed for %d rows, retrying with json only", len(rows), exc_info=True)
    raw = str(make_brief_agent(model)(prompt + BRIEF_JSON_ONLY_SUFFIX))
    return BriefBatch.model_validate_json(_strip_fence(raw)).briefs


def write_briefs(model: Any, surfaced: list[Classification], batch_size: int = BRIEF_BATCH_SIZE) -> BriefSet:
    out = BriefSet()
    wanted = {c.ein: c for c in surfaced}
    for start in range(0, len(surfaced), batch_size):
        rows = surfaced[start : start + batch_size]
        try:
            produced = _batch_briefs(model, rows)
        except Exception:
            logger.warning("brief batch of %d fell back to the record", len(rows), exc_info=True)
            produced = []
        seen: set[str] = set()
        for b in produced:
            ein = normalize_ein(b.ein)
            if ein not in wanted or ein in seen:
                continue
            seen.add(ein)
            out.briefs.append(b.model_copy(update={"ein": ein}))
            out.sources[ein] = "model"
        for c in rows:
            if c.ein not in seen:
                out.briefs.append(fallback_brief(c))
                out.sources[c.ein] = "fallback"
    order = {c.ein: i for i, c in enumerate(surfaced)}
    out.briefs.sort(key=lambda b: order.get(b.ein, len(order)))
    return out


def make_send_alert_tool(sink: list[dict], deliverer: Deliverer, names: dict[str, str]) -> Callable:
    @tool(name="send_alert", description="Send one alert about an organization to the intermediary's grants lead.")
    def send_alert(
        ein: Annotated[str, "The organization's nine digit EIN, digits only."],
        predicted_revocation: Annotated[str, "The predicted revocation date as YYYY-MM-DD."],
        message: Annotated[str, "The note to deliver, verbatim."],
    ) -> str:
        key = normalize_ein(ein)
        subject = alert_subject(names.get(key, f"EIN {format_ein(key)}"), predicted_revocation)
        delivery = deliverer.deliver(key, predicted_revocation, subject, message)
        sink.append(
            {
                "ein": key,
                "predicted_revocation": predicted_revocation,
                "message": message,
                "channel": delivery.channel,
                "delivery_id": delivery.delivery_id,
            }
        )
        return f"sent via {delivery.channel}, delivery {delivery.delivery_id}"

    return send_alert


def make_hold_tool(holds: list[dict]) -> Callable:
    @tool(
        name="hold_for_review",
        description="Hold an organization's alert so a person checks the record before anyone is contacted.",
    )
    def hold_for_review(
        ein: Annotated[str, "The organization's nine digit EIN, digits only."],
        predicted_revocation: Annotated[str, "The predicted revocation date as YYYY-MM-DD."],
        reason: Annotated[str, "What in the record suggests a person should check first."],
    ) -> str:
        holds.append({"ein": normalize_ein(ein), "predicted_revocation": predicted_revocation, "reason": reason})
        return "held"

    return hold_for_review


def make_dispatch_agent(model: Any, tools: list, hooks: list) -> Agent:
    return Agent(
        model=model,
        system_prompt=DISPATCH_SYSTEM_PROMPT,
        tools=tools,
        hooks=hooks,
        callback_handler=None,
    )


def dispatch_rows(surfaced: list[Classification], briefs: dict[str, BriefOut]) -> list[dict]:
    rows = []
    for c in surfaced:
        b = briefs.get(c.ein)
        if b is None:
            continue
        rows.append(
            {
                "ein": c.ein,
                "name": c.name,
                "predicted_revocation": c.predicted_revocation.isoformat() if c.predicted_revocation else "",
                "message": b.outreach,
                "review_note": b.review_note,
            }
        )
    return rows


def dispatch_alerts(
    model: Any,
    rows: list[dict],
    gate: Any,
    sink: list[dict],
    deliverer: Deliverer,
    holds: list[dict] | None = None,
    batch_size: int = DISPATCH_BATCH_SIZE,
) -> None:
    names = {normalize_ein(r["ein"]): r.get("name", "") for r in rows}
    tools = [make_send_alert_tool(sink, deliverer, names), make_hold_tool(holds if holds is not None else [])]
    for start in range(0, len(rows), batch_size):
        _dispatch_batch(model, rows[start : start + batch_size], gate, tools)
    missed = [r for r in rows if normalize_ein(r["ein"]) not in gate.attempted]
    for start in range(0, len(missed), batch_size):
        _dispatch_batch(model, missed[start : start + batch_size], gate, tools)


def _dispatch_batch(model: Any, batch: list[dict], gate: Any, tools: list) -> None:
    try:
        make_dispatch_agent(model, tools, [gate])(json.dumps(batch, indent=1))
    except Exception:
        logger.warning("dispatch batch of %d failed", len(batch), exc_info=True)
