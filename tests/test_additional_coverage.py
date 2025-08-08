import decimal
from typing import Any

import pytest

from json2xml import dicttoxml


class TestAdditionalCoverage:
    def test_wrap_cdata_handles_cdata_end(self) -> None:
        # Ensure CDATA splitting works for "]]>" sequence
        text = "a]]>b"
        wrapped = dicttoxml.wrap_cdata(text)
        assert wrapped == "<![CDATA[a]]]]><![CDATA[>b]]>"

    def test_make_valid_xml_name_with_int_key(self) -> None:
        # Int keys should be converted to n<digits>
        key, attr = dicttoxml.make_valid_xml_name(123, {})  # type: ignore[arg-type]
        assert key == "n123"
        assert attr == {}

    def test_make_valid_xml_name_namespace_flat(self) -> None:
        # Namespaced key with @flat suffix should be considered valid as-is
        key_in = "ns:key@flat"
        key_out, attr = dicttoxml.make_valid_xml_name(key_in, {})
        assert key_out == key_in
        assert attr == {}

    def test_dict2xml_str_parent_list_with_attrs_and_no_wrap(self) -> None:
        # When inside list context with list_headers=True and item_wrap=False,
        # attributes belong to the parent element header
        item = {"@attrs": {"a": "b"}, "@val": "X"}
        xml = dicttoxml.dict2xml_str(
            attr_type=False,
            attr={},
            item=item,
            item_func=lambda _p: "item",
            cdata=False,
            item_name="ignored",
            item_wrap=False,
            parentIsList=True,
            parent="Parent",
            list_headers=True,
        )
        assert xml == '<Parent a="b">X</Parent>'

    def test_dict2xml_str_with_flat_flag_in_item(self) -> None:
        # If @flat=True, the subtree should not be wrapped
        item = {"@val": "text", "@flat": True}
        xml = dicttoxml.dict2xml_str(
            attr_type=False,
            attr={},
            item=item,
            item_func=lambda _p: "item",
            cdata=False,
            item_name="ignored",
            item_wrap=True,
            parentIsList=False,
        )
        assert xml == "text"

    def test_list2xml_str_returns_subtree_when_list_headers_true(self) -> None:
        # list_headers=True should return subtree directly from convert_list
        xml = dicttoxml.list2xml_str(
            attr_type=False,
            attr={},
            item=["a"],
            item_func=lambda _p: "item",
            cdata=False,
            item_name="test",
            item_wrap=True,
            list_headers=True,
        )
        assert xml == "<item>a</item>"

    def test_get_xml_type_with_decimal_number(self) -> None:
        # Decimal is a numbers.Number but not int/float
        value = decimal.Decimal("5")
        assert dicttoxml.get_xml_type(value) == "number"
        # And convert_kv should mark it as type="number"
        out = dicttoxml.convert_kv("key", value, attr_type=True)
        assert out == '<key type="number">5</key>'

    def test_dicttoxml_cdata_with_cdata_end_sequence(self) -> None:
        data = {"key": "a]]>b"}
        out = dicttoxml.dicttoxml(data, root=False, attr_type=False, cdata=True).decode()
        assert out == "<key><![CDATA[a]]]]><![CDATA[>b]]></key>"

    def test_convert_dict_with_ids_adds_id_attributes(self) -> None:
        obj: dict[str, Any] = {"a": 1, "b": 2}
        xml = dicttoxml.convert_dict(
            obj=obj,
            ids=["seed"],
            parent="root",
            attr_type=False,
            item_func=lambda _p: "item",
            cdata=False,
            item_wrap=True,
        )
        # Both elements should carry some id attribute
        assert xml.count(' id="') == 2
