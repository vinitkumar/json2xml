"""Tests for optional Rust backend selection in dicttoxml_fast."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

import json2xml.dicttoxml_fast as fast_module
from json2xml import dicttoxml as py_dicttoxml
from json2xml.backend_selector import ConversionRequest, rust_renders_identically


def _force_rust_backend(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Install a fake Rust backend so tests can exercise selection logic without PyO3.

    The payload gate is part of that backend, so it is stubbed with its pure-Python
    reference; without it the adapter would correctly refuse every request and these tests
    would exercise nothing.
    """
    rust_backend = Mock(return_value=b"<rust/>")
    monkeypatch.setattr(fast_module, "_use_rust", True)
    monkeypatch.setattr(fast_module, "_rust_dicttoxml", rust_backend)
    monkeypatch.setattr(
        fast_module, "_rust_payload_is_supported", rust_renders_identically
    )
    return rust_backend


# @lat: [[tests#Conversion behavior#Outdated Rust backends stay disabled]]
@pytest.mark.parametrize(
    ("escape", "expected"),
    [
        (Mock(return_value="\x00"), False),
        (Mock(side_effect=RuntimeError("broken backend")), False),
        (Mock(side_effect=ValueError("invalid XML")), True),
    ],
)
def test_rust_backend_must_reject_invalid_xml(escape: Mock, expected: bool) -> None:
    """Only backends that reject XML 1.0 control characters are safe to use."""
    assert fast_module._rejects_invalid_xml(escape) is expected


# @lat: [[tests#Conversion behavior#Fast wrapper exposes backend metadata]]
def test_fast_wrapper_reports_python_backend_when_rust_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backend metadata should reflect the active fallback backend."""
    monkeypatch.setattr(fast_module, "_use_rust", False)

    assert fast_module.is_rust_available() is False
    assert fast_module.get_backend() == "python"


# @lat: [[tests#Conversion behavior#Fast wrapper uses Rust for supported options]]
def test_fast_wrapper_uses_rust_when_available_for_supported_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Supported option combinations should go through the Rust callable when present."""
    rust_backend = _force_rust_backend(monkeypatch)

    result = fast_module.dicttoxml(
        {"name": "Ada"},
        root=False,
        custom_root="person",
        attr_type=False,
        item_wrap=False,
        cdata=True,
        list_headers=True,
    )

    assert result == b"<rust/>"
    rust_backend.assert_called_once_with(
        {"name": "Ada"},
        root=False,
        custom_root="person",
        attr_type=False,
        item_wrap=False,
        cdata=True,
        list_headers=True,
    )


def test_fast_wrapper_enforces_output_limit_for_rust_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact byte limits also apply when the optional Rust backend renders."""
    _force_rust_backend(monkeypatch)

    with pytest.raises(ValueError, match="XML output size limit exceeded"):
        fast_module.dicttoxml({"name": "Ada"}, max_output_bytes=6)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"ids": [1]}, b'id="'),
        ({"item_func": lambda parent: "entry"}, b"<entry"),
        (
            {"xml_namespaces": {"demo": "https://example.com/demo"}},
            b'xmlns:demo="https://example.com/demo"',
        ),
        ({"xpath_format": True}, b'xmlns="http://www.w3.org/2005/xpath-functions"'),
    ],
)
def test_fast_wrapper_falls_back_to_python_for_unsupported_options(
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict[str, Any],
    expected: bytes,
) -> None:
    """Unsupported Rust options should preserve Python semantics instead of calling Rust."""
    rust_backend = _force_rust_backend(monkeypatch)

    result = fast_module.dicttoxml({"items": [1, 2]}, **kwargs)

    assert expected in result
    rust_backend.assert_not_called()


# @lat: [[tests#Conversion behavior#Special keys force Python fallback]]
def test_fast_wrapper_falls_back_to_python_for_special_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Special @attrs/@val keys require Python processing even when Rust is installed."""
    rust_backend = _force_rust_backend(monkeypatch)

    result = fast_module.dicttoxml(
        {"records": [{"record": {"@attrs": {"id": "7"}, "@val": "Ada"}}]}
    )

    assert b'id="7"' in result
    assert b">Ada</record>" in result
    rust_backend.assert_not_called()


# @lat: [[tests#Conversion behavior#Root scalars keep Python fallback]]
def test_fast_wrapper_falls_back_to_python_for_root_scalars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Root scalar values should keep the legacy Python <item> wrapper shape."""
    rust_backend = _force_rust_backend(monkeypatch)

    result = fast_module.dicttoxml(0, custom_root="all")

    assert b'<item type="int">0</item>' in result
    rust_backend.assert_not_called()


def test_fast_wrapper_falls_back_to_python_when_rust_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contributors without json2xml_rs should still exercise the pure Python fallback."""
    rust_backend = Mock(return_value=b"<rust/>")
    monkeypatch.setattr(fast_module, "_use_rust", False)
    monkeypatch.setattr(fast_module, "_rust_dicttoxml", rust_backend)

    result = fast_module.dicttoxml({"name": "Ada"})

    assert b"<name" in result
    assert b">Ada</name>" in result
    rust_backend.assert_not_called()


# @lat: [[tests#Conversion behavior#Fast helper functions use Python fallback]]
def test_fast_helper_functions_use_python_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Helper exports should preserve behavior when Rust helpers are unavailable."""
    monkeypatch.setattr(fast_module, "_use_rust", False)
    monkeypatch.setattr(fast_module, "rust_escape_xml", None)
    monkeypatch.setattr(fast_module, "rust_wrap_cdata", None)

    assert fast_module.escape_xml("Ada & <XML>") == "Ada &amp; &lt;XML&gt;"
    assert fast_module.wrap_cdata("Ada <XML>") == "<![CDATA[Ada <XML>]]>"


def test_backend_without_the_payload_gate_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An extension predating the payload gate also predates the output parity fixes.

    Such a build would render admitted payloads differently from the Python serializer, so
    the adapter must decline every request rather than trust it.
    """
    _force_rust_backend(monkeypatch)
    monkeypatch.setattr(fast_module, "_rust_payload_is_supported", None)

    adapter = fast_module._RustBackendAdapter()
    request = ConversionRequest(
        obj={"a": 1},
        root=True,
        custom_root="root",
        ids=None,
        attr_type=True,
        item_wrap=True,
        item_func=None,
        cdata=False,
        xml_namespaces=None,
        list_headers=False,
        xpath_format=False,
        max_output_bytes=None,
        indent=None,
    )

    assert adapter.can_handle(request) is False
    assert fast_module.dicttoxml({"a": 1}) == py_dicttoxml.dicttoxml({"a": 1})
