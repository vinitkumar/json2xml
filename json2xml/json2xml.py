from typing import Any

__lazy_modules__ = ["defusedxml.minidom", "pyexpat"]

from . import dicttoxml_fast as dicttoxml
from .types import JSONValue
from .utils import InvalidDataError


# @lat: [[architecture#Core pipeline]]
class Json2xml:
    """Configure conversion of a decoded JSON value to XML.

    :param data: The decoded JSON value. ``None`` represents absent input; other falsy values
        are serialized.
    :param wrapper: The root element name used when ``root`` is enabled.
    :param root: Include the XML declaration and root element.
    :param pretty: Reparse and indent the serialized XML, returning text instead of bytes.
    :param attr_type: Add each value's JSON type as an XML attribute.
    :param item_wrap: Wrap list members in ``<item>`` elements.
    :param xpath_format: Emit the W3C XPath 3.1 JSON-to-XML representation.
    :param cdata: Wrap string values in CDATA sections.
    :param list_headers: Repeat the parent element for nested dictionary items in lists.
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

    # @lat: [[behavior#Conversion output]]
    # @lat: [[behavior#Invalid XML payloads]]
    def to_xml(self) -> bytes | str | None:
        """Serialize the configured JSON value.

        :return: Pretty-printed XML text when ``pretty`` is enabled, UTF-8 encoded XML bytes
            otherwise, or ``None`` when the configured data is ``None``.
        :raises InvalidDataError: If serialization rejects the data or pretty-print parsing finds
            malformed XML.
        """
        if self.data is not None:
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
                )
            except ValueError as error:
                raise InvalidDataError from error
            if self.pretty:
                # Keep parser imports off the compact-output path, which returns serializer bytes directly.
                from pyexpat import ExpatError

                from defusedxml.minidom import parseString

                try:
                    result = parseString(xml_data).toprettyxml(encoding="UTF-8").decode()
                except ExpatError:
                    raise InvalidDataError
                return result
            return xml_data
        return None
