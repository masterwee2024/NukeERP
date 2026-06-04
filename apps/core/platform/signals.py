"""Signal bus for inter-module communication.

Modules emit and subscribe to named events without importing each other directly.
"""

import logging
from collections import defaultdict
from collections.abc import Callable

logger = logging.getLogger(__name__)

_handler_registry: dict[str, list[Callable[[dict], object]]] = defaultdict(list)


def send(event_name: str, data: dict | None = None) -> list:
    """Emit an event — all subscribed handlers receive the data."""
    results: list = []
    for handler in _handler_registry.get(event_name, []):
        try:
            results.append(handler(data or {}))
        except Exception:
            logger.exception(
                "Handler %s failed for event %s", handler.__name__, event_name
            )
    return results


def subscribe(event_name: str, handler: Callable[[dict], object]) -> None:
    """Register a callable to handle a named event."""
    _handler_registry[event_name].append(handler)
    logger.info("Handler %s subscribed to %s", handler.__name__, event_name)


def unsubscribe(event_name: str, handler: Callable[[dict], object]) -> None:
    """Remove a handler from a named event."""
    _handler_registry[event_name] = [
        h for h in _handler_registry[event_name] if h is not handler
    ]


CORE_EVENTS: frozenset[str] = frozenset(
    {
        "invoice.posted",
        "payment.received",
        "asset.registered",
        "employee.hired",
        "stock.received",
        "facility.utility.reading",
    }
)
