"""
Tests for the Rust (PyO3) dicttoxml implementation.

These tests verify that the Rust implementation produces correct output
and matches the Python implementation for supported features.
"""
from __future__ import annotations

import pytest

# Check if Rust extension is available
try:
    from json2xml_rs import dicttoxml as rust_dicttoxml
    from json2xml_rs import escape_xml_py, wrap_cdata_py
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

from json2xml import dicttoxml as py_dicttoxml
from json2xml.dicttoxml_fast import dicttoxml as fast_dicttoxml, is_rust_available, get_backend


# Skip all tests if Rust is not available
pytestmark = pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extension not installed")


class TestRustEscapeXml:
    """Test the Rust escape_xml function."""

    def test_escape_ampersand(self):
        assert escape_xml_py("foo & bar") == "foo &amp; bar"

    def test_escape_quotes(self):
        assert escape_xml_py('say "hello"') == "say &quot;hello&quot;"

    def test_escape_apostrophe(self):
        assert escape_xml_py("it's") == "it&apos;s"

    def test_escape_less_than(self):
        assert escape_xml_py("a < b") == "a &lt; b"

    def test_escape_greater_than(self):
        assert escape_xml_py("a > b") == "a &gt; b"

    def test_escape_multiple(self):
        assert escape_xml_py("<foo & 'bar'>") == "&lt;foo &amp; &apos;bar&apos;&gt;"

    def test_escape_empty(self):
        assert escape_xml_py("") == ""

    def test_escape_no_special_chars(self):
        assert escape_xml_py("hello world") == "hello world"

    def test_escape_unicode(self):
        assert escape_xml_py("héllo wörld 日本語") == "héllo wörld 日本語"


class TestRustWrapCdata:
    """Test the Rust wrap_cdata function."""

    def test_wrap_simple(self):
        assert wrap_cdata_py("hello") == "<![CDATA[hello]]>"

    def test_wrap_with_special_chars(self):
        # CDATA doesn't need escaping for most chars
        assert wrap_cdata_py("<foo & bar>") == "<![CDATA[<foo & bar>]]>"

    def test_wrap_with_cdata_end(self):
        # ]]> must be escaped within CDATA
        assert wrap_cdata_py("test]]>end") == "<![CDATA[test]]]]><![CDATA[>end]]>"

    def test_wrap_empty(self):
        assert wrap_cdata_py("") == "<![CDATA[]]>"


class TestRustDicttoxml:
    """Test the main Rust dicttoxml function."""

    def test_simple_dict(self):
        data = {"name": "John", "age": 30}
        result = rust_dicttoxml(data)
        assert b'<?xml version="1.0" encoding="UTF-8" ?>' in result
        assert b"<root>" in result
        assert b"</root>" in result
        assert b"<name" in result
        assert b">John</name>" in result
        assert b"<age" in result
        assert b">30</age>" in result

    def test_string_value(self):
        data = {"message": "Hello World"}
        result = rust_dicttoxml(data)
        assert b">Hello World</message>" in result
        assert b'type="str"' in result

    def test_integer_value(self):
        data = {"count": 42}
        result = rust_dicttoxml(data)
        assert b">42</count>" in result
        assert b'type="int"' in result

    def test_float_value(self):
        data = {"price": 19.99}
        result = rust_dicttoxml(data)
        assert b">19.99</price>" in result
        assert b'type="float"' in result

    def test_boolean_true(self):
        data = {"active": True}
        result = rust_dicttoxml(data)
        assert b">true</active>" in result
        assert b'type="bool"' in result

    def test_boolean_false(self):
        data = {"active": False}
        result = rust_dicttoxml(data)
        assert b">false</active>" in result
        assert b'type="bool"' in result

    def test_none_value(self):
        data = {"empty": None}
        result = rust_dicttoxml(data)
        assert b"<empty" in result
        assert b'type="null"' in result

    def test_nested_dict(self):
        data = {"person": {"name": "John", "age": 30}}
        result = rust_dicttoxml(data)
        assert b"<person" in result
        assert b"</person>" in result
        assert b"<name" in result
        assert b"<age" in result

    def test_simple_list(self):
        data = {"numbers": [1, 2, 3]}
        result = rust_dicttoxml(data)
        assert b"<numbers" in result
        assert b"<item" in result
        assert b">1</item>" in result
        assert b">2</item>" in result
        assert b">3</item>" in result

    def test_list_of_dicts(self):
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        result = rust_dicttoxml(data)
        assert b"<users" in result
        assert b">Alice</name>" in result
        assert b">Bob</name>" in result

    def test_deeply_nested(self):
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }
        result = rust_dicttoxml(data)
        assert b"<level1" in result
        assert b"<level2" in result
        assert b"<level3" in result
        assert b">deep</value>" in result

    def test_mixed_types_in_dict(self):
        data = {
            "string": "hello",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2],
            "dict": {"nested": "value"}
        }
        result = rust_dicttoxml(data)
        assert b">hello</string>" in result
        assert b">42</integer>" in result
        assert b">3.14</float>" in result
        assert b">true</boolean>" in result
        assert b'type="null"' in result
        assert b"<nested" in result

    def test_special_characters_escaped(self):
        data = {"message": "Hello <World> & 'Friends'"}
        result = rust_dicttoxml(data)
        assert b"&lt;World&gt;" in result
        assert b"&amp;" in result
        assert b"&apos;Friends&apos;" in result

    def test_empty_dict(self):
        data = {}
        result = rust_dicttoxml(data)
        assert b"<root></root>" in result

    def test_empty_list(self):
        data = {"items": []}
        result = rust_dicttoxml(data)
        assert b"<items" in result


class TestRustDicttoxmlOptions:
    """Test Rust dicttoxml with various options."""

    def test_no_root(self):
        data = {"name": "John"}
        result = rust_dicttoxml(data, root=False)
        assert b'<?xml version' not in result
        assert b"<root>" not in result
        assert b"<name" in result

    def test_custom_root(self):
        data = {"name": "John"}
        result = rust_dicttoxml(data, custom_root="person")
        assert b"<person>" in result
        assert b"</person>" in result

    def test_no_attr_type(self):
        data = {"name": "John", "age": 30}
        result = rust_dicttoxml(data, attr_type=False)
        assert b'type="str"' not in result
        assert b'type="int"' not in result

    def test_with_cdata(self):
        data = {"message": "Hello <World>"}
        result = rust_dicttoxml(data, cdata=True)
        assert b"<![CDATA[Hello <World>]]>" in result

    def test_item_wrap_false(self):
        data = {"colors": ["red", "green", "blue"]}
        result = rust_dicttoxml(data, item_wrap=False)
        # Without item_wrap, items use parent tag name
        assert b"<colors" in result
        assert b">red</colors>" in result
        assert b">green</colors>" in result
        assert b">blue</colors>" in result

    def test_list_headers(self):
        data = {"colors": ["red", "green"]}
        result = rust_dicttoxml(data, list_headers=True)
        assert b"<colors" in result


class TestRustVsPythonCompatibility:
    """Test that Rust output matches Python for supported features."""

    def compare_outputs(self, data, **kwargs):
        """Compare Rust and Python outputs for the same input."""
        rust_result = rust_dicttoxml(data, **kwargs)
        python_result = py_dicttoxml.dicttoxml(data, **kwargs)
        return rust_result, python_result

    def test_simple_dict_matches(self):
        data = {"name": "John", "age": 30}
        rust, python = self.compare_outputs(data)
        assert rust == python

    def test_nested_dict_matches(self):
        data = {"person": {"name": "John", "city": "NYC"}}
        rust, python = self.compare_outputs(data)
        assert rust == python

    def test_list_matches(self):
        data = {"numbers": [1, 2, 3]}
        rust, python = self.compare_outputs(data)
        assert rust == python

    def test_bool_matches(self):
        data = {"active": True, "deleted": False}
        rust, python = self.compare_outputs(data)
        assert rust == python

    def test_none_matches(self):
        data = {"empty": None}
        rust, python = self.compare_outputs(data)
        assert rust == python

    def test_special_chars_matches(self):
        data = {"text": "Hello <World> & 'Friends'"}
        rust, python = self.compare_outputs(data)
        assert rust == python

    def test_no_root_matches(self):
        data = {"key": "value"}
        rust, python = self.compare_outputs(data, root=False)
        assert rust == python

    def test_custom_root_matches(self):
        data = {"key": "value"}
        rust, python = self.compare_outputs(data, custom_root="custom")
        assert rust == python

    def test_no_attr_type_matches(self):
        data = {"name": "John", "age": 30}
        rust, python = self.compare_outputs(data, attr_type=False)
        assert rust == python

    def test_cdata_matches(self):
        data = {"message": "Hello World"}
        rust, python = self.compare_outputs(data, cdata=True)
        assert rust == python

    def test_complex_nested_matches(self):
        data = {
            "users": [
                {"name": "Alice", "scores": [90, 85, 88]},
                {"name": "Bob", "scores": [75, 80, 82]}
            ],
            "metadata": {
                "count": 2,
                "active": True
            }
        }
        rust, python = self.compare_outputs(data)
        assert rust == python


class TestFastDicttoxmlWrapper:
    """Test the dicttoxml_fast wrapper module."""

    def test_rust_available(self):
        assert is_rust_available() is True

    def test_backend_is_rust(self):
        assert get_backend() == "rust"

    def test_basic_conversion(self):
        data = {"name": "John"}
        result = fast_dicttoxml(data)
        assert b"<name" in result
        assert b">John</name>" in result

    def test_falls_back_for_xpath_format(self):
        """xpath_format requires Python fallback."""
        data = {"name": "John"}
        result = fast_dicttoxml(data, xpath_format=True)
        # Should still work (uses Python)
        assert b"<string" in result  # XPath format uses <string> tags

    def test_falls_back_for_namespaces(self):
        """xml_namespaces requires Python fallback."""
        data = {"name": "John"}
        result = fast_dicttoxml(data, xml_namespaces={"ns": "http://example.com"})
        assert b'xmlns:ns="http://example.com"' in result

    def test_falls_back_for_item_func(self):
        """Custom item_func requires Python fallback."""
        data = {"items": [1, 2, 3]}
        result = fast_dicttoxml(data, item_func=lambda p: "element")
        assert b"<element" in result

    def test_falls_back_for_special_keys(self):
        """@attrs and other special keys require Python fallback."""
        data = {"key": {"@attrs": {"id": "123"}, "@val": "value"}}
        result = fast_dicttoxml(data)
        assert b'id="123"' in result


class TestRustEdgeCases:
    """Test edge cases and potential problem areas."""

    def test_unicode_keys(self):
        data = {"名前": "太郎", "ciudad": "México"}
        result = rust_dicttoxml(data)
        result_str = result.decode("utf-8")
        assert "太郎" in result_str
        assert "México" in result_str

    def test_numeric_string_key(self):
        # Keys that are numbers should be prefixed with 'n'
        data = {"123": "value"}
        result = rust_dicttoxml(data)
        # Either the key is modified or wrapped in a name attribute
        assert b"<n123" in result or b'name="123"' in result

    def test_key_with_spaces(self):
        data = {"my key": "value"}
        result = rust_dicttoxml(data)
        # Spaces should be converted to underscores
        assert b"<my_key" in result or b'name="my key"' in result

    def test_large_integer(self):
        data = {"big": 9999999999999999}
        result = rust_dicttoxml(data)
        assert b"9999999999999999" in result

    def test_negative_number(self):
        data = {"negative": -42}
        result = rust_dicttoxml(data)
        assert b">-42</negative>" in result

    def test_float_precision(self):
        data = {"pi": 3.141592653589793}
        result = rust_dicttoxml(data)
        assert b"3.14159" in result  # At least 6 digits

    def test_empty_string(self):
        data = {"empty": ""}
        result = rust_dicttoxml(data)
        assert b"<empty" in result
        assert b"></empty>" in result

    def test_list_of_lists(self):
        data = {"matrix": [[1, 2], [3, 4]]}
        result = rust_dicttoxml(data)
        assert b"<matrix" in result
        assert b">1<" in result
        assert b">4<" in result

    def test_list_with_none(self):
        data = {"items": [1, None, 3]}
        result = rust_dicttoxml(data)
        assert b">1<" in result
        assert b">3<" in result
        assert b'type="null"' in result

    def test_mixed_list(self):
        data = {"mixed": ["string", 42, True, None]}
        result = rust_dicttoxml(data)
        assert b">string<" in result
        assert b">42<" in result
        assert b">true<" in result


class TestRustPerformanceBasics:
    """Basic sanity checks for performance-related behavior."""

    def test_large_dict(self):
        """Ensure large dicts don't crash."""
        data = {f"key_{i}": f"value_{i}" for i in range(1000)}
        result = rust_dicttoxml(data)
        assert b"<root>" in result
        assert b"key_999" in result

    def test_large_list(self):
        """Ensure large lists don't crash."""
        data = {"items": list(range(1000))}
        result = rust_dicttoxml(data)
        assert b"<items" in result
        assert b">999<" in result

    def test_deeply_nested_structure(self):
        """Ensure deep nesting doesn't crash."""
        data = {"level": None}
        current = data
        for i in range(50):
            current["level"] = {"value": i}
            current = current["level"]
        result = rust_dicttoxml(data)
        assert b"<level" in result
