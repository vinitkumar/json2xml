"""Tests for optional Rust backend selection in dicttoxml_fast."""

from __future__ import annotations

import logging
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

import json2xml.dicttoxml_fast as fast_module
from json2xml import dicttoxml as py_dicttoxml
from json2xml.backend_selector import rust_renders_identically
from json2xml.dicttoxml_fast import _RustBindings


def _gate_with_limits(
    obj: Any, max_depth: int | None = None, max_items: int | None = None
) -> bool:
    """Reference gate with the keyword signature of a limit-enforcing extension."""
    return rust_renders_identically(obj)


def _fake_bindings(**overrides: Any) -> _RustBindings:
    """Build Rust bindings backed by the Python reference implementations."""
    fields: dict[str, Any] = {
        "dicttoxml": Mock(return_value=b"<rust/>"),
        "payload_is_supported": _gate_with_limits,
        "escape_xml": py_dicttoxml.escape_xml,
        "wrap_cdata": py_dicttoxml.wrap_cdata,
        "enforces_limits": True,
    }
    fields.update(overrides)
    return _RustBindings(**fields)


def _force_rust_backend(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Install a fake Rust backend so tests can exercise selection logic without PyO3.

    The payload gate is part of that backend, so it is stubbed with its pure-Python
    reference; without it the adapter would correctly refuse every request and these tests
    would exercise nothing.
    """
    rust_backend = Mock(return_value=b"<rust/>")
    monkeypatch.setattr(fast_module, "_RUST", _fake_bindings(dicttoxml=rust_backend))
    return rust_backend


def _fake_extension(monkeypatch: pytest.MonkeyPatch, **exports: Any) -> None:
    """Register a stand-in ``json2xml_rs`` module exposing only ``exports``."""
    monkeypatch.setitem(sys.modules, "json2xml_rs", SimpleNamespace(**exports))


_COMPLETE_EXPORTS: dict[str, Any] = {
    "dicttoxml": Mock(return_value=b"<rust/>"),
    "payload_is_supported": rust_renders_identically,
    "escape_xml_py": py_dicttoxml.escape_xml,
    "wrap_cdata_py": py_dicttoxml.wrap_cdata,
}


# @lat: [[tests#Conversion behavior#Rust backend loader refuses unusable builds]]
def test_loader_returns_none_when_extension_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "json2xml_rs", None)

    assert fast_module._load_rust_bindings() is None


def test_loader_refuses_builds_without_the_payload_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An extension predating the payload gate also predates the output parity fixes."""
    exports = {
        k: v for k, v in _COMPLETE_EXPORTS.items() if k != "payload_is_supported"
    }
    _fake_extension(monkeypatch, **exports)

    assert fast_module._load_rust_bindings() is None


def test_loader_refuses_builds_that_permit_invalid_xml(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _fake_extension(monkeypatch, **{**_COMPLETE_EXPORTS, "escape_xml_py": str})

    with caplog.at_level(logging.WARNING, logger="json2xml.dicttoxml_fast"):
        assert fast_module._load_rust_bindings() is None

    assert "permits invalid XML characters" in caplog.text


def test_loader_binds_a_complete_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_extension(monkeypatch, **_COMPLETE_EXPORTS)

    bindings = fast_module._load_rust_bindings()

    assert bindings == _RustBindings(
        dicttoxml=_COMPLETE_EXPORTS["dicttoxml"],
        payload_is_supported=rust_renders_identically,
        escape_xml=py_dicttoxml.escape_xml,
        wrap_cdata=py_dicttoxml.wrap_cdata,
        enforces_limits=False,
    )


# @lat: [[tests#Conversion behavior#Native conversion budget]]
def test_loader_detects_builds_that_enforce_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A gate that accepts limit keywords lets Json2xml skip its Python walk."""
    _fake_extension(
        monkeypatch, **{**_COMPLETE_EXPORTS, "payload_is_supported": _gate_with_limits}
    )

    bindings = fast_module._load_rust_bindings()

    assert bindings is not None
    assert bindings.enforces_limits is True


def test_budget_check_defers_to_python_without_rust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fast_module, "_RUST", None)

    assert fast_module.check_conversion_budget({"a": 1}, 10, 10) is False


def test_budget_check_defers_when_build_cannot_enforce_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = Mock(return_value=True)
    monkeypatch.setattr(
        fast_module,
        "_RUST",
        _fake_bindings(payload_is_supported=gate, enforces_limits=False),
    )

    assert fast_module.check_conversion_budget({"a": 1}, 10, 10) is False
    gate.assert_not_called()


def test_budget_check_defers_for_limits_beyond_native_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = Mock(return_value=True)
    monkeypatch.setattr(fast_module, "_RUST", _fake_bindings(payload_is_supported=gate))

    assert fast_module.check_conversion_budget({"a": 1}, 2**64, 10) is False
    assert fast_module.check_conversion_budget({"a": 1}, 10, 2**64) is False
    gate.assert_not_called()


def test_budget_check_runs_natively(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = Mock(return_value=True)
    monkeypatch.setattr(fast_module, "_RUST", _fake_bindings(payload_is_supported=gate))

    assert fast_module.check_conversion_budget({"a": 1}, 10, 20) is True
    gate.assert_called_once_with({"a": 1}, max_depth=10, max_items=20)


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
    monkeypatch.setattr(fast_module, "_RUST", None)

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
    monkeypatch.setattr(fast_module, "_RUST", None)

    result = fast_module.dicttoxml({"name": "Ada"})

    assert b"<name" in result
    assert b">Ada</name>" in result


# @lat: [[tests#Conversion behavior#Fast helper functions use Python fallback]]
def test_fast_helper_functions_use_python_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Helper exports should preserve behavior when Rust helpers are unavailable."""
    monkeypatch.setattr(fast_module, "_RUST", None)

    assert fast_module.escape_xml("Ada & <XML>") == "Ada &amp; &lt;XML&gt;"
    assert fast_module.wrap_cdata("Ada <XML>") == "<![CDATA[Ada <XML>]]>"


def _str_only(transform: Any) -> Any:
    """Mimic a PyO3 ``&str`` parameter, which rejects every non-str argument."""

    def guarded(value: Any) -> str:
        if not isinstance(value, str):
            raise TypeError(f"'{type(value).__name__}' object is not a 'str'")
        return transform(value)

    return guarded


# @lat: [[tests#Conversion behavior#Fast helper functions accept every scalar]]
def test_fast_helpers_coerce_scalars_before_calling_rust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public helpers accept the same scalars on both backends."""
    bindings = _fake_bindings(
        escape_xml=_str_only(py_dicttoxml.escape_xml),
        wrap_cdata=_str_only(py_dicttoxml.wrap_cdata),
    )
    monkeypatch.setattr(fast_module, "_RUST", bindings)

    assert fast_module.escape_xml(5) == py_dicttoxml.escape_xml(5) == "5"
    assert fast_module.wrap_cdata(1.5) == py_dicttoxml.wrap_cdata(1.5)
    assert fast_module.escape_xml("a<b") == "a&lt;b"
