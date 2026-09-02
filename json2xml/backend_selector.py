from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

# Shared with the Python serializer deliberately: the root-name gate below is only
# correct while it uses the exact predicate Python's name resolver starts from.
from .dicttoxml import _is_fast_valid_xml_name


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    """Normalized conversion request shared across backend adapters."""

    obj: Any
    root: bool
    custom_root: str
    ids: list[int] | None
    attr_type: bool
    item_wrap: bool
    item_func: Any
    cdata: bool
    xml_namespaces: dict[str, Any] | None
    list_headers: bool
    xpath_format: bool
    max_output_bytes: int | None = None
    indent: str | None = None


class BackendAdapter(Protocol):
    """Small adapter seam for conversion backends."""

    @property
    def name(self) -> str:
        raise NotImplementedError  # pragma: no cover

    def can_handle(self, request: ConversionRequest) -> bool:
        raise NotImplementedError  # pragma: no cover

    def render(self, request: ConversionRequest) -> bytes:
        raise NotImplementedError  # pragma: no cover


class BackendSelector:
    """Pick the first backend that can preserve request semantics."""

    def __init__(self, *backends: BackendAdapter) -> None:
        self._backends = backends

    def render(self, request: ConversionRequest) -> bytes:
        for backend in self._backends:
            if backend.can_handle(request):
                return backend.render(request)
        raise RuntimeError("No XML backend can handle the requested conversion")


# Types the Rust backend renders byte-identically to the Python serializer. Subclasses are
# excluded on purpose: Python classifies them through its isinstance fallbacks, which the
# native writer does not reproduce. Tuples are excluded because Python applies its
# list-shape rules to them while the native writer only recognizes lists.
_RUST_SCALAR_TYPES = frozenset({str, bool, int, float, type(None)})


def _rust_renders_key_identically(key: Any) -> bool:
    """Return True when both backends derive the same element name for a key.

    Python resolves names its ASCII fast path rejects through a real XML parser, and the
    native backend cannot reproduce that verdict. For ASCII names without a colon the two
    agree by construction, because the XML Name production restricted to ASCII is exactly
    ``[A-Za-z_][A-Za-z0-9._-]*`` -- the fast path itself. The exclusions below are the cases
    where they can disagree: non-ASCII names, colon names, and names ending in whitespace,
    which the parser accepts only because the probe document tolerates trailing space before
    the tag close.
    """
    if type(key) is not str or not key:
        return False
    if key.startswith("@") or key.endswith("@flat"):
        return False
    return key.isascii() and ":" not in key and not key[-1].isspace()


def rust_renders_root_identically(root: bool, custom_root: Any) -> bool:
    """Return True when the root element name needs no parser-backed normalization.

    Python rewrites an unusable root name into ``<key name="...">``; the native backend
    rejects it outright. Keeping non-trivial root names on Python avoids both the mismatch
    and the spurious error.
    """
    if not root:
        return True
    return type(custom_root) is str and _is_fast_valid_xml_name(custom_root)


def rust_renders_identically(obj: Any) -> bool:
    """Return True when the whole payload stays inside the native backend's exact subset."""
    stack: list[Any] = [obj]
    while stack:
        value = stack.pop()
        value_type = type(value)
        if value_type in _RUST_SCALAR_TYPES:
            continue
        if value_type is dict:
            for key, child in value.items():
                if not _rust_renders_key_identically(key):
                    return False
                stack.append(child)
            continue
        if value_type is list:
            stack.extend(value)
            continue
        return False
    return True


def has_special_keys(obj: Any) -> bool:
    """Return True when the payload uses Python-only special key semantics."""
    if isinstance(obj, dict):
        return any(
            (isinstance(key, str) and (key.startswith("@") or key.endswith("@flat")))
            or has_special_keys(value)
            for key, value in obj.items()
        )

    if isinstance(obj, list):
        return any(has_special_keys(item) for item in obj)

    return False
