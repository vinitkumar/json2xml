## 
# @file test.py
# @Synopsis  Unit test for json2xml
# @author Vinit Kumar
# @version 
# @date 2015-02-13


import unittest
from json2xml.json2xml import Json2xml

class Json2xmlTestCase(unittest.TestCase):

    def test_is_json_from_file_works(self):
        data = Json2xml.fromjsonfile('examples/example.json').data
        data_object = Json2xml(data)
        xml_output = data_object.json2xml()
        is_xml = xml_output.XML_ENTITIES
        self.assertEqual(is_xml, 'xml')

        
if __name__ == '__main__':
    unittest.main()
