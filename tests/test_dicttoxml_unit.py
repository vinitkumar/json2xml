from __future__ import annotations

import datetime
import numbers
from decimal import Decimal
from fractions import Fraction
from typing import Any
from unittest.mock import Mock

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


class StringSubclass(str):
    pass


class IntSubclass(int):
    pass


class DictSubclass(dict[str, Any]):
    pass


class ListSubclass(list[Any]):
    pass


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
def test_get_xml_type_and_primitive_classification(
    value: Any, xml_type: str, is_primitive: bool
) -> None:
    assert dicttoxml.get_xml_type(value) == xml_type
    assert dicttoxml.is_primitive_type(value) is is_primitive


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, True),
        (3.5, True),
        (1 + 2j, True),
        (Decimal("1.25"), True),
        (Fraction(3, 4), True),
        (CustomNumber(), True),
        (True, False),
        ("1", False),
    ],
)
# @lat: [[tests#XML helper behavior#Numeric fast path preserves general Number support]]
def test_number_classifier_preserves_supported_number_types(
    value: Any, expected: bool
) -> None:
    assert dicttoxml._is_number(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (StringSubclass("value"), "str"),
        (DictSubclass(), "dict"),
        (ListSubclass(), "list"),
    ],
)
def test_get_xml_type_preserves_container_subclasses(value: Any, expected: str) -> None:
    assert dicttoxml.get_xml_type(value) == expected


# @lat: [[tests#XML helper behavior#Exact-type dispatch preserves subclass fallbacks]]
def test_exact_type_dispatch_preserves_subclass_fallbacks() -> None:
    data = DictSubclass({"values": ListSubclass([IntSubclass(7)])})

    assert dicttoxml.dicttoxml(data) == (
        b'<?xml version="1.0" encoding="UTF-8" ?>'
        b'<root><values type="list"><item type="number">7</item></values></root>'
    )


# @lat: [[tests#Type dispatch#Date-like values serialize the same in every position]]
def test_date_like_values_serialize_identically_in_every_position() -> None:
    moment = datetime.time(12, 30)
    expected = b"12:30:00"

    assert expected in dicttoxml.dicttoxml({"t": moment})
    assert expected in dicttoxml.dicttoxml([moment])
    assert (
        dicttoxml.dicttoxml(moment, root=False, attr_type=False)
        == b"<item>12:30:00</item>"
    )


def test_falsy_unsupported_objects_raise_instead_of_becoming_null() -> None:
    class FalsyUnsupported:
        def __len__(self) -> int:
            return 0

    with pytest.raises(TypeError, match="Unsupported data type"):
        dicttoxml.dicttoxml({"value": FalsyUnsupported()})


def test_convert_preserves_root_scalar_and_sequence_subclasses() -> None:
    def item_func(_parent: str) -> str:
        return "item"

    assert dicttoxml.convert(IntSubclass(7), [], True, item_func, False, True) == (
        '<item type="number">7</item>'
    )
    assert dicttoxml.convert(ListSubclass([1]), [], True, item_func, False, True) == (
        '<item type="int">1</item>'
    )


def test_nested_subclasses_match_compatible_serializer_shapes() -> None:
    def item_func(_parent: str) -> str:
        return "item"

    assert dicttoxml.convert_dict(
        {"text": StringSubclass("value"), "mapping": DictSubclass({"count": 1})},
        [],
        "root",
        True,
        item_func,
        False,
        True,
    ) == (
        '<text type="str">value</text><mapping type="dict"><count type="int">1</count></mapping>'
    )
    assert dicttoxml.convert_list(
        [DictSubclass({"count": 1}), ListSubclass([2])],
        [],
        "items",
        True,
        item_func,
        False,
        True,
    ) == (
        '<item type="dict"><count type="int">1</count></item><item type="list"><item type="int">2</item></item>'
    )
    assert (
        dicttoxml.convert_list(
            [IntSubclass(7)],
            None,
            "bad&parent",
            True,
            item_func,
            False,
            False,
        )
        == '<key name="bad&amp;parent" type="number">7</key>'
    )


def test_raw_attribute_values_preserve_mapping_subclasses() -> None:
    assert (
        dicttoxml.dict2xml_str(
            attr_type=False,
            attr={},
            item={"@attrs": {"source": "api"}, "@val": DictSubclass({"count": 1})},
            item_func=lambda _parent: "item",
            cdata=False,
            item_name="field",
            item_wrap=True,
            parentIsList=False,
        )
        == '<field source="api"><count>1</count></field>'
    )


def test_pretty_output_limit_counts_trailing_newline() -> None:
    rendered = dicttoxml.dicttoxml({"name": "Ada"}, indent="  ")

    assert rendered.endswith(b"\n")
    assert dicttoxml.dicttoxml(
        {"name": "Ada"}, indent="  ", max_output_bytes=len(rendered)
    ) == rendered
    with pytest.raises(ValueError, match="XML output size limit exceeded"):
        dicttoxml.dicttoxml(
            {"name": "Ada"}, indent="  ", max_output_bytes=len(rendered) - 1
        )


@pytest.mark.parametrize(
    ("value", "expected_text"),
    [
        (StringSubclass("A & B"), b"A &amp; B"),
        (IntSubclass(7), b"7"),
    ],
)
# @lat: [[tests#Conversion behavior#Raw attribute values preserve scalar subclasses]]
def test_raw_attribute_values_preserve_scalar_subclasses(
    value: str | int, expected_text: bytes
) -> None:
    assert dicttoxml.dicttoxml(
        {"field": {"@attrs": {"source": "api"}, "@val": value}}
    ) == (
        b'<?xml version="1.0" encoding="UTF-8" ?><root><field source="api">'
        + expected_text
        + b"</field></root>"
    )


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
def test_make_attrstring_pins_spacing_and_order(
    attrs: dict[str, Any], expected: str
) -> None:
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


def test_public_scalar_helpers_do_not_mutate_caller_attrs() -> None:
    converters = (
        lambda attrs: dicttoxml.convert_kv("invalid&key", "Bike", True, attrs),
        lambda attrs: dicttoxml.convert_bool("invalid&key", True, True, attrs),
        lambda attrs: dicttoxml.convert_none("invalid&key", True, attrs),
    )

    for convert in converters:
        attrs = {"id": "shared"}

        result = convert(attrs)

        assert 'name="invalid&amp;key"' in result
        assert 'type="' in result
        assert attrs == {"id": "shared"}


def test_valid_name_helpers_keep_existing_attrs_without_attr_type() -> None:
    base_attrs = {"name": "invalid key"}

    assert (
        dicttoxml.convert_kv_valid_name("key", "Bike", False, base_attrs)
        == '<key name="invalid key">Bike</key>'
    )
    assert (
        dicttoxml.convert_bool_valid_name("key", True, False, base_attrs)
        == '<key name="invalid key">true</key>'
    )
    assert (
        dicttoxml.convert_none_valid_name("key", False, base_attrs)
        == '<key name="invalid key"></key>'
    )
    assert base_attrs == {"name": "invalid key"}


# @lat: [[tests#XML helper behavior#Typed attributes preserve caller attrs]]
def test_valid_name_helpers_replace_type_attr_without_mutating_caller_attrs() -> None:
    base_attrs = {"type": "caller", "id": "shared"}

    assert (
        dicttoxml.convert_kv_valid_name("name", "Bike", True, base_attrs)
        == '<name type="str" id="shared">Bike</name>'
    )
    assert (
        dicttoxml.convert_bool_valid_name("active", True, True, base_attrs)
        == '<active type="bool" id="shared">true</active>'
    )
    assert (
        dicttoxml.convert_none_valid_name("empty", True, base_attrs)
        == '<empty type="null" id="shared"></empty>'
    )
    assert base_attrs == {"type": "caller", "id": "shared"}

    only_type = {"type": "caller"}
    assert (
        dicttoxml.convert_bool_valid_name("active", False, True, only_type)
        == '<active type="bool">false</active>'
    )
    assert only_type == {"type": "caller"}

    metadata_attrs = {"id": "shared", "name": "invalid key"}
    assert (
        dicttoxml.convert_none_valid_name("empty", True, metadata_attrs)
        == '<empty id="shared" name="invalid key" type="null"></empty>'
    )
    assert metadata_attrs == {"id": "shared", "name": "invalid key"}


# @lat: [[tests#XML helper behavior#Container helpers preserve caller attrs]]
def test_container_helpers_set_type_without_mutating_caller_attrs() -> None:
    dict_attrs = {"id": "shared"}
    list_attrs = {"id": "shared"}

    assert (
        dicttoxml.dict2xml_str(
            attr_type=True,
            attr=dict_attrs,
            item={"name": "Bike"},
            item_func=lambda _parent: "item",
            cdata=False,
            item_name="product",
            item_wrap=True,
            parentIsList=False,
        )
        == '<product id="shared" type="dict"><name type="str">Bike</name></product>'
    )
    assert dict_attrs == {"id": "shared"}

    assert (
        dicttoxml.list2xml_str(
            attr_type=True,
            attr=list_attrs,
            item=["Bike"],
            item_func=lambda _parent: "item",
            cdata=False,
            item_name="products",
            item_wrap=True,
        )
        == '<products id="shared" type="list"><item type="str">Bike</item></products>'
    )
    assert list_attrs == {"id": "shared"}


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


# @lat: [[tests#XML helper behavior#XML attribute name validation]]
def test_xml_attribute_name_validation_accepts_only_parser_valid_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dicttoxml.key_is_valid_xml_attr.cache_clear()
    from defusedxml.minidom import parseString

    parse_string = Mock(wraps=parseString)
    monkeypatch.setattr("defusedxml.minidom.parseString", parse_string)

    cases = {
        "a_b": True,
        "a-b": True,
        "xmlAttr": True,
        "": False,
        "1foo": False,
        "foo>bar": False,
        'foo"bar': False,
        "foo\nbar": False,
    }

    first = {key: dicttoxml.key_is_valid_xml_attr(key) for key in cases}
    second = {key: dicttoxml.key_is_valid_xml_attr(key) for key in reversed(cases)}

    assert first == cases
    assert second == cases
    assert parse_string.call_count == 4
    dicttoxml.validate_xml_attr_names(
        {key: "value" for key, is_valid in cases.items() if is_valid}
    )
    for key, is_valid in cases.items():
        if not is_valid:
            with pytest.raises(ValueError, match="Invalid XML attribute name"):
                dicttoxml.validate_xml_attr_names({key: "value"})
