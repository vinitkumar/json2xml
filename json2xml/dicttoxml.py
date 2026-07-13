from __future__ import annotations

import datetime
import logging
import numbers
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache
from io import BytesIO
from random import SystemRandom
from typing import Any, Union, cast

__lazy_modules__ = ["defusedxml.minidom"]

# Create a safe random number generator
_SAFE_RANDOM = SystemRandom()

# Set up logging
LOG = logging.getLogger("dicttoxml")
_XML_ESCAPE_CHARS = frozenset("&\"'<>")


class _XMLWriter:
    """Small UTF-8 byte writer used by the internal streaming serializer."""

    __slots__ = ("_buffer",)

    def __init__(self) -> None:
        self._buffer = BytesIO()

    def write(self, value: str) -> None:
        self._buffer.write(value.encode("utf-8"))

    def to_bytes(self) -> bytes:
        return self._buffer.getvalue()


def make_id(element: str, start: int = 100000, end: int = 999999) -> str:
    """
    Generate a random ID for a given element.

    Args:
        element (str): The element to generate an ID for.
        start (int, optional): The lower bound for the random number. Defaults to 100000.
        end (int, optional): The upper bound for the random number. Defaults to 999999.

    Returns:
        str: The generated ID.
    """
    return f"{element}_{_SAFE_RANDOM.randint(start, end)}"


def get_unique_id(element: str) -> str:
    """
    Generate an ID for a given element.

    Args:
        element (str): The element to generate an ID for.

    Returns:
        str: The generated ID.
    """
    return make_id(element)


ELEMENT = Union[
    str,
    int,
    float,
    bool,
    complex,
    Decimal,
    Fraction,
    numbers.Number,
    Sequence[Any],
    datetime.datetime,
    datetime.date,
    None,
    dict[str, Any],
]


def get_xml_type(val: Any) -> str:
    """
    Get the XML type of a given value.

    Args:
        val (ELEMENT): The value to get the type of.

    Returns:
        str: The XML type.
    """
    if val is None:
        return "null"
    val_type = type(val)
    if val_type is str:
        return "str"
    if val_type is int:
        return "int"
    if val_type is float:
        return "float"
    if val_type is bool:
        return "bool"
    if isinstance(val, numbers.Number):
        return "number"
    if isinstance(val, dict):
        return "dict"
    if isinstance(val, Sequence):
        return "list"
    return type(val).__name__


def escape_xml(s: str | int | float | numbers.Number | None) -> str:
    """
    Escape a string for use in XML.

    Args:
        s (str | numbers.Number): The string to escape.

    Returns:
        str: The escaped string.
    """
    if isinstance(s, str):
        if not _XML_ESCAPE_CHARS.intersection(s):
            return s
        s = s.replace("&", "&amp;")
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&apos;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
    return str(s)


def make_attrstring(attr: dict[str, Any]) -> str:
    """
    Create a string of XML attributes from a dictionary.

    Args:
        attr (dict[str, Any]): The dictionary of attributes.

    Returns:
        str: The string of XML attributes.
    """
    if not attr:
        return ""
    validate_xml_attr_names(attr)
    if len(attr) == 1:
        key, val = next(iter(attr.items()))
        if key == "type":
            return f' type="{val}"'
        return f' {key}="{escape_xml(val)}"'
    attrstring = " ".join(f'{k}="{escape_xml(v)}"' for k, v in attr.items())
    return f" {attrstring}"


def make_typed_attrstring(attr: dict[str, Any], xml_type: str) -> str:
    """Create XML attributes with a type value without mutating caller attrs."""
    if not attr:
        return f' type="{xml_type}"'

    typed_attr = dict(attr)
    typed_attr["type"] = xml_type
    return make_attrstring(typed_attr)


def _is_fast_valid_xml_name(key: str) -> bool:
    """Return True for ASCII XML names known to be accepted by the legacy parser."""
    if not key or not key.isascii() or ":" in key:
        return False
    first = key[0]
    if not (first.isalpha() or first == "_"):
        return False
    return all(char.isalnum() or char in {"-", "_", "."} for char in key[1:])


@lru_cache(maxsize=4096)
def key_is_valid_xml(key: str) -> bool:
    """
    Check if a key is a valid XML name.

    Args:
        key (str): The key to check.

    Returns:
        bool: True if the key is a valid XML name, False otherwise.
    """
    key = str(key)
    if _is_fast_valid_xml_name(key):
        return True
    if not key or key.isdigit() or ":" in key:
        return False

    from defusedxml.minidom import parseString

    test_xml = f'<?xml version="1.0" encoding="UTF-8" ?><{key}>foo</{key}>'
    try:
        parseString(test_xml)
        return True
    except Exception:  # minidom does not implement exceptions well
        return False


@lru_cache(maxsize=4096)
def key_is_valid_xml_attr(key: str) -> bool:
    """Return True when key can be emitted directly as an XML attribute name."""
    key = str(key)
    if not key:
        return False

    from defusedxml.minidom import parseString

    test_xml = f'<?xml version="1.0" encoding="UTF-8" ?><root {key}="value"></root>'
    try:
        parseString(test_xml)
        return True
    except Exception:  # minidom does not implement exceptions well
        return False


def validate_xml_attr_names(attr: dict[str, Any]) -> None:
    """Reject attributes that would make the generated XML malformed."""
    for key in attr:
        if not key_is_valid_xml_attr(key):
            raise ValueError(f"Invalid XML attribute name: {key}")


def make_valid_xml_name(key: str, attr: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return a valid XML element name and carry the original key as metadata when needed."""
    key = str(key)

    if key_is_valid_xml(key):
        return key, attr

    if key.isdigit():
        return f"n{key}", attr

    key_with_underscores = key.replace(" ", "_")
    if key_is_valid_xml(key_with_underscores):
        return key_with_underscores, attr

    if ":" in key and key_is_valid_xml(key.replace(":", "")):
        return key, attr

    attr["name"] = key
    return "key", attr


def wrap_cdata(s: str | int | float | numbers.Number) -> str:
    """Wraps a string into CDATA sections"""
    s = str(s).replace("]]>", "]]]]><![CDATA[>")
    return "<![CDATA[" + s + "]]>"


def default_item_func(parent: str) -> str:
    return "item"


# XPath 3.1 json-to-xml conversion
# Spec: https://www.w3.org/TR/xpath-functions-31/#json-to-xml-mapping
XPATH_FUNCTIONS_NS = "http://www.w3.org/2005/xpath-functions"


def get_xpath31_tag_name(val: Any) -> str:
    """
    Determine XPath 3.1 tag name by Python type.

    See: https://www.w3.org/TR/xpath-functions-31/#func-json-to-xml

    Args:
        val: The value to get the tag name for.

    Returns:
        str: The XPath 3.1 tag name (map, array, string, number, boolean, null).
    """
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "boolean"
    if isinstance(val, dict):
        return "map"
    if isinstance(val, (int, float, numbers.Number)):
        return "number"
    if isinstance(val, str):
        return "string"
    if isinstance(val, (bytes, bytearray)):
        return "string"
    if isinstance(val, Sequence):
        return "array"
    return "string"


# @lat: [[behavior#XPath 3.1 format]]
def convert_to_xpath31(obj: Any, parent_key: str | None = None) -> str:
    """
    Convert a Python object to XPath 3.1 json-to-xml format.

    See: https://www.w3.org/TR/xpath-functions-31/#json-to-xml-mapping

    Args:
        obj: The object to convert.
        parent_key: The key from the parent dict (used for key attribute).

    Returns:
        str: XML string in XPath 3.1 format.
    """
    output = _XMLWriter()
    _append_xpath31(output, obj, parent_key)
    return output.to_bytes().decode("utf-8")


def _append_xpath31(
    output: _XMLWriter,
    obj: Any,
    parent_key: str | None = None,
    namespace: bool = False,
) -> None:
    """Append XPath 3.1 json-to-xml output without building child strings."""
    key_attr = f' key="{escape_xml(parent_key)}"' if parent_key is not None else ""
    namespace_attr = f' xmlns="{XPATH_FUNCTIONS_NS}"' if namespace else ""
    tag_name = get_xpath31_tag_name(obj)

    if tag_name == "null":
        output.write(f"<null{namespace_attr}{key_attr}/>")
    elif tag_name == "boolean":
        output.write(f"<boolean{namespace_attr}{key_attr}>{str(obj).lower()}</boolean>")
    elif tag_name == "number":
        output.write(f"<number{namespace_attr}{key_attr}>{obj}</number>")
    elif tag_name == "string":
        output.write(f"<string{namespace_attr}{key_attr}>{escape_xml(str(obj))}</string>")
    elif tag_name == "map":
        output.write(f"<map{namespace_attr}{key_attr}>")
        for key, val in obj.items():
            _append_xpath31(output, val, key)
        output.write("</map>")
    elif tag_name == "array":
        output.write(f"<array{namespace_attr}{key_attr}>")
        for item in obj:
            _append_xpath31(output, item)
        output.write("</array>")
    else:
        output.write(f"<string{namespace_attr}{key_attr}>{escape_xml(str(obj))}</string>")


def convert(
    obj: Any,
    ids: Any,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    parent: str = "root",
    list_headers: bool = False,
) -> str:
    """Routes the elements of an object to the right function to convert them
    based on their data type"""
    output = _XMLWriter()
    _append_convert(
        output,
        obj,
        ids,
        attr_type,
        item_func,
        cdata,
        item_wrap,
        parent,
        list_headers=list_headers,
    )
    return output.to_bytes().decode("utf-8")


def is_primitive_type(val: Any) -> bool:
    return val is None or isinstance(val, (str, bool, numbers.Number))


def dict2xml_str(
    attr_type: bool,
    attr: dict[str, Any],
    item: dict[str, Any],
    item_func: Callable[[str], str],
    cdata: bool,
    item_name: str,
    item_wrap: bool,
    parentIsList: bool,
    parent: str = "",
    list_headers: bool = False,
) -> str:
    """
    parse dict2xml
    """
    output = _XMLWriter()
    _append_dict2xml_str(
        output,
        attr_type,
        attr,
        item,
        item_func,
        cdata,
        item_name,
        item_wrap,
        parentIsList,
        parent,
        list_headers=list_headers,
    )
    return output.to_bytes().decode("utf-8")


def list2xml_str(
    attr_type: bool,
    attr: dict[str, Any],
    item: Sequence[Any],
    item_func: Callable[[str], str],
    cdata: bool,
    item_name: str,
    item_wrap: bool,
    list_headers: bool = False,
) -> str:
    output = _XMLWriter()
    _append_list2xml_str(
        output,
        attr_type,
        attr,
        item,
        item_func,
        cdata,
        item_name,
        item_wrap,
        list_headers=list_headers,
    )
    return output.to_bytes().decode("utf-8")


def convert_dict(
    obj: dict[str, Any],
    ids: list[str],
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool = False
) -> str:
    """Converts a dict into an XML string."""
    output = _XMLWriter()
    _append_convert_dict(
        output,
        obj,
        ids,
        parent,
        attr_type,
        item_func,
        cdata,
        item_wrap,
        list_headers=list_headers,
    )
    return output.to_bytes().decode("utf-8")


def convert_list(
    items: Sequence[Any],
    ids: list[str] | None,
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool = False,
) -> str:
    """Converts a list into an XML string."""
    output = _XMLWriter()
    _append_convert_list(
        output,
        items,
        ids,
        parent,
        attr_type,
        item_func,
        cdata,
        item_wrap,
        list_headers=list_headers,
    )
    return output.to_bytes().decode("utf-8")


def _append_convert(
    output: _XMLWriter,
    obj: Any,
    ids: Any,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    parent: str = "root",
    list_headers: bool = False,
) -> None:
    """Append converted XML directly into output without building subtree strings."""
    item_name = item_func(parent)

    if isinstance(obj, bool):
        output.write(convert_bool(key=item_name, val=obj, attr_type=attr_type, cdata=cdata))
    elif isinstance(obj, numbers.Number):
        output.write(convert_kv(key=item_name, val=obj, attr_type=attr_type, attr={}, cdata=cdata))
    elif isinstance(obj, str):
        output.write(convert_kv(key=item_name, val=obj, attr_type=attr_type, attr={}, cdata=cdata))
    elif hasattr(obj, "isoformat") and isinstance(obj, (datetime.datetime, datetime.date)):
        output.write(
            convert_kv(
                key=item_name,
                val=obj.isoformat(),
                attr_type=attr_type,
                attr={},
                cdata=cdata,
            )
        )
    elif obj is None:
        output.write(convert_none(key=item_name, attr_type=attr_type, cdata=cdata))
    elif isinstance(obj, dict):
        _append_convert_dict(
            output,
            cast("dict[str, Any]", obj),
            ids,
            parent,
            attr_type,
            item_func,
            cdata,
            item_wrap,
            list_headers=list_headers,
        )
    elif isinstance(obj, Sequence):
        _append_convert_list(
            output,
            obj,
            ids,
            parent,
            attr_type,
            item_func,
            cdata,
            item_wrap,
            list_headers=list_headers,
        )
    else:
        raise TypeError(f"Unsupported data type: {obj} ({type(obj).__name__})")


def _append_dict2xml_str(
    output: _XMLWriter,
    attr_type: bool,
    attr: dict[str, Any],
    item: dict[str, Any],
    item_func: Callable[[str], str],
    cdata: bool,
    item_name: str,
    item_wrap: bool,
    parentIsList: bool,
    parent: str = "",
    list_headers: bool = False,
) -> None:
    """Append a dict element using the same shape as dict2xml_str."""
    ids: list[str] = []
    attr = dict(attr)

    if attr_type:
        attr["type"] = get_xml_type(item)
    has_custom_attrs = "@attrs" in item
    if has_custom_attrs:
        raw_attrs = item["@attrs"]
        val_attr = raw_attrs if isinstance(raw_attrs, dict) else dict(raw_attrs)
        rawitem = item["@val"] if "@val" in item else {
            key: value for key, value in item.items() if key != "@attrs"
        }
    else:
        val_attr = attr
        rawitem = item.get("@val", item)

    if parentIsList and list_headers:
        if len(val_attr) > 0 and not item_wrap:
            output.write(f"<{parent}{make_attrstring(val_attr)}>")
        else:
            output.write(f"<{parent}>")
        _append_rawitem(
            output,
            rawitem,
            ids,
            attr_type,
            item_func,
            cdata,
            item_wrap,
            item_name,
            list_headers,
        )
        output.write(f"</{parent}>")
    elif item.get("@flat", False) or (parentIsList and not item_wrap):
        _append_rawitem(
            output,
            rawitem,
            ids,
            attr_type,
            item_func,
            cdata,
            item_wrap,
            item_name,
            list_headers,
        )
    else:
        output.write(f"<{item_name}{make_attrstring(val_attr)}>")
        _append_rawitem(
            output,
            rawitem,
            ids,
            attr_type,
            item_func,
            cdata,
            item_wrap,
            item_name,
            list_headers,
        )
        output.write(f"</{item_name}>")


def _append_rawitem(
    output: _XMLWriter,
    rawitem: Any,
    ids: list[str],
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    item_name: str,
    list_headers: bool,
) -> None:
    if rawitem is None:
        return
    if isinstance(rawitem, bool):
        output.write("true" if rawitem else "false")
    elif isinstance(rawitem, (str, numbers.Number)):
        output.write(escape_xml(str(rawitem)))
    else:
        _append_convert(
            output,
            rawitem,
            ids,
            attr_type,
            item_func,
            cdata,
            item_wrap,
            item_name,
            list_headers=list_headers,
        )


def _append_list2xml_str(
    output: _XMLWriter,
    attr_type: bool,
    attr: dict[str, Any],
    item: Sequence[Any],
    item_func: Callable[[str], str],
    cdata: bool,
    item_name: str,
    item_wrap: bool,
    list_headers: bool = False,
) -> None:
    ids: list[str] = []
    attr = dict(attr)
    if attr_type:
        attr["type"] = get_xml_type(item)
    flat = False
    if item_name.endswith("@flat"):
        item_name = item_name[0:-5]
        flat = True

    if flat or (len(item) > 0 and is_primitive_type(item[0]) and not item_wrap) or list_headers:
        _append_convert_list(
            output,
            item,
            ids,
            item_name,
            attr_type,
            item_func,
            cdata,
            item_wrap,
            list_headers=list_headers,
        )
        return

    output.write(f"<{item_name}{make_attrstring(attr)}>")
    _append_convert_list(
        output,
        item,
        ids,
        item_name,
        attr_type,
        item_func,
        cdata,
        item_wrap,
        list_headers=list_headers,
    )
    output.write(f"</{item_name}>")


def _append_convert_dict(
    output: _XMLWriter,
    obj: dict[str, Any],
    ids: list[str],
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool = False,
) -> None:
    """Append a dict as XML without allocating a joined child subtree."""
    for key, val in obj.items():
        attr = {} if not ids else {"id": f"{get_unique_id(parent)}"}
        key_is_flat = isinstance(key, str) and key.endswith("@flat")
        xml_key = key[:-5] if key_is_flat else key

        key, attr = make_valid_xml_name(xml_key, attr)

        if isinstance(val, bool):
            output.write(convert_bool_valid_name(key, val, attr_type, attr))
        elif isinstance(val, (numbers.Number, str)):
            output.write(
                convert_kv_valid_name(
                    key=key, val=val, attr_type=attr_type, attr=attr, cdata=cdata
                )
            )
        elif hasattr(val, "isoformat"):
            output.write(
                convert_kv_valid_name(
                    key=key,
                    val=val.isoformat(),
                    attr_type=attr_type,
                    attr=attr,
                    cdata=cdata,
                )
            )
        elif isinstance(val, dict):
            _append_dict2xml_str(
                output,
                attr_type,
                attr,
                val,
                item_func,
                cdata,
                key,
                item_wrap,
                False,
                list_headers=list_headers,
            )
        elif isinstance(val, Sequence):
            _append_list2xml_str(
                output,
                attr_type=attr_type,
                attr=attr,
                item=val,
                item_func=item_func,
                cdata=cdata,
                item_name=f"{key}@flat" if key_is_flat else key,
                item_wrap=item_wrap,
                list_headers=list_headers,
            )
        elif not val:
            output.write(convert_none_valid_name(key, attr_type, attr))
        else:
            raise TypeError(f"Unsupported data type: {val} ({type(val).__name__})")


def _append_convert_list(
    output: _XMLWriter,
    items: Sequence[Any],
    ids: list[str] | None,
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool = False,
) -> None:
    """Append a list as XML without allocating a joined child subtree."""
    item_name = item_func(parent)
    if item_name.endswith("@flat"):
        item_name = item_name[:-5]
    item_name, item_name_attr = make_valid_xml_name(item_name, {})
    scalar_key = item_name if item_wrap else parent
    scalar_key, scalar_key_attr = make_valid_xml_name(scalar_key, {})
    this_id = get_unique_id(parent) if ids else None

    for i, item in enumerate(items):
        base_attr: dict[str, Any] | None = None
        if ids:
            base_attr = {"id": f"{this_id}_{i + 1}"}

        if isinstance(item, bool):
            attr = dict(base_attr) if base_attr else {}
            if item_name_attr:
                attr.update(item_name_attr)
            output.write(convert_bool_valid_name(item_name, item, attr_type, attr))
        elif isinstance(item, (numbers.Number, str)):
            attr = dict(base_attr) if base_attr else {}
            if scalar_key_attr:
                attr.update(scalar_key_attr)
            output.write(
                convert_kv_valid_name(
                    key=scalar_key,
                    val=item,
                    attr_type=attr_type,
                    attr=attr,
                    cdata=cdata,
                )
            )
        elif hasattr(item, "isoformat"):
            attr = dict(base_attr) if base_attr else {}
            if item_name_attr:
                attr.update(item_name_attr)
            output.write(
                convert_kv_valid_name(
                    key=item_name,
                    val=item.isoformat(),
                    attr_type=attr_type,
                    attr=attr,
                    cdata=cdata,
                )
            )
        elif isinstance(item, dict):
            attr = dict(base_attr) if base_attr else {}
            _append_dict2xml_str(
                output,
                attr_type=attr_type,
                attr=attr,
                item=item,
                item_func=item_func,
                cdata=cdata,
                item_name=item_name,
                item_wrap=item_wrap,
                parentIsList=True,
                parent=parent,
                list_headers=list_headers,
            )
        elif isinstance(item, Sequence):
            attr = dict(base_attr) if base_attr else {}
            _append_list2xml_str(
                output,
                attr_type=attr_type,
                attr=attr,
                item=item,
                item_func=item_func,
                cdata=cdata,
                item_name=item_name,
                item_wrap=item_wrap,
                list_headers=list_headers,
            )
        elif item is None:
            attr = dict(base_attr) if base_attr else {}
            if item_name_attr:
                attr.update(item_name_attr)
            output.write(convert_none_valid_name(item_name, attr_type, attr))
        else:
            raise TypeError(f"Unsupported data type: {item} ({type(item).__name__})")


def convert_kv(
    key: str,
    val: str | int | float | numbers.Number | datetime.datetime | datetime.date,
    attr_type: bool,
    attr: dict[str, Any] | None = None,
    cdata: bool = False,
) -> str:
    """Converts a number, string, or datetime into an XML element"""
    if attr is None:
        attr = {}
    key, attr = make_valid_xml_name(key, attr)

    # Convert datetime to isoformat string
    if hasattr(val, "isoformat") and isinstance(val, (datetime.datetime, datetime.date)):
        val = val.isoformat()

    if attr_type:
        attr["type"] = get_xml_type(val)
    attr_string = make_attrstring(attr)
    return f"<{key}{attr_string}>{wrap_cdata(val) if cdata else escape_xml(val)}</{key}>"


def convert_kv_valid_name(
    key: str,
    val: str | int | float | numbers.Number | datetime.datetime | datetime.date,
    attr_type: bool,
    attr: dict[str, Any],
    cdata: bool = False,
) -> str:
    """Converts a scalar into an XML element when the caller already validated the key."""
    if hasattr(val, "isoformat") and isinstance(val, (datetime.datetime, datetime.date)):
        val = val.isoformat()

    attr_string = make_typed_attrstring(attr, get_xml_type(val)) if attr_type else make_attrstring(attr)
    return f"<{key}{attr_string}>{wrap_cdata(val) if cdata else escape_xml(val)}</{key}>"


def convert_bool(
    key: str, val: bool, attr_type: bool, attr: dict[str, Any] | None = None, cdata: bool = False
) -> str:
    """Converts a boolean into an XML element"""
    if attr is None:
        attr = {}
    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr["type"] = get_xml_type(val)
    attr_string = make_attrstring(attr)
    return f"<{key}{attr_string}>{str(val).lower()}</{key}>"


def convert_bool_valid_name(
    key: str,
    val: bool,
    attr_type: bool,
    attr: dict[str, Any],
) -> str:
    """Converts a boolean when the caller already validated the key."""
    attr_string = make_typed_attrstring(attr, "bool") if attr_type else make_attrstring(attr)
    return f"<{key}{attr_string}>{'true' if val else 'false'}</{key}>"


def convert_none(
    key: str, attr_type: bool, attr: dict[str, Any] | None = None, cdata: bool = False
) -> str:
    """Converts a null value into an XML element"""
    if attr is None:
        attr = {}
    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr["type"] = get_xml_type(None)
    attr_string = make_attrstring(attr)
    return f"<{key}{attr_string}></{key}>"


def convert_none_valid_name(
    key: str, attr_type: bool, attr: dict[str, Any]
) -> str:
    """Converts a null value when the caller already validated the key."""
    attr_string = make_typed_attrstring(attr, "null") if attr_type else make_attrstring(attr)
    return f"<{key}{attr_string}></{key}>"


@dataclass(frozen=True, slots=True)
class SerializerConfig:
    """Normalized options for the pure Python serializer engine."""

    obj: ELEMENT
    root: bool
    custom_root: str
    ids: list[int] | None
    attr_type: bool
    item_wrap: bool
    item_func: Callable[[str], str]
    cdata: bool
    xml_namespaces: dict[str, Any] | None
    list_headers: bool
    xpath_format: bool


class _XPathDocumentRenderer:
    """Render the W3C XPath 3.1 JSON-to-XML document shape."""

    def __init__(self, config: SerializerConfig) -> None:
        self._config = config

    def render(self) -> bytes:
        output = _XMLWriter()
        output.write('<?xml version="1.0" encoding="UTF-8" ?>')
        tag_name = get_xpath31_tag_name(self._config.obj)
        if tag_name in {"map", "array"}:
            _append_xpath31(output, self._config.obj, namespace=True)
        else:
            output.write(f'<map xmlns="{XPATH_FUNCTIONS_NS}">')
            _append_xpath31(output, self._config.obj)
            output.write("</map>")
        return output.to_bytes()


class _NamespaceFormatter:
    """Keep namespace emission and schema-attribute quirks in one place."""

    @staticmethod
    def format(xml_namespaces: dict[str, Any] | None) -> str:
        if xml_namespaces is None:
            return ""

        namespace_parts: list[str] = []
        for prefix in xml_namespaces:
            if prefix == "xsi":
                for schema_att in xml_namespaces[prefix]:
                    if schema_att == "schemaInstance":
                        namespace_parts.append(
                            f' xmlns:{prefix}="{xml_namespaces[prefix]["schemaInstance"]}"'
                        )
                    elif schema_att == "schemaLocation":
                        namespace_parts.append(
                            f' xsi:{schema_att}="{xml_namespaces[prefix][schema_att]}"'
                        )
            elif prefix == "xmlns":
                namespace_parts.append(f' xmlns="{xml_namespaces[prefix]}"')
            else:
                namespace_parts.append(f' xmlns:{prefix}="{xml_namespaces[prefix]}"')
        return "".join(namespace_parts)


class _StandardDocumentRenderer:
    """Render the project-specific XML document shape."""

    def __init__(self, config: SerializerConfig) -> None:
        self._config = config

    def render(self) -> bytes:
        output = _XMLWriter()
        if self._config.root:
            self._render_with_root(output)
        else:
            self._render_fragment(output)
        return output.to_bytes()

    def _render_with_root(self, output: _XMLWriter) -> None:
        custom_root, root_attr = make_valid_xml_name(self._config.custom_root, {})
        namespace_str = _NamespaceFormatter.format(self._config.xml_namespaces)
        output.write('<?xml version="1.0" encoding="UTF-8" ?>')
        output.write(f"<{custom_root}{make_attrstring(root_attr)}{namespace_str}>")
        _append_convert(
            output,
            self._config.obj,
            self._config.ids,
            self._config.attr_type,
            self._config.item_func,
            self._config.cdata,
            self._config.item_wrap,
            parent=custom_root,
            list_headers=self._config.list_headers,
        )
        output.write(f"</{custom_root}>")

    def _render_fragment(self, output: _XMLWriter) -> None:
        _append_convert(
            output,
            self._config.obj,
            self._config.ids,
            self._config.attr_type,
            self._config.item_func,
            self._config.cdata,
            self._config.item_wrap,
            parent="",
            list_headers=self._config.list_headers,
        )


class _SerializerEngine:
    """Choose the document renderer while keeping helper semantics local."""

    def __init__(self, config: SerializerConfig) -> None:
        self._config = config

    def render(self) -> bytes:
        if self._config.xpath_format:
            return _XPathDocumentRenderer(self._config).render()
        return _StandardDocumentRenderer(self._config).render()


# @lat: [[architecture#Conversion engine]]
def dicttoxml(
    obj: ELEMENT,
    root: bool = True,
    custom_root: str = "root",
    ids: list[int] | None = None,
    attr_type: bool = True,
    item_wrap: bool = True,
    item_func: Callable[[str], str] = default_item_func,
    cdata: bool = False,
    xml_namespaces: dict[str, Any] | None = None,
    list_headers: bool = False,
    xpath_format: bool = False,
) -> bytes:
    """
    Converts a python object into XML.

    :param dict obj:
        dictionary

    :param bool root:
        Default is True
        specifies wheter the output is wrapped in an XML root element

    :param custom_root:
        Default is 'root'
        allows you to specify a custom root element.

    :param bool ids:
        Default is False
        specifies whether elements get unique ids.

    :param bool attr_type:
        Default is True
        specifies whether elements get a data type attribute.

    :param bool item_wrap:
        Default is True
        specifies whether to nest items in array in <item/> Example if True

        ..code-block:: python

            data = {'bike': ['blue', 'green']}

        .. code-block:: xml

            <bike>
            <item>blue</item>
            <item>green</item>
            </bike>

        Example if False

        ..code-block:: python

            data = {'bike': ['blue', 'green']}

        ..code-block:: xml

            <bike>blue</bike>
            <bike>green</bike>'

    :param item_func:
        items in a list. Default is 'item'
        specifies what function should generate the element name for

    :param bool cdata:
        Default is False
        specifies whether string values should be wrapped in CDATA sections.

    :param xml_namespaces:
        is a dictionary where key is xmlns prefix and value the urn, Default is {}. Example:

        .. code-block:: python

            { 'flex': 'http://www.w3.org/flex/flexBase', 'xsl': "http://www.w3.org/1999/XSL/Transform"}

        results in

        .. code-block:: xml

            <root xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:flex="http://www.w3.org/flex/flexBase">

    :param bool list_headers:
        Default is False
        Repeats the header for every element in a list. Example if True:

        .. code-block:: python

            "Bike": [
            {'frame_color': 'red'},
            {'frame_color': 'green'}
            ]}

        results in

        .. code-block:: xml

            <Bike><frame_color>red</frame_color></Bike>
            <Bike><frame_color>green</frame_color></Bike>

    :param bool xpath_format:
        Default is False
        When True, produces XPath 3.1 json-to-xml compliant output as specified
        by W3C (https://www.w3.org/TR/xpath-functions-31/#func-json-to-xml).
        Uses type-based element names (map, array, string, number, boolean, null)
        with key attributes and the http://www.w3.org/2005/xpath-functions namespace.

        Example:

        .. code-block:: python

            {"name": "John", "age": 30}

        results in

        .. code-block:: xml

            <map xmlns="http://www.w3.org/2005/xpath-functions">
              <string key="name">John</string>
              <number key="age">30</number>
            </map>

    Dictionaries-keys with special char '@' has special meaning:
    @attrs: This allows custom xml attributes:

    .. code-block:: python

        {'@attr':{'a':'b'}, 'x':'y'}

    results in

    .. code-block:: xml

        <root a="b"><x>y</x></root>

    @flat: If a key ends with @flat (or dict contains key '@flat'),
    encapsulating node is omitted. Similar to item_wrap.
    @val: @attrs requires complex dict type. If primitive type should be used, then @val is used as key.
    To add custom xml-attributes on a list {'list': [4, 5, 6]}, you do this:

    .. code-block:: python

        {'list': {'@attrs': {'a':'b','c':'d'}, '@val': [4, 5, 6]}

    which results in

    .. code-block:: xml

        <list a="b" c="d"><item>4</item><item>5</item><item>6</item></list>

    """
    config = SerializerConfig(
        obj=obj,
        root=root,
        custom_root=custom_root,
        ids=ids,
        attr_type=attr_type,
        item_wrap=item_wrap,
        item_func=item_func,
        cdata=cdata,
        xml_namespaces=xml_namespaces,
        list_headers=list_headers,
        xpath_format=xpath_format,
    )
    return _SerializerEngine(config).render()
