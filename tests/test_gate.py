from datetime import date
from pathlib import Path
from types import SimpleNamespace

from kizashi.classify import classify_portfolio
from kizashi.gate import AlertGate, AlertStore
from kizashi.sources import read_bmf, read_postcards, read_revocations

FIX = Path(__file__).parent / "fixtures"
AS_OF = date(2026, 9, 12)
SURFACE_EIN = "223456789"
SURFACE_DATE = "2027-05-15"
WATCH_EIN = "223456792"
WATCH_DATE = "2028-05-15"


def classes():
    bmf = read_bmf(FIX / "bmf_small.csv")
    pcs = read_postcards(FIX / "epostcard_small.txt")
    revs = read_revocations(FIX / "revocation_small.txt")
    rows = classify_portfolio(sorted(bmf), AS_OF, bmf, pcs, revs)
    return {c.ein: c for c in rows}


def make_gate(tmp_path: Path):
    events: list = []
    store = AlertStore(tmp_path / "alerts.json")
    return AlertGate(classes(), store, "run-1", events), store, events


def before_event(ein: str, predicted: str):
    return SimpleNamespace(
        tool_use={
            "name": "send_alert",
            "toolUseId": "t1",
            "input": {"ein": ein, "predicted_revocation": predicted, "message": "note"},
        },
        cancel_tool=False,
        selected_tool=None,
        invocation_state={},
    )


def after_event(ein: str, predicted: str, status: str = "success", cancel_message=None):
    return SimpleNamespace(
        tool_use={
            "name": "send_alert",
            "toolUseId": "t1",
            "input": {"ein": ein, "predicted_revocation": predicted, "message": "note"},
        },
        selected_tool=None,
        invocation_state={},
        result={"toolUseId": "t1", "status": status, "content": [{"text": "sent"}]},
        cancel_message=cancel_message,
    )


def test_surface_org_is_allowed(tmp_path):
    gate, _, events = make_gate(tmp_path)
    event = before_event(SURFACE_EIN, SURFACE_DATE)
    gate.before(event)
    assert event.cancel_tool is False
    assert events[0].decision == "allowed"
    assert events[0].reason == f"class=SURFACE, no prior alert for {SURFACE_DATE}"


def test_watch_org_is_cancelled_with_its_class(tmp_path):
    gate, _, events = make_gate(tmp_path)
    event = before_event(WATCH_EIN, WATCH_DATE)
    gate.before(event)
    assert isinstance(event.cancel_tool, str)
    assert "WATCH" in event.cancel_tool
    assert events[0].decision == "cancelled"
    assert events[0].reason == "class=WATCH, not an alert condition"


def test_second_alert_for_the_same_date_is_suppressed(tmp_path):
    gate, store, events = make_gate(tmp_path)
    store.record(SURFACE_EIN, SURFACE_DATE, "run-0")
    event = before_event(SURFACE_EIN, SURFACE_DATE)
    gate.before(event)
    assert event.cancel_tool == f"already alerted for {SURFACE_DATE}"
    assert events[0].decision == "cancelled"


def test_dismissed_org_is_suppressed(tmp_path):
    gate, store, events = make_gate(tmp_path)
    store.dismiss(SURFACE_EIN, SURFACE_DATE)
    event = before_event(SURFACE_EIN, SURFACE_DATE)
    gate.before(event)
    assert event.cancel_tool == f"dismissed for {SURFACE_DATE}"


def test_restore_lifts_a_dismissal_but_not_a_send(tmp_path):
    gate, store, events = make_gate(tmp_path)
    store.dismiss(SURFACE_EIN, SURFACE_DATE)
    assert store.restore(SURFACE_EIN, SURFACE_DATE) is True
    assert store.status(SURFACE_EIN, SURFACE_DATE) is None
    store.record(SURFACE_EIN, SURFACE_DATE, "run-1")
    assert store.restore(SURFACE_EIN, SURFACE_DATE) is False
    assert store.status(SURFACE_EIN, SURFACE_DATE) == "sent"


def test_restore_after_a_sent_alert_puts_the_send_back(tmp_path):
    gate, store, events = make_gate(tmp_path)
    store.record(SURFACE_EIN, SURFACE_DATE, "run-1")
    store.dismiss(SURFACE_EIN, SURFACE_DATE)
    assert store.status(SURFACE_EIN, SURFACE_DATE) == "dismissed"
    assert store.restore(SURFACE_EIN, SURFACE_DATE) is True
    assert store.status(SURFACE_EIN, SURFACE_DATE) == "sent"
    event = before_event(SURFACE_EIN, SURFACE_DATE)
    gate.before(event)
    assert event.cancel_tool == f"already alerted for {SURFACE_DATE}"


def test_unknown_ein_is_cancelled(tmp_path):
    gate, _, events = make_gate(tmp_path)
    event = before_event("999999999", SURFACE_DATE)
    gate.before(event)
    assert event.cancel_tool == "unknown_ein"


def test_wrong_predicted_date_is_cancelled(tmp_path):
    gate, _, events = make_gate(tmp_path)
    event = before_event(SURFACE_EIN, "2030-05-15")
    gate.before(event)
    assert event.cancel_tool == "predicted date mismatch"


def test_after_records_a_successful_send(tmp_path):
    gate, store, _ = make_gate(tmp_path)
    gate.after(after_event(SURFACE_EIN, SURFACE_DATE))
    assert store.has(SURFACE_EIN, SURFACE_DATE)
    assert AlertStore(tmp_path / "alerts.json").has(SURFACE_EIN, SURFACE_DATE)


def test_after_ignores_a_cancelled_call(tmp_path):
    gate, store, _ = make_gate(tmp_path)
    gate.after(after_event(WATCH_EIN, WATCH_DATE, cancel_message="class=WATCH, not an alert condition"))
    assert not store.has(WATCH_EIN, WATCH_DATE)


def test_store_survives_a_reload(tmp_path):
    store = AlertStore(tmp_path / "alerts.json")
    store.record(SURFACE_EIN, SURFACE_DATE, "run-1")
    reloaded = AlertStore(tmp_path / "alerts.json")
    assert reloaded.has(SURFACE_EIN, SURFACE_DATE)
    assert not reloaded.has(SURFACE_EIN, "2028-05-15")
