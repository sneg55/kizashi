import json
from pathlib import Path
from typing import Any

from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry

from kizashi.classify import Classification, Cls
from kizashi.ledger import GateEvent

ALERT_TOOL = "send_alert"


def _normalize_ein(ein: Any) -> str:
    return "".join(ch for ch in str(ein) if ch.isdigit())


class AlertStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: dict[str, dict] = {}
        if path.exists():
            self.entries = json.loads(path.read_text())

    @staticmethod
    def key(ein: str, predicted: str) -> str:
        return f"{_normalize_ein(ein)}:{predicted}"

    def has(self, ein: str, predicted: str) -> bool:
        return self.key(ein, predicted) in self.entries

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=2, sort_keys=True))

    def record(self, ein: str, predicted: str, run_id: str) -> None:
        self.entries[self.key(ein, predicted)] = {"status": "sent", "run_id": run_id}
        self._write()

    def dismiss(self, ein: str, predicted: str) -> None:
        prior = self.entries.get(self.key(ein, predicted))
        self.entries[self.key(ein, predicted)] = {"status": "dismissed", "run_id": None, "prior": prior}
        self._write()

    def status(self, ein: str, predicted: str) -> str | None:
        entry = self.entries.get(self.key(ein, predicted))
        return None if entry is None else entry.get("status")

    def restore(self, ein: str, predicted: str) -> bool:
        if self.status(ein, predicted) != "dismissed":
            return False
        prior = self.entries[self.key(ein, predicted)].get("prior")
        if prior is None:
            del self.entries[self.key(ein, predicted)]
        else:
            self.entries[self.key(ein, predicted)] = prior
        self._write()
        return True


class AlertGate(HookProvider):
    def __init__(
        self,
        classes: dict[str, Classification],
        store: AlertStore,
        run_id: str,
        events: list[GateEvent],
    ) -> None:
        self.classes = classes
        self.store = store
        self.run_id = run_id
        self.events = events
        self.attempted: set[str] = set()

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before)
        registry.add_callback(AfterToolCallEvent, self.after)

    @staticmethod
    def _args(event: Any) -> tuple[str, str] | None:
        tool_use = getattr(event, "tool_use", None) or {}
        if tool_use.get("name") != ALERT_TOOL:
            return None
        args = tool_use.get("input") or {}
        return _normalize_ein(args.get("ein", "")), str(args.get("predicted_revocation", "")).strip()

    def _reason(self, ein: str, predicted: str) -> str | None:
        c = self.classes.get(ein)
        if c is None:
            return "unknown_ein"
        if c.cls != Cls.SURFACE:
            return f"class={c.cls.value}, not an alert condition"
        if c.predicted_revocation is None or c.predicted_revocation.isoformat() != predicted:
            return "predicted date mismatch"
        status = self.store.status(ein, predicted)
        if status == "dismissed":
            return f"dismissed for {predicted}"
        if status is not None:
            return f"already alerted for {predicted}"
        return None

    def before(self, event: Any) -> None:
        parsed = self._args(event)
        if parsed is None:
            return
        ein, predicted = parsed
        self.attempted.add(ein)
        reason = self._reason(ein, predicted)
        if reason is None:
            self.events.append(
                GateEvent(
                    ein=ein,
                    tool=ALERT_TOOL,
                    decision="allowed",
                    reason=f"class=SURFACE, no prior alert for {predicted}",
                )
            )
            return
        event.cancel_tool = reason
        self.events.append(GateEvent(ein=ein, tool=ALERT_TOOL, decision="cancelled", reason=reason))

    def after(self, event: Any) -> None:
        parsed = self._args(event)
        if parsed is None:
            return
        if getattr(event, "cancel_message", None) is not None:
            return
        result = getattr(event, "result", None)
        if isinstance(result, dict) and result.get("status") != "success":
            return
        ein, predicted = parsed
        self.store.record(ein, predicted, self.run_id)
