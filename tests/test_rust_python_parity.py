"""Parity contract between the optional Rust backend and the Python serializer.

The selector promises that switching backends never changes output. These tests pin that
promise from both sides: the gate keeps payloads the native writer cannot reproduce on the
Python serializer, and everything the gate does admit renders byte-identically.
"""

from __future__ import annotations

import datetime
import itertools
import random
from decimal import Decimal
from fractions import Fraction
from typing import Any

import pytest

from json2xml import dicttoxml as py_dicttoxml
from json2xml.backend_selector import (
    rust_renders_identically,
    rust_renders_root_identically,
)

try:
    from json2xml_rs import (
        dicttoxml as rust_dicttoxml,  # type: ignore[import-not-found]
    )

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

requires_rust = pytest.mark.skipif(
    not RUST_AVAILABLE, reason="Rust extension not installed"
)

# root, attr_type, item_wrap, cdata, list_headers
OPTION_MATRIX = list(itertools.product([True, False], repeat=5))


def _options(combo: tuple[bool, ...]) -> dict[str, Any]:
    root, attr_type, item_wrap, cdata, list_headers = combo
    return {
        "root": root,
        "custom_root": "root",
        "attr_type": attr_type,
        "item_wrap": item_wrap,
        "cdata": cdata,
        "list_headers": list_headers,
    }


# @lat: [[tests#Rust backend parity#Gate rejects payloads Rust cannot reproduce]]
@pytest.mark.parametrize(
    "value",
    [
        Decimal("1.5"),
        Fraction(1, 3),
        1 + 2j,
        datetime.datetime(2026, 1, 1),
        datetime.date(2026, 1, 1),
        {1, 2},
        b"bytes",
        bytearray(b"x"),
    ],
)
def test_gate_rejects_value_types_python_classifies_differently(value: Any) -> None:
    """Values Python routes through its isinstance fallbacks stay on Python.

    The native writer reaches most of these through ``str()``, which loses Python's
    ``number`` type attribute and its ISO datetime separator.
    """
    assert not rust_renders_identically({"a": value})


def test_gate_rejects_scalar_subclasses() -> None:
    """Subclasses take Python's fallback classification, which Rust does not mirror."""

    class IntSubclass(int):
        pass

    class StrSubclass(str):
        pass

    assert not rust_renders_identically({"a": IntSubclass(1)})
    assert not rust_renders_identically({"a": StrSubclass("x")})


@pytest.mark.parametrize(
    "key",
    ["ns1:node1", "名前", "trailing ", "", "@attrs", "flat@flat", 1, None],
)
def test_gate_rejects_keys_python_resolves_with_a_parser(key: Any) -> None:
    """Keys whose element name Python derives from a parser stay on Python."""
    assert not rust_renders_identically({key: "value"})


@pytest.mark.parametrize(
    "key",
    ["name", "_x", "a-b", "a.b", "xmlfoo", "XML", "123", "my key", " leading", "a&b"],
)
def test_gate_admits_keys_both_backends_name_identically(key: str) -> None:
    """ASCII, colon-free keys resolve the same way in both implementations."""
    assert rust_renders_identically({key: "value"})


def test_gate_walks_nested_containers() -> None:
    """A single unsupported value anywhere in the payload disqualifies the request."""
    assert rust_renders_identically({"a": [{"b": (1, 2)}, None]})
    assert not rust_renders_identically({"a": [{"b": [Decimal("1")]}]})
    assert not rust_renders_identically([[{"deep": {"deeper": Decimal("1")}}]])


def test_root_gate_only_applies_when_a_root_is_emitted() -> None:
    """A rootless document never names the root, so its value cannot matter."""
    assert rust_renders_root_identically(True, "root")
    assert not rust_renders_root_identically(True, "not a name")
    assert not rust_renders_root_identically(True, 5)
    assert rust_renders_root_identically(False, "not a name")


# --------------------------------------------------------------------------- parity


def _assert_identical(data: Any, **kwargs: Any) -> None:
    assert rust_dicttoxml(data, **kwargs) == py_dicttoxml.dicttoxml(data, **kwargs)


# @lat: [[tests#Rust backend parity#Admitted payloads render identically]]
@requires_rust
@pytest.mark.parametrize("combo", OPTION_MATRIX)
def test_regression_payloads_render_identically(combo: tuple[bool, ...]) -> None:
    """Every divergence found by differential testing, pinned across the option matrix."""
    payloads: list[Any] = [
        # CDATA reached only strings; Python wraps every non-bool, non-null scalar.
        {"n": 1, "f": 1.5, "s": "x", "b": True, "z": None},
        {"big": 2**70},
        # Nested lists were wrapped instead of following Python's flattening rules.
        {"a": [[1, 2], [3]]},
        [[1, 2], None],
        [[], {}],
        # Booleans and nulls keep the item tag even when scalars borrow the parent.
        {"a": [True, None, 1]},
        # type="dict" was dropped for unwrapped list members under list_headers.
        {"a": [{"b": 2}, 1]},
        {"a": [{}]},
        # Names beginning with "xml" were silently renamed to <key name="...">.
        {"xmlfoo": 1, "XML": 2, "xml": 3},
        {"123": "v", "my key": "v", "a&b": "v", "-bad": "v"},
    ]
    for data in payloads:
        if not rust_renders_identically(data):
            continue
        _assert_identical(data, **_options(combo))


_KEYS = ["name", "a b", "123", "x-y", "xmlfoo", "_ok", "A.B", "9lives", "XmL", "a\tb"]
_SCALARS: list[Any] = [
    None,
    True,
    False,
    0,
    1,
    -5,
    2**63,
    2**70,
    1.0,
    0.5,
    -0.0,
    "plain",
    "",
    "a&b<c>d\"e'f",
    "]]>",
    "líne",
    "tab\there",
    "🎉",
]


def _random_value(rng: random.Random, depth: int = 0) -> Any:
    roll = rng.random()
    if depth >= 3 or roll < 0.45:
        return rng.choice(_SCALARS)
    if roll < 0.75:
        return {
            rng.choice(_KEYS): _random_value(rng, depth + 1)
            for _ in range(rng.randint(0, 3))
        }
    return [_random_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]


def _random_payload(rng: random.Random) -> Any:
    if rng.random() < 0.6:
        return {
            rng.choice(_KEYS): _random_value(rng, 1) for _ in range(rng.randint(1, 4))
        }
    return [_random_value(rng, 1) for _ in range(rng.randint(0, 4))]


# @lat: [[tests#Rust backend parity#Admitted payloads render identically]]
@requires_rust
def test_randomized_payloads_render_identically() -> None:
    """Differential check over the option matrix with a fixed seed for reproducibility."""
    rng = random.Random(20260823)
    compared = 0
    for _ in range(60):
        data = _random_payload(rng)
        if not rust_renders_identically(data):
            continue
        for combo in OPTION_MATRIX:
            options = _options(combo)
            assert rust_dicttoxml(data, **options) == py_dicttoxml.dicttoxml(
                data, **options
            ), f"backend divergence for {data!r} with {options!r}"
            compared += 1
    assert compared > 500, f"differential coverage collapsed to {compared} comparisons"


# @lat: [[tests#Rust backend parity#Native and Python gates agree]]
@requires_rust
def test_native_and_python_gates_agree() -> None:
    """The native gate is an optimization, so it must decide exactly as Python does.

    A disagreement in either direction is a correctness bug: admitting too much routes a
    payload the writer cannot reproduce, and admitting too little silently drops the fast
    path.
    """
    from json2xml.dicttoxml_fast import _rust_payload_is_supported

    assert _rust_payload_is_supported is not None

    fixtures: list[Any] = [
        {},
        [],
        {"a": 1},
        [1, 2],
        {"a": [{"b": [None, True, 1.5, "s"]}]},
        {"a": (1, 2)},
        {"a": Decimal("1")},
        {"a": datetime.date(2026, 1, 1)},
        {"a": {1, 2}},
        {"ns:x": 1},
        {"名前": 1},
        {"trail ": 1},
        {"": 1},
        {"@attrs": 1},
        {"x@flat": 1},
        {1: "int key"},
        {None: "none key"},
        [[[{"deep": Decimal("1")}]]],
        {"a": [1, [2, [3, {"b": (4,)}]]]},
    ]
    for data in fixtures:
        assert _rust_payload_is_supported(data) == rust_renders_identically(data), data

    rng = random.Random(4242)
    for _ in range(400):
        data = _random_payload(rng)
        assert _rust_payload_is_supported(data) == rust_renders_identically(data), data
