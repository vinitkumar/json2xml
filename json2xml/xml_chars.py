"""XML 1.0 character policies for decoded JSON values."""

from __future__ import annotations

from enum import Enum
from typing import Any

from .types import JSONValue
from .utils import InvalidDataError

XML_REPLACEMENT_CHAR = "\uFFFD"


class InvalidXMLPolicy(str, Enum):
    """Action applied to characters forbidden by XML 1.0."""

    REJECT = "reject"
    REPLACE = "replace"
    ESCAPE = "escape"
    REMOVE = "remove"

    def __str__(self) -> str:
        return self.value


def is_xml10_char(character: str) -> bool:
    """Return whether one character belongs to the XML 1.0 Char production."""
    codepoint = ord(character)
    if codepoint in (0x09, 0x0A, 0x0D):
        return True
    if 0x20 <= codepoint <= 0xD7FF:
        return True
    if 0xE000 <= codepoint <= 0xFFFD:
        return True
    return 0x10000 <= codepoint <= 0x10FFFF


def _transform_text(value: str, policy: InvalidXMLPolicy) -> str:
    if value.isprintable():
        return value

    transformed: list[str] = []
    for character in value:
        if is_xml10_char(character):
            transformed.append(character)
            continue
        if policy is InvalidXMLPolicy.REPLACE:
            transformed.append(XML_REPLACEMENT_CHAR)
        elif policy is InvalidXMLPolicy.ESCAPE:
            transformed.append(f"\\u{ord(character):04X}")
        else:
            assert policy is InvalidXMLPolicy.REMOVE
    return "".join(transformed)


def transform_json_xml_chars(
    value: JSONValue, policy: InvalidXMLPolicy
) -> JSONValue:
    """Apply an explicit XML character policy without recursive traversal.

    Replacement applies to string values and object keys. A transformed-key
    collision raises `InvalidDataError` instead of silently losing a value.
    """
    if policy is InvalidXMLPolicy.REJECT:
        return value

    root: list[JSONValue] = [None]
    stack: list[tuple[JSONValue, Any, Any]] = [(value, root, 0)]
    while stack:
        current, parent, key = stack.pop()
        if isinstance(current, str):
            parent[key] = _transform_text(current, policy)
            continue
        if isinstance(current, list):
            transformed_list: list[JSONValue] = [None] * len(current)
            parent[key] = transformed_list
            stack.extend(
                (current[index], transformed_list, index)
                for index in range(len(current) - 1, -1, -1)
            )
            continue
        if isinstance(current, dict):
            transformed_dict: dict[str, JSONValue] = {}
            transformed_items: list[tuple[str, JSONValue]] = []
            for item_key, child in current.items():
                transformed_key = _transform_text(item_key, policy)
                if transformed_key in transformed_dict:
                    raise InvalidDataError(
                        "Invalid XML character replacement created a duplicate JSON key"
                    )
                transformed_dict[transformed_key] = None
                transformed_items.append((transformed_key, child))
            parent[key] = transformed_dict
            stack.extend(
                (child, transformed_dict, item_key)
                for item_key, child in reversed(transformed_items)
            )
            continue
        parent[key] = current

    return root[0]
