from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .state_store import StateSnapshot


class StateHook(Protocol):
    def handle_snapshot(self, snapshot: "StateSnapshot") -> None:
        ...


@dataclass(slots=True)
class CallbackStateHook:
    callback: Callable[[dict[str, Any]], None]

    def handle_snapshot(self, snapshot: "StateSnapshot") -> None:
        self.callback(snapshot.to_dict())


@dataclass(slots=True)
class InMemoryStateHook:
    events: list[dict[str, Any]] = field(default_factory=list)

    def handle_snapshot(self, snapshot: "StateSnapshot") -> None:
        self.events.append(snapshot.to_dict())

    def tail(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.events[-limit:]
