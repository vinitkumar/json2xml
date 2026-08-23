from collections.abc import Mapping, Sequence
from typing import Any

from . import dicttoxml_fast as dicttoxml
from .types import JSONValue
from .utils import InvalidDataError

DEFAULT_MAX_DEPTH = 100
DEFAULT_MAX_ITEMS = 100_000
DEFAULT_MAX_OUTPUT_BYTES = 10 * 1024 * 1024
PRETTY_INDENT = "  "


def _positive_limit(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _validate_conversion_budget(data: JSONValue, max_depth: int, max_items: int) -> None:
    """Reject inputs whose nesting depth or item count exceeds a limit."""
    stack: list[tuple[Any, int]] = [(data, 0)]
    items = 0
    while stack:
        value, depth = stack.pop()
        items += 1
        if items > max_items:
            raise InvalidDataError("JSON item limit exceeded")
        if depth > max_depth:
            raise InvalidDataError("JSON nesting depth limit exceeded")
        if isinstance(value, Mapping):
            for child in value.values():
                stack.append((child, depth + 1))
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            stack.extend((child, depth + 1) for child in value)


# @lat: [[architecture#Core pipeline]]
class Json2xml:
    """Configure conversion of a decoded JSON value to XML.

    :param data: The decoded JSON value. ``None`` represents absent input; other falsy values
        are serialized.
    :param wrapper: The root element name used when ``root`` is enabled.
    :param root: Include the XML declaration and root element.
    :param pretty: Indent serialized XML as it is generated, returning text instead of bytes.
    :param attr_type: Add each value's JSON type as an XML attribute.
    :param item_wrap: Wrap list members in ``<item>`` elements.
    :param xpath_format: Emit the W3C XPath 3.1 JSON-to-XML representation.
    :param cdata: Wrap string values in CDATA sections.
    :param list_headers: Repeat the parent element for nested dictionary items in lists.
    :param max_depth: Maximum JSON container nesting depth.
    :param max_items: Maximum total number of JSON values and containers.
    :param max_output_bytes: Maximum compact or pretty UTF-8 XML size.
    """

    def __init__(
        self,
        data: JSONValue = None,
        wrapper: str = "all",
        root: bool = True,
        pretty: bool = False,
        attr_type: bool = True,
        item_wrap: bool = True,
        xpath_format: bool = False,
        cdata: bool = False,
        list_headers: bool = False,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_items: int = DEFAULT_MAX_ITEMS,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    ):
        self.data = data
        self.pretty = pretty
        self.wrapper = wrapper
        self.attr_type = attr_type
        self.root = root
        self.item_wrap = item_wrap
        self.xpath_format = xpath_format
        self.cdata = cdata
        self.list_headers = list_headers
        self.max_depth = _positive_limit("max_depth", max_depth)
        self.max_items = _positive_limit("max_items", max_items)
        self.max_output_bytes = _positive_limit("max_output_bytes", max_output_bytes)

    # @lat: [[behavior#Conversion output]]
    # @lat: [[behavior#Invalid XML payloads]]
    def to_xml(self) -> bytes | str | None:
        """Serialize the configured JSON value.

        :return: Pretty-printed XML text when ``pretty`` is enabled, UTF-8 encoded XML bytes
            otherwise, or ``None`` when the configured data is ``None``.
        :raises InvalidDataError: If a conversion limit is exceeded or serialization rejects
            the data.
        """
        if self.data is not None:
            _validate_conversion_budget(self.data, self.max_depth, self.max_items)
            try:
                xml_data = dicttoxml.dicttoxml(
                    self.data,
                    root=self.root,
                    custom_root=self.wrapper,
                    attr_type=self.attr_type,
                    item_wrap=self.item_wrap,
                    xpath_format=self.xpath_format,
                    cdata=self.cdata,
                    list_headers=self.list_headers,
                    max_output_bytes=self.max_output_bytes,
                    indent=PRETTY_INDENT if self.pretty else None,
                )
            except ValueError as error:
                raise InvalidDataError(str(error)) from error
            if len(xml_data) > self.max_output_bytes:
                raise InvalidDataError("XML output size limit exceeded")
            if self.pretty:
                return xml_data.decode("utf-8")
            return xml_data
        return None
