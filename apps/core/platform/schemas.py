"""Module configuration schema — validates industry module registration payloads."""

from typing import Any

from ninja import Schema


class ModuleConfigSchema(Schema):
    name: str
    code: str
    version: str = "1.0.0"
    description: str = ""
    dependencies: list[str] = []
    menu_items: list[dict[str, Any]] = []
    page_configs: list[dict[str, Any]] = []
    workflows: list[dict[str, Any]] = []
    gl_accounts: list[dict[str, Any]] = []
    signals_emitted: list[str] = []
    signals_handled: list[str] = []


class ModuleDetailSchema(Schema):
    code: str
    name: str
    version: str
    description: str
    dependencies: list[str]
    is_active: bool
    signals_emitted: list[str]
    signals_handled: list[str]
