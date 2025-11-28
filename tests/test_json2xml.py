#!/usr/bin/env python

"""Tests for `json2xml` package."""

import json
from pyexpat import ExpatError

import pytest
import xmltodict

from json2xml import json2xml
from json2xml.utils import (
    InvalidDataError,
    JSONReadError,
    StringReadError,
    readfromjson,
    readfromstring,
)


class TestJson2xml:
    """Tests for `json2xml` package."""

    def setUp(self) -> None:
        """Set up test fixtures, if any."""

    def tearDown(self) -> None:
        """Tear down test fixtures, if any."""

    def test_read_from_json(self) -> None:
        """Test something."""
        data = readfromjson("examples/bigexample.json")
        if isinstance(data, list):
            # it's json array, so we just take the first element and check it's type
            assert isinstance(data[0], dict)
        else:
            data = readfromjson("examples/licht.json")
            assert isinstance(data, dict)

    def test_read_from_invalid_json(self) -> None:
        """Test something."""
        with pytest.raises(JSONReadError) as pytest_wrapped_e:
            readfromjson("examples/licht_wrong.json")
        assert pytest_wrapped_e.type == JSONReadError

    def test_read_from_invalid_json2(self) -> None:
        with pytest.raises(JSONReadError) as pytest_wrapped_e:
            readfromjson("examples/wrongjson.json")
        assert pytest_wrapped_e.type == JSONReadError

    def test_read_from_jsonstring(self) -> None:
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        assert isinstance(data, dict)

    def test_read_from_invalid_string1(self) -> None:
        with pytest.raises(StringReadError) as pytest_wrapped_e:
            readfromstring(1)  # type: ignore[arg-type]
        assert pytest_wrapped_e.type == StringReadError

    def test_read_from_invalid_string2(self) -> None:
        with pytest.raises(StringReadError) as pytest_wrapped_e:
            readfromstring(jsondata=None)  # type: ignore[arg-type]
        assert pytest_wrapped_e.type == StringReadError

    def test_read_from_invalid_jsonstring(self) -> None:
        with pytest.raises(StringReadError) as pytest_wrapped_e:
            readfromstring(
                '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"'
            )
        assert pytest_wrapped_e.type == StringReadError

    def test_json_to_xml_conversion(self) -> None:
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        xmldata = json2xml.Json2xml(data).to_xml()
        dict_from_xml = xmltodict.parse(xmldata)
        assert isinstance(dict_from_xml["all"], dict)

    def test_json_to_xml_empty_data_conversion(self) -> None:
        data = None
        xmldata = json2xml.Json2xml(data).to_xml()
        assert xmldata is None

    def test_custom_wrapper_and_indent(self) -> None:
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        xmldata = json2xml.Json2xml(data, wrapper="test", pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # test must be present, snce it is the wrpper
        assert "test" in old_dict.keys()
        # reverse test, say a wrapper called ramdom won't be present
        assert "random" not in old_dict.keys()

    def test_no_wrapper(self) -> None:
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        xmldata = json2xml.Json2xml(data, root=False, pretty=False).to_xml()
        if xmldata:
            assert xmldata.startswith(b'<login type="str">mojombo</login>')
        pytest.raises(ExpatError, xmltodict.parse, xmldata)

    def test_item_wrap(self) -> None:
        data = readfromstring(
            '{"my_items":[{"my_item":{"id":1} },{"my_item":{"id":2} }],"my_str_items":["a","b"]}'
        )
        xmldata = json2xml.Json2xml(data, pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # item must be present within my_items
        assert "item" in old_dict['all']['my_items']
        assert "item" in old_dict['all']['my_str_items']

    def test_no_item_wrap(self) -> None:
        data = readfromstring(
            '{"my_items":[{"my_item":{"id":1} },{"my_item":{"id":2} }],"my_str_items":["a","b"]}'
        )
        xmldata = json2xml.Json2xml(data, pretty=False, item_wrap=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # my_item must be present within my_items
        assert "my_item" in old_dict['all']['my_items']
        assert "my_str_items" in old_dict['all']

    def test_empty_array(self) -> None:
        data = readfromstring(
            '{"empty_list":[]}'
        )
        xmldata = json2xml.Json2xml(data, pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # item empty_list be present within all
        assert "empty_list" in old_dict['all']

    def test_attrs(self) -> None:
        data = readfromstring(
            '{"my_string":"a","my_int":1,"my_float":1.1,"my_bool":true,"my_null":null,"empty_list":[],"empty_dict":{}}'
        )
        xmldata = json2xml.Json2xml(data, pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # test all attrs
        assert "str" == old_dict['all']['my_string']['@type']
        assert "int" == old_dict['all']['my_int']['@type']
        assert "float" == old_dict['all']['my_float']['@type']
        assert "bool" == old_dict['all']['my_bool']['@type']
        assert "null" == old_dict['all']['my_null']['@type']
        assert "list" == old_dict['all']['empty_list']['@type']
        assert "dict" == old_dict['all']['empty_dict']['@type']

    def test_dicttoxml_bug(self) -> None:
        input_dict = {
            'response': {
                'results': {
                    'user': [{
                        'name': 'Ezequiel', 'age': '33', 'city': 'San Isidro'
                    }, {
                        'name': 'Belén', 'age': '30', 'city': 'San Isidro'}]}}}

        xmldata = json2xml.Json2xml(
            input_dict, wrapper='response', pretty=False, attr_type=False, item_wrap=False
        ).to_xml()

        old_dict = xmltodict.parse(xmldata)
        assert 'response' in old_dict.keys()

    def test_bad_data(self) -> None:
        data = b"!\0a8f"
        decoded = data.decode("utf-8")
        with pytest.raises(InvalidDataError) as pytest_wrapped_e:
            json2xml.Json2xml({"bad": decoded}).to_xml()
        assert pytest_wrapped_e.type == InvalidDataError

    def test_read_boolean_data_from_json(self) -> None:
        """Test correct return for boolean types."""
        data = readfromjson("examples/booleanjson.json")
        result = json2xml.Json2xml(data).to_xml()
        dict_from_xml = xmltodict.parse(result)
        assert dict_from_xml["all"]["boolean"]["#text"] != 'True'
        assert dict_from_xml["all"]["boolean"]["#text"] == 'true'
        assert dict_from_xml["all"]["boolean_dict_list"]["item"][0]["boolean_dict"]["boolean"]["#text"] == 'true'
        assert dict_from_xml["all"]["boolean_dict_list"]["item"][1]["boolean_dict"]["boolean"]["#text"] == 'false'
        assert dict_from_xml["all"]["boolean_list"]["item"][0]["#text"] == 'true'
        assert dict_from_xml["all"]["boolean_list"]["item"][1]["#text"] == 'false'

    def test_read_boolean_data_from_json2(self) -> None:
        """Test correct return for boolean types."""
        data = readfromjson("examples/booleanjson2.json")
        result = json2xml.Json2xml(data).to_xml()
        dict_from_xml = xmltodict.parse(result)
        assert dict_from_xml["all"]["boolean_list"]["item"][0]["#text"] != 'True'
        assert dict_from_xml["all"]["boolean_list"]["item"][0]["#text"] == 'true'
        assert dict_from_xml["all"]["boolean_list"]["item"][1]["#text"] == 'false'
        assert dict_from_xml["all"]["number_array"]["item"][0]["#text"] == '1'
        assert dict_from_xml["all"]["number_array"]["item"][1]["#text"] == '2'
        assert dict_from_xml["all"]["number_array"]["item"][2]["#text"] == '3'
        assert dict_from_xml["all"]["string_array"]["item"][0]["#text"] == 'a'
        assert dict_from_xml["all"]["string_array"]["item"][1]["#text"] == 'b'
        assert dict_from_xml["all"]["string_array"]["item"][2]["#text"] == 'c'

    def test_dict_attr_crash(self) -> None:
        data = {
            "product": {
                "@attrs": {
                    "attr_name": "attr_value",
                    "a": "b"
                },
                "@val": [],
            },
        }
        result = json2xml.Json2xml(data).to_xml()
        dict_from_xml = xmltodict.parse(result)
        assert dict_from_xml["all"]["product"]["@attr_name"] == "attr_value"
        assert dict_from_xml["all"]["product"]["@a"] == "b"

    def test_encoding_pretty_print(self) -> None:
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        xmldata = json2xml.Json2xml(data, pretty=True).to_xml()
        if xmldata:
            assert 'encoding="UTF-8"' in xmldata

    def test_encoding_without_pretty_print(self) -> None:
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        xmldata = json2xml.Json2xml(data, pretty=False).to_xml()
        if xmldata:
            assert b'encoding="UTF-8"' in xmldata

    def test_xpath_format_basic(self) -> None:
        """Test XPath 3.1 json-to-xml format with basic types."""
        data = {"name": "John", "age": 30, "active": True}
        xmldata = json2xml.Json2xml(data, xpath_format=True, pretty=False).to_xml()
        if xmldata:
            assert b'xmlns="http://www.w3.org/2005/xpath-functions"' in xmldata
            assert b'<string key="name">John</string>' in xmldata
            assert b'<number key="age">30</number>' in xmldata
            assert b'<boolean key="active">true</boolean>' in xmldata

    def test_xpath_format_nested_dict(self) -> None:
        """Test XPath 3.1 format with nested dictionaries."""
        data = {"person": {"name": "Alice", "age": 25}}
        xmldata = json2xml.Json2xml(data, xpath_format=True, pretty=False).to_xml()
        if xmldata:
            assert b'<map key="person">' in xmldata
            assert b'<string key="name">Alice</string>' in xmldata
            assert b'<number key="age">25</number>' in xmldata

    def test_xpath_format_array(self) -> None:
        """Test XPath 3.1 format with arrays."""
        data = {"numbers": [1, 2, 3]}
        xmldata = json2xml.Json2xml(data, xpath_format=True, pretty=False).to_xml()
        if xmldata:
            assert b'<array key="numbers">' in xmldata
            assert b'<number>1</number>' in xmldata
            assert b'<number>2</number>' in xmldata
            assert b'<number>3</number>' in xmldata

    def test_xpath_format_null(self) -> None:
        """Test XPath 3.1 format with null values."""
        data = {"value": None}
        xmldata = json2xml.Json2xml(data, xpath_format=True, pretty=False).to_xml()
        if xmldata:
            assert b'<null key="value"/>' in xmldata

    def test_xpath_format_mixed_array(self) -> None:
        """Test XPath 3.1 format with mixed type arrays."""
        data = {"items": ["text", 42, True, None]}
        xmldata = json2xml.Json2xml(data, xpath_format=True, pretty=False).to_xml()
        if xmldata:
            assert b'<array key="items">' in xmldata
            assert b'<string>text</string>' in xmldata
            assert b'<number>42</number>' in xmldata
            assert b'<boolean>true</boolean>' in xmldata
            assert b'<null/>' in xmldata

    def test_xpath_format_complex_nested(self) -> None:
        """Test XPath 3.1 format with complex nested structures."""
        data = {
            "content": [
                {"id": 70805774, "value": "1001", "position": [1004.0, 288.0]},
            ]
        }
        xmldata = json2xml.Json2xml(data, xpath_format=True, pretty=False).to_xml()
        if xmldata:
            assert b'<array key="content">' in xmldata
            assert b'<number key="id">70805774</number>' in xmldata
            assert b'<string key="value">1001</string>' in xmldata
            assert b'<array key="position">' in xmldata
            assert b'<number>1004.0</number>' in xmldata

    def test_xpath_format_escaping(self) -> None:
        """Test XPath 3.1 format properly escapes special characters."""
        data = {"text": "<script>alert('xss')</script>"}
        xmldata = json2xml.Json2xml(data, xpath_format=True, pretty=False).to_xml()
        if xmldata:
            assert b"&lt;script&gt;" in xmldata
            assert b"&apos;xss&apos;" in xmldata

    def test_xpath_format_with_pretty_print(self) -> None:
        """Test XPath 3.1 format works with pretty printing."""
        data = {"name": "Test"}
        xmldata = json2xml.Json2xml(data, xpath_format=True, pretty=True).to_xml()
        if xmldata:
            assert 'xmlns="http://www.w3.org/2005/xpath-functions"' in xmldata
            assert '<string key="name">Test</string>' in xmldata

    def test_xpath_format_root_array(self) -> None:
        """Test XPath 3.1 format with root-level array."""
        data = [1, 2, 3]
        xmldata = json2xml.Json2xml(data, xpath_format=True, pretty=False).to_xml()
        if xmldata:
            assert b'<array xmlns="http://www.w3.org/2005/xpath-functions">' in xmldata
            assert b'<number>1</number>' in xmldata
