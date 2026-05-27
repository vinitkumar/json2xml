from __future__ import annotations

import numbers
from decimal import Decimal
from fractions import Fraction
from typing import Any

import pytest

from json2xml import dicttoxml


class CustomNumber(numbers.Number):
    def __complex__(self) -> complex:
        return complex(7)

    def __float__(self) -> float:
        return 7.0

    def __int__(self) -> int:
        return 7

    def __round__(self, ndigits: int | None = None) -> int:
        return 7


@pytest.mark.parametrize(
    ("value", "xml_type", "is_primitive"),
    [
        (None, "null", True),
        (False, "bool", True),
        (True, "bool", True),
        (1, "int", True),
        (3.5, "float", True),
        (Decimal("1.25"), "number", True),
        (Fraction(3, 4), "number", True),
        (CustomNumber(), "number", True),
        ({}, "dict", False),
        ([], "list", False),
    ],
)
def test_get_xml_type_and_primitive_classification(value: Any, xml_type: str, is_primitive: bool) -> None:
    assert dicttoxml.get_xml_type(value) == xml_type
    assert dicttoxml.is_primitive_type(value) is is_primitive


@pytest.mark.parametrize(
    "value",
    [
        "plain text",
        "rock & roll",
        "\"double\" and 'single'",
        "<tag>value</tag>",
        "mixed & <tag attr=\"value\">'text'</tag>",
    ],
)
def test_escape_xml_matches_full_replacement_chain(value: str) -> None:
    expected = (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    assert dicttoxml.escape_xml(value) == expected


@pytest.mark.parametrize(
    ("attrs", "expected"),
    [
        ({}, ""),
        ({"a": 1}, ' a="1"'),
        ({"type": "str"}, ' type="str"'),
        ({"type": "str", "id": 1}, ' type="str" id="1"'),
    ],
)
def test_make_attrstring_pins_spacing_and_order(attrs: dict[str, Any], expected: str) -> None:
    assert dicttoxml.make_attrstring(attrs) == expected


# @lat: [[tests#XML helper behavior#Valid-name helpers preserve caller attrs]]
def test_valid_name_helpers_set_type_without_mutating_caller_attrs() -> None:
    base_attrs = {"id": "shared"}

    assert (
        dicttoxml.convert_kv_valid_name("name", "Bike", True, base_attrs)
        == '<name id="shared" type="str">Bike</name>'
    )
    assert base_attrs == {"id": "shared"}

    assert (
        dicttoxml.convert_bool_valid_name("active", False, True, base_attrs)
        == '<active id="shared" type="bool">false</active>'
    )
    assert base_attrs == {"id": "shared"}

    assert (
        dicttoxml.convert_none_valid_name("empty", True, base_attrs)
        == '<empty id="shared" type="null"></empty>'
    )
    assert base_attrs == {"id": "shared"}


def test_valid_name_helpers_keep_existing_attrs_without_attr_type() -> None:
    base_attrs = {"name": "invalid key"}

    assert (
        dicttoxml.convert_kv_valid_name("key", "Bike", False, base_attrs)
        == '<key name="invalid key">Bike</key>'
    )
    assert dicttoxml.convert_bool_valid_name("key", True, False, base_attrs) == '<key name="invalid key">true</key>'
    assert dicttoxml.convert_none_valid_name("key", False, base_attrs) == '<key name="invalid key"></key>'
    assert base_attrs == {"name": "invalid key"}


# @lat: [[tests#XML helper behavior#XML name validity fast and cached paths]]
def test_key_is_valid_xml_fast_and_parse_paths_are_stable_under_cache() -> None:
    dicttoxml.key_is_valid_xml.cache_clear()

    cases = {
        "foo": True,
        "_bar-1": True,
        "café": True,
        "éclair": True,
        "1foo": False,
        "foo:bar": False,
        "": False,
    }

    first = {key: dicttoxml.key_is_valid_xml(key) for key in cases}
    second = {key: dicttoxml.key_is_valid_xml(key) for key in reversed(cases)}

    assert first == cases
    assert second == cases
    cache_info = dicttoxml.key_is_valid_xml.cache_info()
    assert cache_info.hits >= len(cases)
