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
        data: dict[str, Any] | None = None,
        wrapper: str = "all",
        root: bool = True,
        pretty: bool = True,
        attr_type: bool = True,
        item_wrap: bool = True,
        parallel: bool = False,
        workers: int | None = None,
        chunk_size: int = 100,
    ):
        self.data = data
        self.pretty = pretty
        self.wrapper = wrapper
        self.attr_type = attr_type
        self.root = root
        self.item_wrap = item_wrap
        self.parallel = parallel
        self.workers = workers
        self.chunk_size = chunk_size

    def to_xml(self) -> Any | None:
        """
        Convert to xml using dicttoxml.dicttoxml and then pretty print it.
        """
        if self.data:
            xml_data = dicttoxml.dicttoxml(
                self.data,
                root=self.root,
                custom_root=self.wrapper,
                attr_type=self.attr_type,
                item_wrap=self.item_wrap,
                parallel=self.parallel,
                workers=self.workers,
                chunk_size=self.chunk_size,
            )
            if self.pretty:
                try:
                    result = parseString(xml_data).toprettyxml(encoding="UTF-8").decode()
                except ExpatError:
                    raise InvalidDataError
                return result
            return xml_data
        return None
