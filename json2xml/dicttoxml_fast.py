"""
Fast dicttoxml implementation with automatic backend selection.

This module provides a dicttoxml function that automatically uses the
high-performance Rust implementation when available, falling back to
the pure Python implementation otherwise.

Usage:
    from json2xml.dicttoxml_fast import dicttoxml

    # Automatically uses fastest available backend
    xml_bytes = dicttoxml({"name": "John", "age": 30})
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

LOG = logging.getLogger("dicttoxml_fast")

# Try to import the Rust implementation
_USE_RUST = False
_rust_dicttoxml = None

try:
    from json2xml_rs import dicttoxml as _rust_dicttoxml
    from json2xml_rs import escape_xml_py as rust_escape_xml
    from json2xml_rs import wrap_cdata_py as rust_wrap_cdata
    _USE_RUST = True
    LOG.debug("Using Rust backend for dicttoxml")
except ImportError:
    LOG.debug("Rust backend not available, using pure Python")
    rust_escape_xml = None
    rust_wrap_cdata = None

# Import the pure Python implementation as fallback
from json2xml import dicttoxml as _py_dicttoxml


def is_rust_available() -> bool:
    """Check if the Rust backend is available."""
    return _USE_RUST


def get_backend() -> str:
    """Return the name of the current backend ('rust' or 'python')."""
    return "rust" if _USE_RUST else "python"


def dicttoxml(
    obj: Any,
    root: bool = True,
    custom_root: str = "root",
    ids: list[int] | None = None,
    attr_type: bool = True,
    item_wrap: bool = True,
    item_func: Callable[[str], str] | None = None,
    cdata: bool = False,
    xml_namespaces: dict[str, Any] | None = None,
    list_headers: bool = False,
    xpath_format: bool = False,
) -> bytes:
    """
    Convert a Python dict or list to XML.

    This function automatically uses the Rust backend when available for
    maximum performance, falling back to pure Python for unsupported features.

    Args:
        obj: The Python object to convert (dict or list)
        root: Include XML declaration and root element (default: True)
        custom_root: Name of the root element (default: "root")
        ids: Generate unique IDs for elements (not supported in Rust)
        attr_type: Include type attributes on elements (default: True)
        item_wrap: Wrap list items in <item> tags (default: True)
        item_func: Custom function for item names (not supported in Rust)
        cdata: Wrap string values in CDATA sections (default: False)
        xml_namespaces: XML namespace definitions (not supported in Rust)
        list_headers: Repeat parent tag for each list item (default: False)
        xpath_format: Use XPath 3.1 format (not supported in Rust)

    Returns:
        UTF-8 encoded XML as bytes
    """
    # Features that require Python fallback
    needs_python = (
        ids is not None
        or item_func is not None
        or xml_namespaces
        or xpath_format
    )

    # Check for special dict keys that require Python
    if not needs_python and isinstance(obj, dict):
        needs_python = _has_special_keys(obj)

    if _USE_RUST and not needs_python and _rust_dicttoxml is not None:
        # Use fast Rust implementation
        return _rust_dicttoxml(
            obj,
            root=root,
            custom_root=custom_root,
            attr_type=attr_type,
            item_wrap=item_wrap,
            cdata=cdata,
            list_headers=list_headers,
        )
    else:
        # Fall back to pure Python
        return _py_dicttoxml.dicttoxml(
            obj,
            root=root,
            custom_root=custom_root,
            ids=ids,
            attr_type=attr_type,
            item_wrap=item_wrap,
            item_func=item_func or _py_dicttoxml.default_item_func,
            cdata=cdata,
            xml_namespaces=xml_namespaces or {},
            list_headers=list_headers,
            xpath_format=xpath_format,
        )


def _has_special_keys(obj: Any) -> bool:
    """Check if a dict contains special keys that require Python processing."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            if isinstance(key, str) and (
                key.startswith("@") or key.endswith("@flat")
            ):
                return True
            if _has_special_keys(val):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if _has_special_keys(item):
                return True
    return False


# Re-export commonly used functions
def escape_xml(s: str) -> str:
    """Escape special XML characters in a string."""
    if _USE_RUST and rust_escape_xml is not None:
        return rust_escape_xml(s)
    return _py_dicttoxml.escape_xml(s)


def wrap_cdata(s: str) -> str:
    """Wrap a string in a CDATA section."""
    if _USE_RUST and rust_wrap_cdata is not None:
        return rust_wrap_cdata(s)
    return _py_dicttoxml.wrap_cdata(s)


# Export the same API as the original dicttoxml module
__all__ = [
    "dicttoxml",
    "escape_xml",
    "wrap_cdata",
    "is_rust_available",
    "get_backend",
]
