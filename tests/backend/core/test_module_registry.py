"""Tests for T009b — Module Plugin Interface."""

import pytest

from apps.core.platform.module_registry import registry
from apps.core.platform.schemas import ModuleDetailSchema
from apps.core.platform.signals import CORE_EVENTS, send, subscribe

# ---------------------------------------------------------------------------
# Fixture — clean singleton state before each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_registry():
    registry._reset()
    yield
    registry._reset()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_valid_module(self):
        result = registry.register_module(
            {
                "name": "Test Module A",
                "code": "test_a",
                "version": "1.0.0",
                "description": "A test module",
                "dependencies": [],
                "signals_emitted": ["test_a.event"],
                "signals_handled": ["invoice.posted"],
            }
        )
        assert isinstance(result, ModuleDetailSchema)
        assert result.code == "test_a"
        assert result.name == "Test Module A"
        assert result.version == "1.0.0"
        assert result.is_active is True

    def test_register_duplicate_raises(self):
        registry.register_module({"name": "Dup", "code": "dup"})
        with pytest.raises(ValueError, match="already registered"):
            registry.register_module({"name": "Dup", "code": "dup"})

    def test_register_module_with_dependencies(self):
        registry.register_module({"name": "A", "code": "a"})
        result = registry.register_module(
            {"name": "B", "code": "b", "dependencies": ["a"]}
        )
        assert result.code == "b"
        assert result.dependencies == ["a"]

    def test_register_missing_dependency_raises(self):
        with pytest.raises(ValueError, match="unresolved dependencies"):
            registry.register_module(
                {"name": "Orphan", "code": "orphan", "dependencies": ["nonexistent"]}
            )

    def test_get_module(self):
        registry.register_module({"name": "A", "code": "a"})
        mod = registry.get_module("a")
        assert mod is not None
        assert mod.code == "a"

    def test_get_module_not_found(self):
        assert registry.get_module("nope") is None

    def test_get_all_modules(self):
        registry.register_module({"name": "A", "code": "a"})
        registry.register_module({"name": "B", "code": "b"})
        codes = {m.code for m in registry.get_all_modules()}
        assert "a" in codes
        assert "b" in codes


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


class TestDependencies:
    def test_dependency_chain(self):
        registry.register_module({"name": "A", "code": "a"})
        registry.register_module({"name": "B", "code": "b", "dependencies": ["a"]})
        chain = registry.get_module_dependencies("b")
        codes = [m.code for m in chain]
        assert codes == ["a", "b"]

    def test_dependency_chain_unknown_module(self):
        assert registry.get_module_dependencies("nope") == []


# ---------------------------------------------------------------------------
# Activation / Deactivation
# ---------------------------------------------------------------------------


class TestActivation:
    def test_activate(self):
        registry.register_module({"name": "A", "code": "a"})
        result = registry.activate("a")
        assert result is not None
        assert result.is_active is True

    def test_deactivate(self):
        registry.register_module({"name": "A", "code": "a"})
        result = registry.deactivate("a")
        assert result is not None
        assert result.is_active is False

    def test_reactivate(self):
        registry.register_module({"name": "A", "code": "a"})
        registry.deactivate("a")
        result = registry.activate("a")
        assert result is not None
        assert result.is_active is True

    def test_activate_unknown(self):
        assert registry.activate("nope") is None

    def test_deactivate_unknown(self):
        assert registry.deactivate("nope") is None

    def test_is_active(self):
        registry.register_module({"name": "A", "code": "a"})
        registry.activate("a")
        assert registry.is_active("a") is True
        registry.deactivate("a")
        assert registry.is_active("a") is False

    def test_unknown_is_not_active(self):
        assert registry.is_active("nope") is False


# ---------------------------------------------------------------------------
# Signal Bus
# ---------------------------------------------------------------------------


class TestSignalBus:
    def test_send_event(self):
        captured = []

        def handler(data):
            captured.append(data)
            return "ok"

        subscribe("test.event", handler)
        results = send("test.event", {"key": "value"})
        assert len(captured) == 1
        assert captured[0] == {"key": "value"}
        assert "ok" in results

    def test_send_without_subscribers(self):
        results = send("unused.event", {"a": 1})
        assert results == []

    def test_core_events_defined(self):
        expected = {
            "invoice.posted",
            "payment.received",
            "asset.registered",
            "employee.hired",
            "stock.received",
            "facility.utility.reading",
        }
        assert CORE_EVENTS == expected

    def test_handler_exception_does_not_bubble(self):
        captured = []

        def failing_handler(data):
            raise RuntimeError("boom")

        def good_handler(data):
            captured.append(data)

        subscribe("test.errorevent", failing_handler)
        subscribe("test.errorevent", good_handler)

        send("test.errorevent", {"ok": True})
        assert len(captured) == 1


# ---------------------------------------------------------------------------
# Module Config Schema Validation
# ---------------------------------------------------------------------------


class TestModuleConfigSchema:
    def test_minimal_config(self):
        s = ModuleDetailSchema(
            name="Minimal",
            code="min",
            version="1.0.0",
            description="",
            dependencies=[],
            is_active=True,
            signals_emitted=[],
            signals_handled=[],
        )
        assert s.name == "Minimal"
        assert s.code == "min"

    def test_basic_module_detail(self):
        s = ModuleDetailSchema(
            name="Full",
            code="full",
            version="2.1.0",
            description="Everything",
            dependencies=["core"],
            is_active=False,
            signals_emitted=["full.event"],
            signals_handled=["invoice.posted"],
        )
        assert "full.event" in s.signals_emitted
        assert s.is_active is False
