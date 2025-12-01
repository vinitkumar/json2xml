"""Tests for missing coverage lines in dicttoxml.py"""

from __future__ import annotations

import numbers
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from json2xml.dicttoxml import (
    convert_to_xpath31,
    dicttoxml,
    get_unique_id,
    get_xml_type,
    get_xpath31_tag_name,
    make_id,
)

if TYPE_CHECKING:
    pass


class TestGetUniqueIdDuplicateGeneration:
    """Test line 52: duplicate ID generation in get_unique_id loop"""

    def test_get_unique_id_generates_id_when_duplicates_occur(self) -> None:
        """Test that get_unique_id handles the while loop by regenerating IDs on duplicates.

        Line 52 (this_id = make_id(element)) is executed when a duplicate is found.
        Since make_id uses SystemRandom, we can't guarantee duplicates, but we can
        ensure the function returns a valid ID in the correct format.
        """
        result = get_unique_id("test_element")

        # Verify it returns a string in the expected format
        assert isinstance(result, str)
        assert result.startswith("test_element_")
        assert len(result) > len("test_element_")

        # Verify the numeric part is valid
        numeric_part = result.replace("test_element_", "")
        assert numeric_part.isdigit()
        assert 100000 <= int(numeric_part) <= 999999

    def test_get_unique_id_duplicate_id_regeneration(self) -> None:
        """Test line 52: trigger duplicate ID regeneration.

        Line 52 (this_id = make_id(element)) only executes if this_id is in the ids list.
        We can't easily trigger this with the current implementation since ids starts empty,
        but we test the function's robustness when make_id returns duplicates.
        """
        # Call get_unique_id multiple times - while theoretically one could duplicate
        # due to SystemRandom, the function handles this correctly
        ids_generated = [get_unique_id("test") for _ in range(10)]

        # All generated IDs should be properly formatted
        for id_val in ids_generated:
            assert isinstance(id_val, str)
            assert id_val.startswith("test_")
            numeric_part = id_val.split("_")[-1]
            assert numeric_part.isdigit()
            assert 100000 <= int(numeric_part) <= 999999


class TestGetXmlTypeWithNumbers:
    """Test line 90: get_xml_type handling of numbers.Number instances"""

    def test_get_xml_type_with_decimal(self) -> None:
        """Test get_xml_type with Decimal (numbers.Number subclass).

        Line 90 (return "number") is executed for instances of numbers.Number
        that don't match other type checks (str, int, float, bool).
        """
        from decimal import Decimal

        result = get_xml_type(Decimal("123.45"))
        assert result == "number"

    def test_get_xml_type_with_fraction(self) -> None:
        """Test get_xml_type with Fraction (numbers.Number subclass)."""
        from fractions import Fraction

        result = get_xml_type(Fraction(3, 4))
        assert result == "number"

    def test_get_xml_type_with_complex(self) -> None:
        """Test get_xml_type with complex numbers (numbers.Number subclass)."""
        result = get_xml_type(complex(1, 2))
        assert result == "number"


class TestGetXpath31TagNameWithBytesAndBytearray:
    """Test lines 219, 222: get_xpath31_tag_name handling of bytes/bytearray and fallback"""

    def test_get_xpath31_tag_name_with_bytes(self) -> None:
        """Test get_xpath31_tag_name with bytes.

        Line 219 (return "string") is executed for bytes instances.
        """
        result = get_xpath31_tag_name(b"hello")
        assert result == "string"

    def test_get_xpath31_tag_name_with_bytearray(self) -> None:
        """Test get_xpath31_tag_name with bytearray.

        Line 219 (return "string") is executed for bytearray instances.
        """
        result = get_xpath31_tag_name(bytearray(b"hello"))
        assert result == "string"

    def test_get_xpath31_tag_name_with_unsupported_type(self) -> None:
        """Test get_xpath31_tag_name with unsupported type falls back to string.

        Line 222 (return "string") is the fallback for types that don't match
        any of the specific type checks.
        """
        # Create an object that isn't any of the handled types
        class CustomObject:
            pass

        result = get_xpath31_tag_name(CustomObject())
        assert result == "string"

    def test_get_xpath31_tag_name_with_empty_bytes(self) -> None:
        """Test get_xpath31_tag_name with empty bytes."""
        result = get_xpath31_tag_name(b"")
        assert result == "string"

    def test_get_xpath31_tag_name_with_empty_bytearray(self) -> None:
        """Test get_xpath31_tag_name with empty bytearray."""
        result = get_xpath31_tag_name(bytearray())
        assert result == "string"


class TestConvertToXpath31Fallback:
    """Test line 261: convert_to_xpath31 fallback case"""

    def test_convert_to_xpath31_with_unsupported_type(self) -> None:
        """Test convert_to_xpath31 with unsupported type falls back to string conversion.

        Line 261 is the fallback case that converts unsupported types to strings.
        """
        # Create an object that will trigger the fallback
        class CustomObject:
            def __str__(self) -> str:
                return "custom_object_string"

        result = convert_to_xpath31(CustomObject())

        # Should wrap it in a string tag
        assert "<string>" in result
        assert "custom_object_string" in result
        assert "</string>" in result

    def test_convert_to_xpath31_with_custom_object_and_parent_key(self) -> None:
        """Test convert_to_xpath31 fallback with parent_key attribute."""
        class CustomObject:
            def __str__(self) -> str:
                return "test_value"

        result = convert_to_xpath31(CustomObject(), parent_key="my_key")

        # Should include key attribute
        assert 'key="my_key"' in result
        assert "<string" in result

    def test_convert_to_xpath31_fallback_line_261(self) -> None:
        """Test line 261: fallback case when get_xpath31_tag_name returns unexpected value.

        This test mocks get_xpath31_tag_name to return an unexpected value,
        forcing the fallback on line 261 to execute.
        """
        test_obj = {"data": "test"}

        with patch('json2xml.dicttoxml.get_xpath31_tag_name') as mock_tag:
            # Return an unexpected tag name that won't match any if statements
            mock_tag.return_value = "unexpected_type"

            result = convert_to_xpath31(test_obj)

            # Should fall through to line 261 and return string representation
            assert "<string>" in result
            assert result.startswith("<string>")
            assert result.endswith("</string>")

    def test_convert_to_xpath31_fallback_with_key_attr(self) -> None:
        """Test line 261 fallback with key attribute."""
        test_obj = object()

        with patch('json2xml.dicttoxml.get_xpath31_tag_name') as mock_tag:
            mock_tag.return_value = "unknown"

            result = convert_to_xpath31(test_obj, parent_key="test_key")

            # Should include key attribute in fallback output
            assert 'key="test_key"' in result
            assert "<string" in result


class TestConvertToXpath31FullIntegration:
    """Integration tests for xpath31 format conversion"""

    def test_xpath31_with_bytes_value(self) -> None:
        """Test xpath31 format conversion with bytes in dict."""
        obj = {"data": b"binary_data"}
        result = dicttoxml(obj, xpath_format=True)

        # Should not raise and should produce valid XML
        assert b"<?xml" in result
        assert b"map" in result
        assert b"string" in result

    def test_xpath31_with_decimal_value(self) -> None:
        """Test xpath31 format conversion with Decimal number."""
        from decimal import Decimal

        obj = {"amount": Decimal("99.99")}
        result = dicttoxml(obj, xpath_format=True)

        # Should convert Decimal to number tag via fallback handling
        assert b"<?xml" in result
        assert b"map" in result

    def test_xpath31_with_nested_custom_object(self) -> None:
        """Test xpath31 format with nested custom objects."""
        class Point:
            def __str__(self) -> str:
                return "0,0"

        obj = {"location": Point()}
        result = dicttoxml(obj, xpath_format=True)

        assert b"<?xml" in result
        assert b"map" in result
        assert b"string" in result


class TestXmlTypeEdgeCases:
    """Additional edge cases for get_xml_type covering line 90"""

    def test_get_xml_type_with_custom_number_class(self) -> None:
        """Test get_xml_type with custom class inheriting from numbers.Number."""
        class CustomNumber(numbers.Number):
            def __init__(self, value: float) -> None:
                self.value = value

            def __str__(self) -> str:
                return str(self.value)

        result = get_xml_type(CustomNumber(42))
        assert result == "number"

    def test_get_xml_type_prioritizes_bool_over_number(self) -> None:
        """Verify bool is checked before numbers.Number (important for correct type)."""
        # This tests the ordering logic that prevents True/False from being typed as int
        result_true = get_xml_type(True)
        result_false = get_xml_type(False)

        assert result_true == "bool"
        assert result_false == "bool"
        # If the order was wrong, they'd be "int"
        assert result_true != "int"
        assert result_false != "int"


class TestXpath31TypesComprehensive:
    """Comprehensive tests ensuring all type paths in get_xpath31_tag_name are covered"""

    def test_xpath31_tag_name_all_types(self) -> None:
        """Test all type branches in get_xpath31_tag_name."""
        # None
        assert get_xpath31_tag_name(None) == "null"

        # bool (must come before int check)
        assert get_xpath31_tag_name(True) == "boolean"
        assert get_xpath31_tag_name(False) == "boolean"

        # dict
        assert get_xpath31_tag_name({}) == "map"
        assert get_xpath31_tag_name({"key": "value"}) == "map"

        # numbers
        assert get_xpath31_tag_name(42) == "number"
        assert get_xpath31_tag_name(3.14) == "number"

        # str
        assert get_xpath31_tag_name("hello") == "string"
        assert get_xpath31_tag_name("") == "string"

        # bytes and bytearray
        assert get_xpath31_tag_name(b"hello") == "string"
        assert get_xpath31_tag_name(bytearray(b"hello")) == "string"

        # Sequence (list, tuple)
        assert get_xpath31_tag_name([]) == "array"
        assert get_xpath31_tag_name([1, 2, 3]) == "array"
        assert get_xpath31_tag_name(()) == "array"
        assert get_xpath31_tag_name((1, 2, 3)) == "array"

        # Fallback
        class CustomType:
            pass
        assert get_xpath31_tag_name(CustomType()) == "string"


class TestGetUniqueIdDuplicateIteration:
    """Test the while loop iteration in get_unique_id (line 47-52)"""

    def test_get_unique_id_returns_valid_format(self) -> None:
        """Test that get_unique_id returns properly formatted ID."""
        from json2xml.dicttoxml import get_unique_id

        # Call multiple times to ensure consistency
        ids = [get_unique_id("element") for _ in range(5)]

        # All should be unique
        assert len(set(ids)) == 5

        # All should follow the format
        for id_val in ids:
            assert isinstance(id_val, str)
            assert id_val.startswith("element_")
            numeric_part = id_val.split("_")[-1]
            assert numeric_part.isdigit()


class TestConvertToXpath31AllPaths:
    """Comprehensive tests for all conversion paths in convert_to_xpath31"""

    def test_convert_to_xpath31_null(self) -> None:
        """Test null conversion."""
        result = convert_to_xpath31(None)
        assert result == "<null/>"

        # With key
        result = convert_to_xpath31(None, parent_key="empty")
        assert 'key="empty"' in result
        assert "<null" in result

    def test_convert_to_xpath31_boolean(self) -> None:
        """Test boolean conversion."""
        result_true = convert_to_xpath31(True)
        assert "<boolean>true</boolean>" == result_true

        result_false = convert_to_xpath31(False)
        assert "<boolean>false</boolean>" == result_false

        # With key
        result = convert_to_xpath31(True, parent_key="is_active")
        assert 'key="is_active"' in result
        assert "<boolean" in result
        assert ">true</boolean>" in result

    def test_convert_to_xpath31_number(self) -> None:
        """Test number conversion."""
        result = convert_to_xpath31(42)
        assert "<number>42</number>" == result

        result = convert_to_xpath31(3.14)
        assert "<number>3.14</number>" == result

    def test_convert_to_xpath31_string(self) -> None:
        """Test string conversion."""
        result = convert_to_xpath31("hello")
        assert "<string>hello</string>" == result

        # With special characters that need escaping
        result = convert_to_xpath31("hello & <world>")
        assert "<string>" in result
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_convert_to_xpath31_map(self) -> None:
        """Test map (dict) conversion."""
        result = convert_to_xpath31({"name": "John", "age": 30})
        assert "<map>" in result
        assert "</map>" in result
        assert "<string" in result
        assert "<number" in result

    def test_convert_to_xpath31_array(self) -> None:
        """Test array (list) conversion."""
        result = convert_to_xpath31([1, "two", 3.0])
        assert "<array>" in result
        assert "</array>" in result
        assert "<number>" in result
        assert "<string>" in result

    def test_convert_to_xpath31_bytes_fallback(self) -> None:
        """Test bytes conversion (falls to string conversion line 261)."""
        result = convert_to_xpath31(b"binary")
        # bytes get converted via fallback to string representation
        assert "<string>" in result

    def test_convert_to_xpath31_custom_object_fallback(self) -> None:
        """Test custom object conversion (line 261 fallback)."""
        class Point:
            def __str__(self) -> str:
                return "(1,2)"

        result = convert_to_xpath31(Point())
        assert "<string>" in result
        assert "(1,2)" in result
