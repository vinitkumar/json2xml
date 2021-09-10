#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `json2xml` package."""


import unittest
from collections import OrderedDict
import pytest
import xmltodict

from json2xml import json2xml
from json2xml.utils import readfromjson, readfromstring, readfromurl, JSONReadError, StringReadError, URLReadError


class TestJson2xml(unittest.TestCase):
    """Tests for `json2xml` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_read_from_json(self):
        """Test something."""
        data = readfromjson("examples/bigexample.json")
        if type(data) == 'list':
            # it's json array, so we just take the first element and check it's type
            assert type(data[0]) is dict
        else:
            data = readfromjson("examples/licht.json")
            assert type(data) is dict

    def test_read_from_invalid_json(self):
        """Test something."""
        with pytest.raises(JSONReadError) as pytest_wrapped_e:
            data = readfromjson("examples/licht_wrong.json")
        assert pytest_wrapped_e.type == JSONReadError

    def test_read_from_url(self):
        data = readfromurl("https://coderwall.com/vinitcool76.json")
        assert type(data) is dict

    def test_read_from_wrong_url(self):
        with pytest.raises(URLReadError) as pytest_wrapped_e:
            data = readfromurl("https://coderwall.com/vinitcool76.jsoni")
        assert pytest_wrapped_e.type == URLReadError

    def test_read_from_jsonstring(self):
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        assert type(data) is dict

    def test_read_from_invalid_jsonstring(self):
        with pytest.raises(StringReadError) as pytest_wrapped_e:
            data = readfromstring(
                '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"'
            )
        assert pytest_wrapped_e.type == StringReadError

    def test_json_to_xml_conversion(self):
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        xmldata = json2xml.Json2xml(data).to_xml()
        dict_from_xml = xmltodict.parse(xmldata)
        assert type(dict_from_xml["all"]) == OrderedDict

    def test_custom_wrapper_and_indent(self):
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        xmldata = json2xml.Json2xml(data, root=False, wrapper="test", pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # test must be present, snce it is the wrpper
        assert "test" in old_dict.keys()
        # reverse test, say a wrapper called ramdom won't be present
        assert "random" not in old_dict.keys()

    def test_no_wrapper_and_indent(self):
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        xmldata = json2xml.Json2xml(data, root=False, wrapper="test", pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # test must be present, snce it is the wrpper
        assert "test" in old_dict.keys()
        # reverse test, say a wrapper called ramdom won't be present
        assert "random" not in old_dict.keys()

    def test_item_wrap(self):
        data = readfromstring(
            '{"my_items":[{"my_item":{"id":1} },{"my_item":{"id":2} }]}'
        )
        xmldata = json2xml.Json2xml(data, root=False, pretty=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # item must be present within my_items
        assert "item" in old_dict['all']['my_items']

        xmldata = json2xml.Json2xml(data, root=False, pretty=False, item_wrap=False, attr_type=False).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # my_item must be present within my_items
        assert "my_item" in old_dict['all']['my_items']

        xmldata = json2xml.Json2xml(data, root=False, pretty=False, item_wrap=False).to_xml()
        print(xmldata)
        old_dict = xmltodict.parse(xmldata)
        # my_item must be present within my_items
        print(old_dict['all']['my_items'])
        assert "my_item" in old_dict['all']['my_items']
