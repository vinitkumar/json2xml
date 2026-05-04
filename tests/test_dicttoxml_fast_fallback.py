"""Tests for optional Rust backend selection in dicttoxml_fast."""
from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

import json2xml.dicttoxml_fast as fast_module


def _force_rust_backend(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Install a fake Rust backend so tests can exercise selection logic without PyO3."""
    rust_backend = Mock(return_value=b"<rust/>")
    monkeypatch.setattr(fast_module, "_USE_RUST", True)
    monkeypatch.setattr(fast_module, "_rust_dicttoxml", rust_backend)
    return rust_backend


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


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"ids": [1]}, b'id="'),
        ({"item_func": lambda parent: "entry"}, b"<entry"),
        ({"xml_namespaces": {"demo": "https://example.com/demo"}}, b'xmlns:demo="https://example.com/demo"'),
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

    result = fast_module.dicttoxml({"record": {"@attrs": {"id": "7"}, "@val": "Ada"}})

    assert b'id="7"' in result
    assert b">Ada</record>" in result
    rust_backend.assert_not_called()


def test_fast_wrapper_falls_back_to_python_when_rust_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contributors without json2xml_rs should still exercise the pure Python fallback."""
    rust_backend = Mock(return_value=b"<rust/>")
    monkeypatch.setattr(fast_module, "_USE_RUST", False)
    monkeypatch.setattr(fast_module, "_rust_dicttoxml", rust_backend)

    result = fast_module.dicttoxml({"name": "Ada"})

    assert b"<name" in result
    assert b">Ada</name>" in result
    rust_backend.assert_not_called()
