"""Singleton registry for pluggable industry modules."""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

from apps.core.platform.schemas import ModuleConfigSchema, ModuleDetailSchema
from apps.core.platform.signals import CORE_EVENTS, subscribe

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """Central registry that tracks all registered modules."""

    def __init__(self) -> None:
        self._modules: dict[str, dict[str, Any]] = {}
        self._active: set[str] = set()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_module(self, config: dict) -> ModuleDetailSchema:
        """Register a module after validating its config and dependencies."""
        schema = ModuleConfigSchema(**config)
        code = schema.code

        if code in self._modules:
            msg = f"Module '{code}' is already registered"
            raise ValueError(msg)

        missing = [d for d in schema.dependencies if d not in self._modules]
        if missing:
            msg = f"Module '{code}' has unresolved dependencies: {missing}"
            raise ValueError(msg)

        self._validate_signals(schema)

        self._modules[code] = schema.model_dump()
        self._active.add(code)
        self._auto_subscribe(schema)

        logger.info("Module registered: %s v%s", schema.name, schema.version)
        return self._to_detail(code)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_module(self, code: str) -> ModuleDetailSchema | None:
        raw = self._modules.get(code)
        if raw is None:
            return None
        return self._to_detail(code)

    def get_all_modules(self) -> list[ModuleDetailSchema]:
        return [self._to_detail(code) for code in self._modules]

    def get_module_dependencies(self, code: str) -> list[ModuleDetailSchema]:
        """Return the dependency chain for a module (DFS ordered)."""
        raw = self._modules.get(code)
        if raw is None:
            return []
        resolved: list[ModuleDetailSchema] = []
        seen: set[str] = set()

        def _walk(dep_code: str) -> None:
            if dep_code in seen:
                return
            seen.add(dep_code)
            dep_raw = self._modules.get(dep_code)
            if dep_raw is not None:
                resolved.append(self._to_detail(dep_code))
                for d in dep_raw["dependencies"]:
                    _walk(d)

        for dep_code in raw["dependencies"]:
            _walk(dep_code)
        resolved.append(self._to_detail(code))
        return resolved

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def activate(self, code: str) -> ModuleDetailSchema | None:
        if code not in self._modules:
            return None
        self._active.add(code)
        logger.info("Module activated: %s", code)
        return self._to_detail(code)

    def deactivate(self, code: str) -> ModuleDetailSchema | None:
        if code not in self._modules:
            return None
        self._active.discard(code)
        logger.info("Module deactivated: %s", code)
        return self._to_detail(code)

    def is_active(self, code: str) -> bool:
        return code in self._active

    # ------------------------------------------------------------------
    # Testing
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        """Clear all modules (testing only)."""
        self._modules.clear()
        self._active.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_detail(self, code: str) -> ModuleDetailSchema:
        raw = self._modules[code]
        return ModuleDetailSchema(
            code=code,
            name=raw["name"],
            version=raw["version"],
            description=raw["description"],
            dependencies=list(raw["dependencies"]),
            is_active=code in self._active,
            signals_emitted=list(raw["signals_emitted"]),
            signals_handled=list(raw["signals_handled"]),
        )

    def _validate_signals(self, schema: ModuleConfigSchema) -> None:
        known_events: set[str] = set(CORE_EVENTS)
        for m in self._modules.values():
            known_events.update(m["signals_emitted"])
        for ev in schema.signals_handled:
            if ev not in known_events:
                logger.warning(
                    "Module '%s' subscribes to unknown event '%s'", schema.code, ev
                )

    def _auto_subscribe(self, schema: ModuleConfigSchema) -> None:
        """Dynamically subscribe handlers declared in module config."""
        for event_name in schema.signals_handled:
            _lazy_handler = _make_lazy_handler(schema.code, event_name)
            subscribe(event_name, _lazy_handler)


def _make_lazy_handler(module_code: str, event_name: str) -> Callable[[dict], None]:
    """Return a no-op handler that logs signal delivery.

    Real modules override this to point at their own handler functions.
    """

    @functools.wraps(lambda d: None)
    def _handler(data: dict) -> None:
        logger.debug(
            "Signal '%s' delivered to module '%s' (data keys: %s)",
            event_name,
            module_code,
            list(data.keys()),
        )

    return _handler


# Singleton — importers get the same instance
registry: ModuleRegistry = ModuleRegistry()
