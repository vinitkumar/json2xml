#!/usr/bin/env python

"""Tests for `json2xml` package."""

import json

import pytest
import xmltodict
from pyexpat import ExpatError

from json2xml import json2xml
from json2xml.utils import (
    InvalidDataError,
    JSONReadError,
    StringReadError,
    URLReadError,
    readfromjson,
    readfromstring,
    readfromurl,
)

JSON_STRING = '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
INVALID_JSON_STRING = '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"'
text = "#text"

class TestJson2xml:
    """Tests for `json2xml` package."""

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

    def test_read_from_url(self) -> None:
        data = readfromurl("https://api.publicapis.org/entries")
        assert isinstance(data, dict)

    def test_read_from_wrong_url(self) -> None:
        with pytest.raises(URLReadError) as pytest_wrapped_e:
            readfromurl("https://api.publicapis.org/entriesi")
        assert pytest_wrapped_e.type == URLReadError

    def test_read_from_jsonstring(self) -> None:
        data = readfromstring(
            JSON_STRING
        )
        assert isinstance(data, dict)

    def test_read_from_invalid_string1(self) -> None:
        with pytest.raises(StringReadError) as pytest_wrapped_e:
            readfromstring(1)  # type: ignore
        assert pytest_wrapped_e.type == StringReadError

    def test_read_from_invalid_string2(self) -> None:
        with pytest.raises(StringReadError) as pytest_wrapped_e:
            readfromstring(jsondata=None) # type: ignore
        assert pytest_wrapped_e.type == StringReadError

    def test_read_from_invalid_jsonstring(self) -> None:
        with pytest.raises(StringReadError) as pytest_wrapped_e:
            readfromstring(INVALID_JSON_STRING)
        assert pytest_wrapped_e.type == StringReadError

    def test_json_to_xml_conversion(self) -> None:
        data = readfromstring(
            JSON_STRING
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
            JSON_STRING
        )
        xmldata = json2xml.Json2xml(data, wrapper="test", pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # test must be present, snce it is the wrpper
        assert "test" in old_dict.keys()
        # reverse test, say a wrapper called ramdom won't be present
        assert "random" not in old_dict.keys()

    def test_no_wrapper(self) -> None:
        data = readfromstring(
            JSON_STRING
        )
        xmldata = json2xml.Json2xml(data, root=False, pretty=False).to_xml()
        if xmldata:
            assert xmldata.startswith(b'<login type="str">mojombo</login>')
            pytest.raises(ExpatError, xmltodict.parse, xmldata)

    def test_item_wrap(self) -> None:
        data = readfromstring('{"my_items":[{"my_item":{"id":1} },{"my_item":{"id":2} }],"my_str_items":["a","b"]}')
        xmldata = json2xml.Json2xml(data, pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # item must be present within my_items
        assert "item" in old_dict["all"]["my_items"]
        assert "item" in old_dict["all"]["my_str_items"]

    def test_no_item_wrap(self) -> None:
        data = readfromstring('{"my_items":[{"my_item":{"id":1} },{"my_item":{"id":2} }],"my_str_items":["a","b"]}')
        xmldata = json2xml.Json2xml(data, pretty=False, item_wrap=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # my_item must be present within my_items
        assert "my_item" in old_dict["all"]["my_items"]
        assert "my_str_items" in old_dict["all"]

    def test_empty_array(self) -> None:
        data = readfromstring('{"empty_list":[]}')
        xmldata = json2xml.Json2xml(data, pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # item empty_list be present within all
        assert "empty_list" in old_dict["all"]

    def test_attrs(self) -> None:
        data = readfromstring(
            '{"my_string":"a","my_int":1,"my_float":1.1,"my_bool":true,"my_null":null,"empty_list":[],"empty_dict":{}}'
        )
        xmldata = json2xml.Json2xml(data, pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # test all attrs
        val_attr_type = "@type"
        assert "str" == old_dict["all"]["my_string"][val_attr_type]
        assert "int" == old_dict["all"]["my_int"][val_attr_type]
        assert "float" == old_dict["all"]["my_float"][val_attr_type]
        assert "bool" == old_dict["all"]["my_bool"][val_attr_type]
        assert "null" == old_dict["all"]["my_null"][val_attr_type]
        assert "list" == old_dict["all"]["empty_list"][val_attr_type]
        assert "dict" == old_dict["all"]["empty_dict"][val_attr_type]

    def test_dicttoxml_bug(self) -> None:
        input_dict = {
            "response": {
                "results": {
                    "user": [
                        {"name": "Ezequiel", "age": "33", "city": "San Isidro"},
                        {"name": "Belén", "age": "30", "city": "San Isidro"},
                    ]
                }
            }
        }

        xml_data = json2xml.Json2xml(
            input_dict, wrapper="response", pretty=False, attr_type=False, item_wrap=False
        ).to_xml()
        old_dict = xmltodict.parse(xml_data)
        assert "response" in old_dict.keys()

    def test_bad_data(self) -> None:
        data = b"!\0a8f"
        decoded = data.decode("utf-8")
        with pytest.raises(InvalidDataError) as pytest_wrapped_e:
            json2xml.Json2xml({"x": decoded}).to_xml()
        assert pytest_wrapped_e.type == InvalidDataError

    def test_read_boolean_data_from_json(self) -> None:
        """Test correct return for boolean types."""
        data = readfromjson("examples/booleanjson.json")
        result = json2xml.Json2xml(data).to_xml()
        dict_from_xml = xmltodict.parse(result)

        assert dict_from_xml["all"]["boolean"][text] != "True"
        assert dict_from_xml["all"]["boolean"][text] == "true"
        assert dict_from_xml["all"]["boolean_dict_list"]["item"][0]["boolean_dict"]["boolean"][text] == "true"
        assert dict_from_xml["all"]["boolean_dict_list"]["item"][1]["boolean_dict"]["boolean"][text] == "false"
        assert dict_from_xml["all"]["boolean_list"]["item"][0][text] == "true"
        assert dict_from_xml["all"]["boolean_list"]["item"][1][text] == "false"

    def test_read_boolean_data_from_json2(self) -> None:
        """Test correct return for boolean types."""
        data = readfromjson("examples/booleanjson2.json")
        result = json2xml.Json2xml(data).to_xml()
        dict_from_xml = xmltodict.parse(result)
        assert dict_from_xml["all"]["boolean_list"]["item"][0][text] != "True"
        assert dict_from_xml["all"]["boolean_list"]["item"][0][text] == "true"
        assert dict_from_xml["all"]["boolean_list"]["item"][1][text] == "false"
        assert dict_from_xml["all"]["number_array"]["item"][0][text] == "1"
        assert dict_from_xml["all"]["number_array"]["item"][1][text] == "2"
        assert dict_from_xml["all"]["number_array"]["item"][2][text] == "3"
        assert dict_from_xml["all"]["string_array"]["item"][0][text] == "a"
        assert dict_from_xml["all"]["string_array"]["item"][1][text] == "b"
        assert dict_from_xml["all"]["string_array"]["item"][2][text] == "c"

    def test_dict_attr_crash(self) -> None:
        data = data = {
            "product": {
                "@attrs": {"attr_name": "attr_value", "a": "b"},
                "@val": [],
            },
        }
        result = json2xml.Json2xml(data).to_xml()
        dict_from_xml = xmltodict.parse(result)
        assert dict_from_xml["all"]["product"]["@attr_name"] == "attr_value"
        assert dict_from_xml["all"]["product"]["@a"] == "b"
