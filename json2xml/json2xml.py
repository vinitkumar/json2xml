# -*- coding: utf-8 -*-
from xml.dom.minidom import parseString
from json2xml import dicttoxml


class Json2xml:
    def __init__(
            self, data: str,
            wrapper: str = "all",
            root: bool = True,
            pretty: bool = True,
            attr_type: bool = True
    ):
        self.data = data
        self.pretty = pretty
        self.wrapper = wrapper
        self.attr_type = attr_type
        self.root = root

    def to_xml(self):
        """
        Convert to xml using dicttoxml.dicttoxml and then pretty print it.
        """
        if self.data:
            # xml_data = dicttoxml.dicttoxml(self.data, root=self.root, custom_root=self.wrapper, attr_type=self.attr_type)
            xml_data = dicttoxml.dicttoxml(self.data, custom_root=self.wrapper, attr_type=self.attr_type)
            print(xml_data)
            if self.pretty:
                return parseString(xml_data).toprettyxml()
            return xml_data
        return None
