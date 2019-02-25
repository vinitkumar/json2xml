#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `json2xml` package."""


import unittest
import pytest
import xmltodict

from collections import OrderedDict
from json2xml import json2xml, readfromjson, readfromstring, readfromurl


class TestJson2xml(unittest.TestCase):
    """Tests for `json2xml` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_read_from_json(self):
        """Test something."""
        data = readfromjson("examples/licht.json")
        assert type(data) is dict

    def test_read_from_invalid_json(self):
        """Test something."""
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            data = readfromjson("examples/licht_wrong.json")
        assert pytest_wrapped_e.type == SystemExit

    def test_read_from_url(self):
        data = readfromurl("https://coderwall.com/vinitcool76.json")
        assert type(data) is dict

    def test_read_from_wrong_url(self):
        """
        Use wrong url and check if there is a sytemExit
        """
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            data = readfromurl("https://coderwall.com/vinitcool76.jsoni")
        print("type is ", pytest_wrapped_e.type)
        assert pytest_wrapped_e.type == SystemExit

    def test_read_from_jsonstring(self):
        data = readfromstring(
            '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
        )
        assert type(data) is dict

    def test_read_from_invalid_jsonstring(self):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            data = readfromstring(
                '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"'
            )
        assert pytest_wrapped_e.type == SystemExit

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
        xmldata = json2xml.Json2xml(data, wrapper="test", indent=8).to_xml()
        old_dict = xmltodict.parse(xmldata)
        # test must be present, snce it is the wrpper
        assert "test" in old_dict.keys()
        # reverse test, say a wrapper called ramdom won't be present
        assert "random" not in old_dict.keys()
