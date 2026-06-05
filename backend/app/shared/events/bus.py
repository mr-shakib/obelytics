import logging
from collections import defaultdict
from typing import Callable, Awaitable, TypeVar
from app.shared.events.base_event import DomainEvent

logger = logging.getLogger(__name__)

Handler = Callable[[DomainEvent], Awaitable[None]]
T = TypeVar("T", bound=DomainEvent)

_handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)


def subscribe(event_type: type[T], handler: Callable[[T], Awaitable[None]]) -> None:
    _handlers[event_type].append(handler)  # type: ignore[arg-type]


def clear_handlers() -> None:
    _handlers.clear()


async def publish(event: DomainEvent) -> None:
    handlers = _handlers.get(type(event), [])
    for handler in handlers:
        try:
            await handler(event)  # type: ignore[arg-type]
        except Exception:
            logger.exception(
                "Event handler failed",
                extra={"event_type": event.event_type, "handler": handler.__name__},
            )
