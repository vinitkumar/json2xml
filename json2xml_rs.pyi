from typing import Any

def dicttoxml(
    obj: Any,
    root: bool = True,
    custom_root: str = "root",
    attr_type: bool = True,
    item_wrap: bool = True,
    cdata: bool = False,
    list_headers: bool = False,
) -> bytes: ...
def escape_xml_py(s: str) -> str: ...
def wrap_cdata_py(s: str) -> str: ...
def payload_is_supported(
    obj: Any, max_depth: int | None = None, max_items: int | None = None
) -> bool: ...
