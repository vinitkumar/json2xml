##
# @file test.py
# @Synopsis  Unit test for json2xml
# @author Vinit Kumar
# @version
# @date 2015-02-13


import unittest
from collections import OrderedDict

import xmltodict

from src.json2xml import Json2xml


class Json2xmlTestCase(unittest.TestCase):
    def test_json_from_file_works(self):
        data = Json2xml.fromjsonfile('examples/example.json').data
        data_object = Json2xml(data)
        xml_output = data_object.json2xml()
        dict_from_xml = xmltodict.parse(xml_output)
        # since it's a valid XML, xml to dict is able to load it and return
        # elements from under the all tag of xml
        self.assertTrue(type(dict_from_xml['all']) == OrderedDict)

    def test_json_from_url(self):
        data = Json2xml.fromurl('https://coderwall.com/vinitcool76.json').data
        data_object = Json2xml(data)
        xml_output = data_object.json2xml()
        dict_from_xml = xmltodict.parse(xml_output)
        # since it's a valid XML, xml to dict is able to load it and return
        # elements from under the all tag of xml
        self.assertTrue(type(dict_from_xml['all']) == OrderedDict)

    def test_json_from_string(self):
        data = Json2xml.fromstring('{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}').data
        data_object = Json2xml(data)
        xml_output = data_object.json2xml()
        dict_from_xml = xmltodict.parse(xml_output)
        print('keys', dict_from_xml)
        # since it's a valid XML, xml to dict is able to load it and return
        # elements from under the all tag of xml
        self.assertTrue(type(dict_from_xml['all']) == OrderedDict)



if __name__ == '__main__':
    unittest.main()
