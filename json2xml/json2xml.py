# -*- coding: utf-8 -*-
import dicttoxml


class Json2xml(object):
    def __init__(self, data: str, wrapper: str = "all", indent: int = 4) -> None:
        self.data = data
        self.indent = indent
        self.wrapper = wrapper

    def to_xml(self):
        """
        dicttoxml.dicttoxml(
            obj,
            root=True,
            custom_root='root',
            ids=False,
            attr_type=True,
            item_func=<function default_item_func at 0x1031d4320>,
            cdata=False,
        )

        """
        if self.data:
            return dicttoxml.dicttoxml(self.data, custom_root=self.wrapper)
