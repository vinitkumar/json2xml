from __future__ import annotations

import pytest

from json2xml.backend_selector import BackendSelector
from json2xml.dicttoxml import SerializerConfig, default_item_func


class _NeverBackend:
    name = "never"

    def can_handle(self, request: SerializerConfig) -> bool:
        return False

    def render(self, request: SerializerConfig) -> bytes:
        raise AssertionError("render should not be called")


# @lat: [[tests#Conversion behavior#Backend selector fails loudly with no compatible backend]]
def test_backend_selector_raises_when_no_backend_can_handle_request() -> None:
    request = SerializerConfig(
        obj={"name": "Ada"},
        root=True,
        custom_root="root",
        ids=None,
        attr_type=True,
        item_wrap=True,
        item_func=default_item_func,
        cdata=False,
        xml_namespaces=None,
        list_headers=False,
        xpath_format=False,
        max_output_bytes=None,
    )

    selector = BackendSelector(_NeverBackend())

    with pytest.raises(RuntimeError, match="No XML backend can handle"):
        selector.render(request)
