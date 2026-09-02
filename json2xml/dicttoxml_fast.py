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
import numbers
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import json2xml.dicttoxml as _py_dicttoxml

from .backend_selector import BackendSelector, rust_renders_root_identically
from .dicttoxml import SerializerConfig

RustStringTransform = Callable[[str], str]

LOG = logging.getLogger(__name__)

# Limits are passed to the extension as u64; anything larger stays on the Python walk.
_NATIVE_LIMIT_MAX = 2**64 - 1


@dataclass(frozen=True, slots=True)
class _RustBindings:
    """Callables exported by a ``json2xml_rs`` build the selector may use."""

    dicttoxml: Callable[..., bytes]
    # The payload gate walks the whole input, so it runs natively when available.
    payload_is_supported: Callable[..., bool]
    escape_xml: RustStringTransform
    wrap_cdata: RustStringTransform
    # Builds before 0.6.0 cannot enforce depth and item limits during that walk.
    enforces_limits: bool


def _rejects_invalid_xml(escape: RustStringTransform) -> bool:
    """Return whether an optional backend enforces XML 1.0 characters."""
    try:
        escape("\x00")
    except ValueError:
        return True
    except Exception:
        return False
    return False


def _accepts_limits(payload_is_supported: Callable[..., bool]) -> bool:
    """Return whether the payload gate takes ``max_depth`` and ``max_items``."""
    try:
        payload_is_supported({}, max_depth=1, max_items=1)
    except TypeError:
        return False
    return True


def _load_rust_bindings() -> _RustBindings | None:
    """Import ``json2xml_rs`` and refuse builds that would change output or safety."""
    try:
        import json2xml_rs
    except ImportError:
        LOG.debug("Rust backend not available, using pure Python")
        return None

    try:
        bindings = _RustBindings(
            dicttoxml=json2xml_rs.dicttoxml,
            payload_is_supported=json2xml_rs.payload_is_supported,
            escape_xml=json2xml_rs.escape_xml_py,
            wrap_cdata=json2xml_rs.wrap_cdata_py,
            enforces_limits=_accepts_limits(json2xml_rs.payload_is_supported),
        )
    except AttributeError:
        # Builds before payload_is_supported existed also predate the output parity
        # fixes, so they must leave the Python serializer in charge.
        LOG.debug("Ignoring an outdated Rust backend that predates the payload gate")
        return None

    if not _rejects_invalid_xml(bindings.escape_xml):
        LOG.warning(
            "Ignoring an outdated Rust backend that permits invalid XML characters"
        )
        return None

    LOG.debug("Using Rust backend for dicttoxml")
    return bindings


_RUST = _load_rust_bindings()


def is_rust_available() -> bool:
    """Check if the Rust backend is available."""
    return _RUST is not None


def get_backend() -> str:
    """Return the name of the current backend ('rust' or 'python')."""
    return "rust" if _RUST is not None else "python"


def check_conversion_budget(obj: Any, max_depth: int, max_items: int) -> bool:
    """Enforce nesting and item limits during the native payload walk.

    Returns True when the native walk completed within budget, so the caller can
    skip its Python-level walk. Returns False when the caller must run that walk
    instead: no usable extension, a build without limit support, a limit outside
    the native range, or a payload outside the exact subset the gate walks.

    :raises ValueError: If ``obj`` exceeds ``max_depth`` or ``max_items``.
    """
    rust = _RUST
    if rust is None or not rust.enforces_limits:
        return False
    if max_depth > _NATIVE_LIMIT_MAX or max_items > _NATIVE_LIMIT_MAX:
        return False
    return rust.payload_is_supported(obj, max_depth=max_depth, max_items=max_items)


@dataclass(frozen=True, slots=True)
class _RustBackendAdapter:
    """Adapter for the optional Rust backend."""

    name: str = "rust"

    def can_handle(self, request: SerializerConfig) -> bool:
        rust = _RUST
        if rust is None:
            return False

        return not (
            request.ids is not None
            or request.item_func is not _py_dicttoxml.default_item_func
            or request.xml_namespaces
            or request.xpath_format
            or request.indent is not None
            or not isinstance(request.obj, (dict, list))
            or not rust_renders_root_identically(request.root, request.custom_root)
            # The native walk keeps this gate from costing more than the conversion it
            # guards; rust_renders_identically is its pure-Python reference.
            or not rust.payload_is_supported(request.obj)
        )

    def render(self, request: SerializerConfig) -> bytes:
        assert _RUST is not None
        output = _RUST.dicttoxml(
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

    name: str = "python"

    def can_handle(self, request: SerializerConfig) -> bool:
        return True

    def render(self, request: SerializerConfig) -> bytes:
        return _py_dicttoxml.serialize(request)


_BACKEND_SELECTOR = BackendSelector(_RustBackendAdapter(), _PythonBackendAdapter())


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
    request = SerializerConfig(
        obj=obj,
        root=root,
        custom_root=custom_root,
        ids=ids,
        attr_type=attr_type,
        item_wrap=item_wrap,
        item_func=_py_dicttoxml.default_item_func if item_func is None else item_func,
        cdata=cdata,
        xml_namespaces=xml_namespaces,
        list_headers=list_headers,
        xpath_format=xpath_format,
        max_output_bytes=max_output_bytes,
        indent=indent,
    )
    return _BACKEND_SELECTOR.render(request)


# Re-export commonly used functions. The Rust helpers take str only, so scalars
# are rendered the way the Python helpers render them before crossing over.
def escape_xml(s: str | int | float | numbers.Number | None) -> str:
    """Escape special XML characters in a string or scalar value.

    Scalar values (int, float, numbers.Number, or None) are converted with str().
    """
    if _RUST is None:
        return _py_dicttoxml.escape_xml(s)
    return _RUST.escape_xml(s if isinstance(s, str) else str(s))


def wrap_cdata(s: str | int | float | numbers.Number) -> str:
    """Wrap a string or scalar value in a CDATA section.

    Scalar values (int, float, or numbers.Number) are converted with str().
    """
    if _RUST is None:
        return _py_dicttoxml.wrap_cdata(s)
    return _RUST.wrap_cdata(s if isinstance(s, str) else str(s))


# Export the same API as the original dicttoxml module
__all__ = [
    "dicttoxml",
    "escape_xml",
    "wrap_cdata",
    "is_rust_available",
    "get_backend",
]
