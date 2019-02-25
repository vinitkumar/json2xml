# -*- coding: utf-8 -*-
import dict2xml


class Json2xml(object):
    def __init__(self, data: str, wrapper: str = "all", indent: int = 4) -> None:
        self.data = data
        self.indent = indent
        self.wrapper = wrapper

    def to_xml(self):
        if self.data:
            return dict2xml.dict2xml(self.data, self.wrapper, indent=self.indent * " ")
