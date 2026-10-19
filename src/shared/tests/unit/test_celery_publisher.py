"""O publisher manda para a fila o que as rotas dos módulos pedem, pelo nome da task."""
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.shared.adapters import CeleryPublisher, TaskCall
from src.shared.domain import DomainEvent


@dataclass(frozen=True)
class _Happened(DomainEvent):
    what: str


@dataclass
class _Queue:
    sent: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def send_task(self, name: str, *, kwargs: dict[str, str]) -> object:
        self.sent.append((name, kwargs))
        return None


def _route(event: DomainEvent) -> TaskCall | None:
    return TaskCall("demo.task", {"what": event.what}) if isinstance(event, _Happened) else None


async def test_routed_event_becomes_a_task() -> None:
    # Arrange
    queue = _Queue()

    # Act
    await CeleryPublisher(queue, routes=[_route]).publish(_Happened(occurred_on=datetime.now(UTC), what="x"))

    # Assert
    assert queue.sent == [("demo.task", {"what": "x"})]


async def test_event_without_a_route_is_only_logged() -> None:
    # Arrange
    queue = _Queue()

    # Act
    await CeleryPublisher(queue, routes=[_route]).publish(DomainEvent(occurred_on=datetime.now(UTC)))

    # Assert
    assert queue.sent == []
