"""Tests for parallel processing functionality."""
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

import pytest

from json2xml import dicttoxml
from json2xml.json2xml import Json2xml
from json2xml.parallel import (
    convert_dict_parallel,
    convert_list_parallel,
    get_optimal_workers,
    is_free_threaded,
    key_is_valid_xml_cached,
    make_valid_xml_name_cached,
)

if TYPE_CHECKING:
    pass


class TestParallelProcessing:
    """Test parallel processing features."""

    def test_is_free_threaded(self) -> None:
        """Test free-threaded detection."""
        result = is_free_threaded()
        assert isinstance(result, bool)

    def test_is_free_threaded_exception(self) -> None:
        """Test free-threaded detection when _is_gil_enabled raises exception."""
        import sys
        original = getattr(sys, '_is_gil_enabled', None)
        def mock_is_gil_enabled():
            raise Exception("test")
        sys._is_gil_enabled = mock_is_gil_enabled  # type: ignore
        try:
            result = is_free_threaded()
            assert result is False  # defaults to False on exception
        finally:
            if original is not None:
                sys._is_gil_enabled = original  # type: ignore
            else:
                delattr(sys, '_is_gil_enabled')

    def test_get_optimal_workers_explicit(self) -> None:
        """Test explicit worker count."""
        assert get_optimal_workers(4) == 4
        assert get_optimal_workers(1) == 1
        assert get_optimal_workers(16) == 16

    def test_get_optimal_workers_auto(self) -> None:
        """Test auto-detect worker count."""
        workers = get_optimal_workers(None)
        assert workers >= 1
        assert workers <= 16

    def test_key_is_valid_xml_cached(self) -> None:
        """Test thread-safe XML validation caching."""
        assert key_is_valid_xml_cached("valid_key") is True
        assert key_is_valid_xml_cached("123invalid") is False
        assert key_is_valid_xml_cached("valid_key") is True

    def test_parallel_dict_small(self) -> None:
        """Test parallel dict conversion with small data (should fallback to serial)."""
        data = {"key1": "value1", "key2": "value2"}
        result_parallel = convert_dict_parallel(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False, workers=2
        )
        result_serial = dicttoxml.convert_dict(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False
        )
        assert result_parallel == result_serial

    def test_parallel_dict_large(self) -> None:
        """Test parallel dict conversion with large data."""
        data = {f"key{i}": f"value{i}" for i in range(20)}
        result_parallel = convert_dict_parallel(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False, workers=4
        )
        result_serial = dicttoxml.convert_dict(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False
        )
        assert result_parallel == result_serial

    def test_parallel_dict_invalid_input(self) -> None:
        """Test parallel dict conversion with invalid input types."""
        # Passing a list instead of a dict
        invalid_data = ["not", "a", "dict"]
        with pytest.raises(TypeError):
            convert_dict_parallel(
                cast(dict[str, Any], invalid_data), [], "root", True, dicttoxml.default_item_func, False, True, False, workers=2
            )

        # Passing None
        with pytest.raises(TypeError):
            convert_dict_parallel(
                cast(dict[str, Any], None), [], "root", True, dicttoxml.default_item_func, False, True, False, workers=2
            )

    def test_parallel_list_invalid_input(self) -> None:
        """Test parallel list conversion with invalid input types."""
        # Passing a dict instead of a list
        invalid_data = {"not": "a list"}
        with pytest.raises(TypeError):
            convert_list_parallel(
                cast(Sequence[Any], invalid_data), [], "root", True, dicttoxml.default_item_func, False, True, False, workers=2, chunk_size=100
            )

        # Passing None
        with pytest.raises(TypeError):
            convert_list_parallel(
                cast(Sequence[Any], None), [], "root", True, dicttoxml.default_item_func, False, True, False, workers=2, chunk_size=100
            )

    def test_parallel_list_small(self) -> None:
        """Test parallel list conversion with small data (should fallback to serial)."""
        data = ["item1", "item2", "item3"]
        result_parallel = convert_list_parallel(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False, workers=2, chunk_size=100
        )
        result_serial = dicttoxml.convert_list(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False
        )
        assert result_parallel == result_serial

    def test_parallel_list_large(self) -> None:
        """Test parallel list conversion with large data."""
        data = [f"item{i}" for i in range(200)]
        result_parallel = convert_list_parallel(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False, workers=4, chunk_size=50
        )
        result_serial = dicttoxml.convert_list(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False
        )
        assert result_parallel == result_serial

    def test_parallel_dict_with_nested_structures(self) -> None:
        """Test parallel dict conversion with nested structures."""
        data = {
            f"key{i}": {
                "nested": f"value{i}",
                "list": [1, 2, 3],
                "bool": True
            } for i in range(15)
        }
        result_parallel = convert_dict_parallel(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False, workers=4
        )
        result_serial = dicttoxml.convert_dict(
            data, [], "root", True, dicttoxml.default_item_func, False, True, False
        )
        assert result_parallel == result_serial

    def test_json2xml_parallel_dict(self) -> None:
        """Test Json2xml with parallel processing enabled for dict."""
        data = {f"key{i}": f"value{i}" for i in range(20)}

        converter_parallel = Json2xml(data, parallel=True, workers=4)
        result_parallel = converter_parallel.to_xml()

        converter_serial = Json2xml(data, parallel=False)
        result_serial = converter_serial.to_xml()

        assert result_parallel == result_serial

    def test_json2xml_parallel_list(self) -> None:
        """Test Json2xml with parallel processing enabled for list."""
        data = {"items": [f"item{i}" for i in range(150)]}

        converter_parallel = Json2xml(data, parallel=True, workers=4, chunk_size=50)
        result_parallel = converter_parallel.to_xml()

        converter_serial = Json2xml(data, parallel=False)
        result_serial = converter_serial.to_xml()

        assert result_parallel == result_serial

    def test_json2xml_parallel_complex(self) -> None:
        """Test Json2xml with parallel processing on complex nested data."""
        data = {
            "users": [
                {
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "active": i % 2 == 0,
                    "roles": ["admin", "user"] if i % 3 == 0 else ["user"],
                    "metadata": {
                        "created": "2024-01-01",
                        "updated": "2024-01-02"
                    }
                }
                for i in range(100)
            ],
            "total": 100,
            "page": 1
        }

        converter_parallel = Json2xml(data, parallel=True, workers=4, chunk_size=25)
        result_parallel = converter_parallel.to_xml()

        converter_serial = Json2xml(data, parallel=False)
        result_serial = converter_serial.to_xml()

        assert result_parallel == result_serial
        assert result_parallel is not None
        result_bytes: bytes = result_parallel.encode() if isinstance(result_parallel, str) else result_parallel
        assert b"<users" in result_bytes
        assert b"<total" in result_bytes

    def test_dicttoxml_parallel_dict(self) -> None:
        """Test dicttoxml with parallel processing enabled."""
        data = {f"item{i}": i for i in range(30)}

        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=4)
        result_serial = dicttoxml.dicttoxml(data, parallel=False)

        assert result_parallel == result_serial

    def test_dicttoxml_parallel_list(self) -> None:
        """Test dicttoxml with parallel list processing."""
        data = [f"item{i}" for i in range(200)]

        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=4, chunk_size=50)
        result_serial = dicttoxml.dicttoxml(data, parallel=False)

        assert result_parallel == result_serial

    def test_parallel_with_attr_type_false(self) -> None:
        """Test parallel processing with attr_type=False."""
        data = {f"key{i}": f"value{i}" for i in range(20)}

        result_parallel = dicttoxml.dicttoxml(data, attr_type=False, parallel=True, workers=4)
        result_serial = dicttoxml.dicttoxml(data, attr_type=False, parallel=False)

        assert result_parallel == result_serial

    def test_parallel_with_item_wrap_false(self) -> None:
        """Test parallel processing with item_wrap=False."""
        data = {"items": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}

        result_parallel = dicttoxml.dicttoxml(data, item_wrap=False, parallel=True, workers=2)
        result_serial = dicttoxml.dicttoxml(data, item_wrap=False, parallel=False)

        assert result_parallel == result_serial

    def test_parallel_with_special_characters(self) -> None:
        """Test parallel processing with special XML characters."""
        data = {
            f"key{i}": f"value with <special> & \"characters\" {i}"
            for i in range(15)
        }

        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=4)
        result_serial = dicttoxml.dicttoxml(data, parallel=False)

        assert result_parallel == result_serial
        assert b"&lt;special&gt;" in result_parallel
        assert b"&amp;" in result_parallel

    def test_parallel_with_attributes(self) -> None:
        """Test parallel processing with XML attributes."""
        # Simulate attribute handling using dicttoxml's attr_type feature
        data = {
            "person": {
                "@id": "123",
                "name": "Alice"
            }
        }
        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=2, attr_type=True)
        result_serial = dicttoxml.dicttoxml(data, parallel=False, attr_type=True)
        assert result_parallel == result_serial
        assert b'id="123"' in result_parallel

    def test_parallel_with_namespaces(self) -> None:
        """Test parallel processing with XML namespaces."""
        # Simulate namespace handling by including a namespace in the tag
        data = {
            "ns:person": {
                "name": "Bob"
            }
        }
        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=2)
        result_serial = dicttoxml.dicttoxml(data, parallel=False)
        assert result_parallel == result_serial
        assert b"<ns:person" in result_parallel

    def test_parallel_with_cdata(self) -> None:
        """Test parallel processing with CDATA sections."""
        # Simulate CDATA by including a value that should be wrapped in CDATA
        data = {
            "note": "<![CDATA[Some <cdata> content & more]]>"
        }
        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=2, cdata=True)
        result_serial = dicttoxml.dicttoxml(data, parallel=False, cdata=True)
        assert result_parallel == result_serial
        assert b"<![CDATA[Some <cdata> content & more]]>" in result_parallel

    def test_parallel_empty_data(self) -> None:
        """Test parallel processing with empty data."""
        data = {"key": "value"}
        converter = Json2xml(data, parallel=True, workers=4)
        result = converter.to_xml()
        assert result is not None

    def test_parallel_with_none_workers(self) -> None:
        """Test parallel processing with None workers (auto-detect)."""
        data = {f"key{i}": f"value{i}" for i in range(20)}
        converter = Json2xml(data, parallel=True, workers=None)
        result = converter.to_xml()
        assert result is not None

    def test_parallel_dict_order_preserved(self) -> None:
        """Test that parallel processing preserves dict order."""
        data = {f"key{i:03d}": f"value{i}" for i in range(30)}

        result_parallel = convert_dict_parallel(
            data, [], "root", False, dicttoxml.default_item_func, False, True, False, workers=4
        )
        result_serial = dicttoxml.convert_dict(
            data, [], "root", False, dicttoxml.default_item_func, False, True, False
        )

        assert result_parallel == result_serial

    def test_parallel_no_root(self) -> None:
        """Test parallel processing without root element."""
        data = {f"item{i}": i for i in range(20)}
        result = dicttoxml.dicttoxml(data, root=False, parallel=True, workers=4)
        assert b"<?xml version" not in result

    def test_parallel_list_no_root(self) -> None:
        """Test parallel processing of list without root element."""
        data = [{"id": i, "name": f"item{i}"} for i in range(20)]
        result = dicttoxml.dicttoxml(data, root=False, parallel=True, workers=4)
        assert b"<?xml version" not in result

    def test_parallel_primitive_no_root(self) -> None:
        """Test parallel processing of primitive value without root element."""
        data = 42
        result = dicttoxml.dicttoxml(data, root=False, parallel=True, workers=4)
        assert b"<?xml version" not in result
        assert b"42" in result

    def test_make_valid_xml_name_cached_with_digit_string(self) -> None:
        """Test make_valid_xml_name_cached with digit string."""
        key, attr = make_valid_xml_name_cached("456", {})
        assert key == "n456"
        assert attr == {}

    def test_make_valid_xml_name_cached_with_space(self) -> None:
        """Test make_valid_xml_name_cached with space in key."""
        key, attr = make_valid_xml_name_cached("my key", {})
        assert key == "my_key"
        assert attr == {}

    def test_make_valid_xml_name_cached_with_colon(self) -> None:
        """Test make_valid_xml_name_cached with colon in key."""
        key, attr = make_valid_xml_name_cached("ns:element", {})
        assert key == "ns:element"
        assert attr == {}

    def test_make_valid_xml_name_cached_with_invalid_chars(self) -> None:
        """Test make_valid_xml_name_cached with invalid XML characters."""
        key, attr = make_valid_xml_name_cached("in<valid>key", {})
        assert key == "key"
        assert attr["name"] == "in&lt;valid&gt;key"

    def test_parallel_with_sequence_value(self) -> None:
        """Test parallel processing with sequence values in dict."""
        data = {f"key{i}": [f"val{j}" for j in range(3)] for i in range(15)}
        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=4)
        result_serial = dicttoxml.dicttoxml(data, parallel=False)
        assert result_parallel == result_serial

    def test_parallel_with_none_values(self) -> None:
        """Test parallel processing with None values."""
        data = {f"key{i}": None for i in range(15)}
        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=4)
        result_serial = dicttoxml.dicttoxml(data, parallel=False)
        assert result_parallel == result_serial

    def test_parallel_unsupported_type_error(self) -> None:
        """Test that unsupported types raise TypeError in parallel mode."""
        class CustomType:
            pass

        data = {f"key{i}": CustomType() for i in range(15)}
        with pytest.raises(TypeError, match="Unsupported data type"):
            dicttoxml.dicttoxml(data, parallel=True, workers=4)

    def test_parallel_list_unsupported_type_error(self) -> None:
        """Test that unsupported types in list raise TypeError in parallel mode."""
        class CustomType:
            pass

        data = [CustomType() for _ in range(200)]
        with pytest.raises(TypeError, match="Unsupported data type"):
            dicttoxml.dicttoxml(data, parallel=True, workers=4, chunk_size=50)

    def test_parallel_with_bool_values(self) -> None:
        """Test parallel processing with boolean values."""
        data = {f"key{i}": i % 2 == 0 for i in range(15)}
        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=4)
        result_serial = dicttoxml.dicttoxml(data, parallel=False)
        assert result_parallel == result_serial

    def test_parallel_with_datetime_values(self) -> None:
        """Test parallel processing with datetime values."""
        from datetime import datetime

        data = {f"key{i}": datetime(2024, 1, i + 1) for i in range(15)}
        result_parallel = dicttoxml.dicttoxml(data, parallel=True, workers=4)
        result_serial = dicttoxml.dicttoxml(data, parallel=False)
        assert result_parallel == result_serial

    def test_parallel_with_root_and_primitive(self) -> None:
        """Test parallel processing with root element and primitive value."""
        data = 123
        result = dicttoxml.dicttoxml(data, root=True, parallel=True, workers=4)
        assert b"<?xml version" in result
        assert b"123" in result
        assert b"<root" in result

    def test_get_optimal_workers_in_non_free_threaded(self) -> None:
        """Test get_optimal_workers returns min(4, cpu_count) in non-free-threaded mode."""
        import os
        from unittest.mock import patch

        cpu_count = os.cpu_count() or 4
        expected = min(4, cpu_count)

        with patch('json2xml.parallel.is_free_threaded', return_value=False):
            result = get_optimal_workers(None)
            assert result == expected
