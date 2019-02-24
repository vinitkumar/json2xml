#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `json2xml` package."""


import unittest

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

    def test_read_from_url(self):
        data = readfromurl("https://coderwall.com/vinitcool76.json")
        assert type(data) is dict
