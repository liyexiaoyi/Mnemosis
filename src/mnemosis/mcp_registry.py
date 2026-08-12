"""MCP tool handler registry (decorator-based)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

_TOOL_HANDLERS: dict[str, str] = {}

_F = TypeVar("_F", bound=Callable[..., Any])


def _tool(
    name: str,
) -> Callable[[_F], _F]:
    """Register a tool handler method on MCPServer."""

    def decorator(method: _F) -> _F:
        _TOOL_HANDLERS[name] = method.__name__
        return method

    return decorator


def registered_handlers() -> dict[str, str]:
    """Return the populated handler registry.

    Importing :mod:`mnemosis.mcp_handlers` forces the ``@_tool`` decorators
    to run, so callers never depend on import order.
    """
    from . import mcp_handlers as _handlers  # noqa: F401

    return dict(_TOOL_HANDLERS)


__all__ = ["registered_handlers"]
