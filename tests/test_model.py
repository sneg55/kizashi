from datetime import date
from pathlib import Path

import pytest
from strands import Agent

from kizashi.agents import write_briefs
from kizashi.classify import Cls, classify_portfolio
from kizashi.model import aws_session_live, make_model, model_descriptor
from kizashi.sources import read_bmf, read_postcards, read_revocations

FIX = Path(__file__).parent / "fixtures"
AS_OF = date(2026, 9, 12)
needs_session = pytest.mark.skipif(not aws_session_live(), reason="no aws session")


def surface_rows():
    bmf = read_bmf(FIX / "bmf_small.csv")
    pcs = read_postcards(FIX / "epostcard_small.txt")
    revs = read_revocations(FIX / "revocation_small.txt")
    rows = classify_portfolio(sorted(bmf), AS_OF, bmf, pcs, revs)
    return [c for c in rows if c.cls == Cls.SURFACE]


def test_model_descriptor_defaults_to_mantle_gemma():
    d = model_descriptor()
    assert set(d) == {"provider", "model_id", "region"}
    assert d["provider"] == "bedrock-mantle"


@needs_session
def test_model_answers():
    agent = Agent(model=make_model(), callback_handler=None)
    assert "ok" in str(agent("Reply with the single word ok")).lower()


@needs_session
def test_write_briefs_covers_the_surface_fixture():
    rows = surface_rows()
    result = write_briefs(make_model(), rows)
    assert [b.ein for b in result.briefs] == [c.ein for c in rows]
    assert result.briefs[0].headline
    assert result.briefs[0].outreach
    assert result.sources[rows[0].ein] in {"model", "fallback"}
