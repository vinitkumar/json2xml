# -*- coding: utf-8 -*-
from typing import Optional, Any
from xml.dom.minidom import parseString
import dicttoxml


class Json2xml:
    def __init__(
            self, data: str,
            wrapper: str = "all",
            pretty: bool = True,
            attr_type: bool = True
    ):
        self.data = data
        self.pretty = pretty
        self.wrapper = wrapper
        self.attr_type = attr_type

    def to_xml(self) -> Optional[Any]:
        """
        Convert to xml using dicttoxml.dicttoxml and then pretty print it.
        """
        if self.data:
            xml_data = dicttoxml.dicttoxml(self.data, custom_root=self.wrapper, attr_type=self.attr_type)
            if self.pretty:
                return parseString(xml_data).toprettyxml()
            return xml_data
        return None
