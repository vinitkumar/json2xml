from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


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


class BackendAdapter(Protocol):
    """Small adapter seam for conversion backends."""

    name: str

    def can_handle(self, request: ConversionRequest) -> bool:
        raise NotImplementedError

    def render(self, request: ConversionRequest) -> bytes:
        raise NotImplementedError


class BackendSelector:
    """Pick the first backend that can preserve request semantics."""

    def __init__(self, *backends: BackendAdapter) -> None:
        self._backends = backends

    def render(self, request: ConversionRequest) -> bytes:
        for backend in self._backends:
            if backend.can_handle(request):
                return backend.render(request)
        raise RuntimeError("No XML backend can handle the requested conversion")


def has_special_keys(obj: Any) -> bool:
    """Return True when the payload uses Python-only special key semantics."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and (key.startswith("@") or key.endswith("@flat")):
                return True
            if has_special_keys(value):
                return True
        return False

    if isinstance(obj, list):
        for item in obj:
            if has_special_keys(item):
                return True

    return False
