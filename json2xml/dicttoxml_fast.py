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
from dataclasses import dataclass
from typing import Any

from .backend_selector import (
    BackendSelector,
    ConversionRequest,
    rust_renders_root_identically,
)

RustStringTransform = Callable[[str], str]

LOG = logging.getLogger("dicttoxml_fast")

# Try to import the Rust implementation
_use_rust = False
_rust_dicttoxml: Callable[..., bytes] | None = None
# The payload gate walks the whole input, so run it natively when the extension provides it.
_rust_payload_is_supported: Callable[[Any], bool] | None = None
rust_escape_xml: RustStringTransform | None = None
rust_wrap_cdata: RustStringTransform | None = None


def _rejects_invalid_xml(escape: RustStringTransform) -> bool:
    """Return whether an optional backend enforces XML 1.0 characters."""
    try:
        escape("\x00")
    except ValueError:
        return True
    except Exception:
        return False
    return False


try:
    from json2xml_rs import dicttoxml as _rust_dicttoxml  # pragma: no cover
    from json2xml_rs import escape_xml_py as rust_escape_xml  # pragma: no cover
    from json2xml_rs import (  # pragma: no cover
        payload_is_supported as _rust_payload_is_supported,
    )
    from json2xml_rs import wrap_cdata_py as rust_wrap_cdata  # pragma: no cover

    if _rejects_invalid_xml(rust_escape_xml):  # pragma: no cover
        _use_rust = True  # pragma: no cover
        LOG.debug("Using Rust backend for dicttoxml")  # pragma: no cover
    else:  # pragma: no cover
        LOG.warning(  # pragma: no cover
            "Ignoring an outdated Rust backend that permits invalid XML characters"
        )
except ImportError:  # pragma: no cover
    # Builds before payload_is_supported existed also predate the output parity fixes, so a
    # failed import of any name here correctly leaves the Python serializer in charge.
    LOG.debug("Rust backend not available or too old, using pure Python")

# Import the pure Python implementation as fallback.
import json2xml.dicttoxml as _py_dicttoxml  # noqa: E402


def is_rust_available() -> bool:
    """Check if the Rust backend is available."""
    return _use_rust


def get_backend() -> str:
    """Return the name of the current backend ('rust' or 'python')."""
    return "rust" if _use_rust else "python"


@dataclass(frozen=True, slots=True)
class _RustBackendAdapter:
    """Adapter for the optional Rust backend."""

    name: str = "rust"

    def can_handle(self, request: ConversionRequest) -> bool:
        if (
            not _use_rust
            or _rust_dicttoxml is None
            or _rust_payload_is_supported is None
        ):
            return False

        return not (
            request.ids is not None
            or request.item_func is not None
            or request.xml_namespaces
            or request.xpath_format
            or request.indent is not None
            or not isinstance(request.obj, (dict, list))
            or not rust_renders_root_identically(request.root, request.custom_root)
            # The native walk keeps this gate from costing more than the conversion it
            # guards; rust_renders_identically is its pure-Python reference.
            or not _rust_payload_is_supported(request.obj)
        )

    def render(self, request: ConversionRequest) -> bytes:
        assert _rust_dicttoxml is not None
        output = _rust_dicttoxml(
            request.obj,
            root=request.root,
            custom_root=request.custom_root,
            attr_type=request.attr_type,
            item_wrap=request.item_wrap,
            cdata=request.cdata,
            list_headers=request.list_headers,
        )
        if (
            request.max_output_bytes is not None
            and len(output) > request.max_output_bytes
        ):
            raise ValueError("XML output size limit exceeded")
        return output


@dataclass(frozen=True, slots=True)
class _PythonBackendAdapter:
    """Adapter for the compatibility-preserving Python backend."""

    python_dicttoxml: Callable[..., bytes]
    default_item_func: Callable[[str], str]

    name: str = "python"

    def can_handle(self, request: ConversionRequest) -> bool:
        return True

    def render(self, request: ConversionRequest) -> bytes:
        return self.python_dicttoxml(
            request.obj,
            root=request.root,
            custom_root=request.custom_root,
            ids=request.ids,
            attr_type=request.attr_type,
            item_wrap=request.item_wrap,
            item_func=request.item_func or self.default_item_func,
            cdata=request.cdata,
            xml_namespaces=request.xml_namespaces,
            list_headers=request.list_headers,
            xpath_format=request.xpath_format,
            max_output_bytes=request.max_output_bytes,
            indent=request.indent,
        )


_BACKEND_SELECTOR = BackendSelector(
    _RustBackendAdapter(),
    _PythonBackendAdapter(_py_dicttoxml.dicttoxml, _py_dicttoxml.default_item_func),
)


# @lat: [[architecture#Backend selection]]
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
    max_output_bytes: int | None = None,
    indent: str | None = None,
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
        max_output_bytes: Reject output larger than this encoded byte count
        indent: Indentation unit for pretty output (not supported in Rust)

    Returns:
        UTF-8 encoded XML as bytes
    """
    request = ConversionRequest(
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
        max_output_bytes=max_output_bytes,
        indent=indent,
    )
    return _BACKEND_SELECTOR.render(request)


# Re-export commonly used functions
def escape_xml(s: str) -> str:
    """Escape special XML characters in a string."""
    if _use_rust and rust_escape_xml is not None:  # pragma: no cover
        return rust_escape_xml(s)
    return _py_dicttoxml.escape_xml(s)


def wrap_cdata(s: str) -> str:
    """Wrap a string in a CDATA section."""
    if _use_rust and rust_wrap_cdata is not None:  # pragma: no cover
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
