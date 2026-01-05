from pyexpat import ExpatError
from typing import Any

from defusedxml.minidom import parseString

from json2xml import dicttoxml

from .utils import InvalidDataError


class Json2xml:
    """
    Wrapper class to convert the data to xml
    """
    def __init__(
        self,
        data: dict[str, Any] | list[Any] | None = None,
        wrapper: str = "all",
        root: bool = True,
        pretty: bool = True,
        attr_type: bool = True,
        item_wrap: bool = True,
        xpath_format: bool = False,
    ):
        self.data = data
        self.pretty = pretty
        self.wrapper = wrapper
        self.attr_type = attr_type
        self.root = root
        self.item_wrap = item_wrap
        self.xpath_format = xpath_format

    def to_xml(self) -> str | bytes | None:
        """
        Convert to xml using dicttoxml.dicttoxml and then pretty print it.

        Returns:
            str: Pretty-printed XML string when pretty=True.
            bytes: Raw XML bytes when pretty=False.
            None: When data is empty or None.
        """
        if self.data:
            xml_data = dicttoxml.dicttoxml(
                self.data,
                root=self.root,
                custom_root=self.wrapper,
                attr_type=self.attr_type,
                item_wrap=self.item_wrap,
                xpath_format=self.xpath_format,
            )
            if self.pretty:
                try:
                    result = parseString(xml_data).toprettyxml(encoding="UTF-8").decode()
                except ExpatError:
                    raise InvalidDataError
                return result
            return xml_data
        return None
