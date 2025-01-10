import pytest
import json

from json2xml import dicttoxml, json2xml



class TestEscaping:
    def test_escaping(self):
        # Test cases
        test_cases = [
            {
                "root": {
                    "@attrs": {
                        "Text": "this & that"
                    }
                }
            },
            {
                "data": json.dumps({"key": "value & more"})
            },
            {
                "mixed": {
                    "json_str": json.dumps({"a": "b & c"}),
                    "plain": "text & symbols"
                }
            }
        ]
        for i, data in enumerate(test_cases):
            print(f"\nTest case {i + 1}:")
            print("Input:", data)
            xml = dicttoxml.dicttoxml(data, custom_root='all')
            print("Output XML:")
            print(xml.decode('utf-8'))

    def test_escapes_angle_brackets(self):
        json_data = json.dumps({"root": {"@attrs": {"HelpText": "version <here>"}}})
        result = json2xml.Json2xml(json_data).to_xml()
        assert '"HelpText": "version &lt;here&gt;"' in result

    def test_escapes_quotes(self):
        json_data = json.dumps({"root": {"@attrs": {"Text": "\"quoted\""}}})
        result = json2xml.Json2xml(json_data).to_xml()
        assert '"Text": "\\"quoted\\""' in result

    def test_escapes_ampersands(self):
        json_data = json.dumps({"root": {"@attrs": {"Text": "this & that"}}})
        result = json2xml.Json2xml(json_data).to_xml()
        assert '"Text": "this &amp; that"' in result

    def test_escapes_mixed_special_chars(self):
        json_data = json.dumps({"root": {"@attrs": {"Text": "<tag> & \"quote\""}}})
        result = json2xml.Json2xml(json_data).to_xml()
        assert '"Text": "&lt;tag&gt; &amp; \\"quote\\""' in result


