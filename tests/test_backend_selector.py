from __future__ import annotations

import pytest

from json2xml.backend_selector import BackendSelector, ConversionRequest, has_special_keys


class _NeverBackend:
    name = "never"

    def can_handle(self, request: ConversionRequest) -> bool:
        return False

    def render(self, request: ConversionRequest) -> bytes:
        raise AssertionError("render should not be called")


# @lat: [[tests#Conversion behavior#Backend selector detects Python-only payload markers]]
def test_has_special_keys_detects_nested_python_only_markers() -> None:
    assert has_special_keys({"items": [{"record": {"@attrs": {"id": "7"}}}]}) is True
    assert has_special_keys({"items": [{"record@flat": [1, 2, 3]}]}) is True
    assert has_special_keys({"items": [{"record": {"name": "Ada"}}]}) is False


# @lat: [[tests#Conversion behavior#Backend selector fails loudly with no compatible backend]]
def test_backend_selector_raises_when_no_backend_can_handle_request() -> None:
    request = ConversionRequest(
        obj={"name": "Ada"},
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
    )

    selector = BackendSelector(_NeverBackend())

    with pytest.raises(RuntimeError, match="No XML backend can handle"):
        selector.render(request)
