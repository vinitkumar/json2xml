"""Shared JSON type aliases used by reader and converter APIs."""
from __future__ import annotations

from typing import TypeAlias

JSONValue: TypeAlias = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]

__all__ = ["JSONValue"]
