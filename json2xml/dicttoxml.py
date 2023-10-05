from __future__ import annotations

import datetime
import logging
import numbers
from collections.abc import Callable, Sequence
from random import SystemRandom
from typing import Any, Dict, Union

from defusedxml.minidom import parseString

# Create a safe random number generator
safe_random = SystemRandom()

# Set up logging
LOG = logging.getLogger("dicttoxml")


def make_id(element: str, start: int = 100000, end: int = 999999) -> str:
    """
    Generate a random ID for a given element.

    Args:
        element (str): The element to generate an ID for.
        start (int, optional): The lower bound for the random number. Defaults to 100000.
        end (int, optional): The upper bound for the random number. Defaults to 999999.

    Returns:
        str: The generated ID.
    """
    return f"{element}_{safe_random.randint(start, end)}"


def get_unique_id(element: str) -> str:
    """
    Generate a unique ID for a given element.

    Args:
        element (str): The element to generate an ID for.

    Returns:
        str: The unique ID.
    """
    ids: list[str] = []  # initialize list of unique ids
    this_id = make_id(element)
    dup = True
    while dup:
        if this_id not in ids:
            dup = False
            ids.append(this_id)
        else:
            this_id = make_id(element)
    return ids[-1]


ELEMENT = Union[
    str,
    int,
    float,
    bool,
    numbers.Number,
    Sequence,
    datetime.datetime,
    datetime.date,
    None,
    Dict[str, Any],
]


def get_xml_type(val: ELEMENT) -> str:
    """
    Get the XML type of a given value.

    Args:
        val (ELEMENT): The value to get the type of.

    Returns:
        str: The XML type.
    """
    if val is not None:
        if type(val).__name__ in ("str", "unicode"):
            return "str"
        if type(val).__name__ in ("int", "long"):
            return "int"
        if type(val).__name__ == "float":
            return "float"
        if type(val).__name__ == "bool":
            return "bool"
        if isinstance(val, numbers.Number):
            return "number"
        if isinstance(val, dict):
            return "dict"
        if isinstance(val, Sequence):
            return "list"
    else:
        return "null"
    return type(val).__name__


def escape_xml(s: str | numbers.Number) -> str:
    """
    Escape a string for use in XML.

    Args:
        s (str | numbers.Number): The string to escape.

    Returns:
        str: The escaped string.
    """
    if isinstance(s, str):
        s = str(s)  # avoid UnicodeDecodeError
        s = s.replace("&", "&amp;")
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&apos;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
    return str(s)


def make_attrstring(attr: dict[str, Any]) -> str:
    """
    Create a string of XML attributes from a dictionary.

    Args:
        attr (dict[str, Any]): The dictionary of attributes.

    Returns:
        str: The string of XML attributes.
    """
    attrstring = " ".join([f'{k}="{v}"' for k, v in attr.items()])
    return f'{" " if attrstring != "" else ""}{attrstring}'


def key_is_valid_xml(key: str) -> bool:
    """
    Check if a key is a valid XML name.

    Args:
        key (str): The key to check.

    Returns:
        bool: True if the key is a valid XML name, False otherwise.
    """
    test_xml = f'<?xml version="1.0" encoding="UTF-8" ?><{key}>foo</{key}>'
    try:
        parseString(test_xml)
        return True
    except Exception:  # minidom does not implement exceptions well
        return False


def make_valid_xml_name(key: str, attr: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Tests an XML name and fixes it if invalid"""
    key = escape_xml(key)
    # nothing happens at escape_xml if attr is not a string, we don't
    # need to pass it to the method at all.
    # attr = escape_xml(attr)

    # pass through if key is already valid
    if key_is_valid_xml(key):
        return key, attr

    # prepend a lowercase n if the key is numeric
    if isinstance(key, int) or key.isdigit():
        return f"n{key}", attr

    # replace spaces with underscores if that fixes the problem
    if key_is_valid_xml(key.replace(" ", "_")):
        return key.replace(" ", "_"), attr

    # allow namespace prefixes + ignore @flat in key
    if key_is_valid_xml(key.replace(":", "").replace("@flat", "")):
        return key, attr

    # key is still invalid - move it into a name attribute
    attr["name"] = key
    key = "key"
    return key, attr


def wrap_cdata(s: str | numbers.Number) -> str:
    """Wraps a string into CDATA sections"""
    s = str(s).replace("]]>", "]]]]><![CDATA[>")
    return "<![CDATA[" + s + "]]>"


def default_item_func(parent: str) -> str:
    return "item"


def convert(
    obj: ELEMENT,
    ids: Any,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    parent: str = "root",
    list_headers: bool = False,
) -> str:
    """Routes the elements of an object to the right function to convert them
    based on their data type"""
    item_name = item_func(parent)
    # since bool is also a subtype of number.Number and int, the check for bool
    # never comes and hence we get wrong value for the xml type bool
    # here, we just change order and check for bool first, because no other
    # type other than bool can be true for bool check
    if isinstance(obj, bool):
        return convert_bool(key=item_name, val=obj, attr_type=attr_type, cdata=cdata)

    if isinstance(obj, numbers.Number):
        return convert_kv(
            key=item_name, val=obj, attr_type=attr_type, attr={}, cdata=cdata
        )

    if isinstance(obj, str):
        return convert_kv(
            key=item_name, val=obj, attr_type=attr_type, attr={}, cdata=cdata
        )

    if hasattr(obj, "isoformat") and isinstance(
        obj, (datetime.datetime, datetime.date)
    ):
        return convert_kv(
            key=item_name,
            val=obj.isoformat(),
            attr_type=attr_type,
            attr={},
            cdata=cdata,
        )

    if obj is None:
        return convert_none(key=item_name, attr_type=attr_type, cdata=cdata)

    if isinstance(obj, dict):
        return convert_dict(obj, ids, parent, attr_type, item_func, cdata, item_wrap, list_headers=list_headers)

    if isinstance(obj, Sequence):
        return convert_list(obj, ids, parent, attr_type, item_func, cdata, item_wrap, list_headers=list_headers)

    raise TypeError(f"Unsupported data type: {obj} ({type(obj).__name__})")


def is_primitive_type(val: Any) -> bool:
    t = get_xml_type(val)
    return t in {"str", "int", "float", "bool", "number", "null"}


def dict2xml_str(
    attr_type: bool,
    attr: dict[str, Any],
    item: dict[str, Any],
    item_func: Callable[[str], str],
    cdata: bool,
    item_name: str,
    item_wrap: bool,
    parentIsList: bool,
    parent: str = "",
    list_headers: bool = False,
) -> str:
    """
    parse dict2xml
    """
    ids: list[str] = []  # initialize list of unique ids
    ", ".join(str(key) for key in item)

    if attr_type:
        attr["type"] = get_xml_type(item)
    val_attr: dict[str, str] = item.pop("@attrs", attr)  # update attr with custom @attr if exists
    rawitem = item["@val"] if "@val" in item else item
    if is_primitive_type(rawitem):
        if isinstance(rawitem, str):
            subtree = escape_xml(rawitem)
        else:
            subtree = rawitem
    else:
        # we can not use convert_dict, because rawitem could be non-dict
        subtree = convert(
            rawitem, ids, attr_type, item_func, cdata, item_wrap, item_name, list_headers=list_headers
        )

    if parentIsList and list_headers:
        if len(val_attr) > 0 and not item_wrap:
            attrstring = make_attrstring(val_attr)
            return f"<{parent}{attrstring}>{subtree}</{parent}>"
        return f"<{parent}>{subtree}</{parent}>"
    elif item.get("@flat", False) or (parentIsList and not item_wrap):
        return subtree

    attrstring = make_attrstring(val_attr)

    return f"<{item_name}{attrstring}>{subtree}</{item_name}>"


def list2xml_str(
    attr_type: bool,
    attr: dict[str, Any],
    item: Sequence[Any],
    item_func: Callable[[str], str],
    cdata: bool,
    item_name: str,
    item_wrap: bool,
    list_headers: bool = False,
) -> str:
    ids: list[str] = []  # initialize list of unique ids
    if attr_type:
        attr["type"] = get_xml_type(item)
    flat = False
    if item_name.endswith("@flat"):
        item_name = item_name[0:-5]
        flat = True
    subtree = convert_list(
        items=item,
        ids=ids,
        parent=item_name,
        attr_type=attr_type,
        item_func=item_func,
        cdata=cdata,
        item_wrap=item_wrap,
        list_headers=list_headers
    )
    if flat or (len(item) > 0 and is_primitive_type(item[0]) and not item_wrap):
        return subtree
    elif list_headers:
        return subtree
    attrstring = make_attrstring(attr)
    return f"<{item_name}{attrstring}>{subtree}</{item_name}>"


def convert_dict(
    obj: dict[str, Any],
    ids: list[str],
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool = False
) -> str:
    """Converts a dict into an XML string."""
    output: list[str] = []
    addline = output.append

    for key, val in obj.items():
        attr = {} if not ids else {"id": f"{get_unique_id(parent)}"}

        key, attr = make_valid_xml_name(key, attr)

        # since bool is also a subtype of number.Number and int, the check for bool
        # never comes and hence we get wrong value for the xml type bool
        # here, we just change order and check for bool first, because no other
        # type other than bool can be true for bool check
        if isinstance(val, bool):
            addline(convert_bool(key, val, attr_type, attr, cdata))

        elif isinstance(val, (numbers.Number, str)):
            addline(
                convert_kv(
                    key=key, val=val, attr_type=attr_type, attr=attr, cdata=cdata
                )
            )

        elif hasattr(val, "isoformat"):  # datetime
            addline(
                convert_kv(
                    key=key,
                    val=val.isoformat(),
                    attr_type=attr_type,
                    attr=attr,
                    cdata=cdata,
                )
            )

        elif isinstance(val, dict):
            addline(
                dict2xml_str(
                    attr_type, attr, val, item_func, cdata, key, item_wrap,
                    False,
                    list_headers=list_headers
                )
            )

        elif isinstance(val, Sequence):
            addline(
                list2xml_str(
                    attr_type=attr_type,
                    attr=attr,
                    item=val,
                    item_func=item_func,
                    cdata=cdata,
                    item_name=key,
                    item_wrap=item_wrap,
                    list_headers=list_headers
                )
            )

        elif not val:
            addline(convert_none(key, attr_type, attr, cdata))

        else:
            raise TypeError(f"Unsupported data type: {val} ({type(val).__name__})")

    return "".join(output)


def convert_list(
    items: Sequence[Any],
    ids: list[str] | None,
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool = False,
) -> str:
    """Converts a list into an XML string."""
    output: list[str] = []
    addline = output.append

    item_name = item_func(parent)  # Is item_name still relevant if item_wrap is false
    if item_name.endswith("@flat"):
        item_name = item_name[:-5]
    this_id = None
    if ids:
        this_id = get_unique_id(parent)

    for i, item in enumerate(items):
        attr = {} if not ids else {"id": f"{this_id}_{i + 1}"}

        if isinstance(item, bool):
            addline(convert_bool(item_name, item, attr_type, attr, cdata))

        elif isinstance(item, (numbers.Number, str)):
            if item_wrap:
                addline(
                    convert_kv(
                        key=item_name,
                        val=item,
                        attr_type=attr_type,
                        attr=attr,
                        cdata=cdata,
                    )
                )
            else:
                addline(
                    convert_kv(
                        key=parent,
                        val=item,
                        attr_type=attr_type,
                        attr=attr,
                        cdata=cdata,
                    )
                )

        elif hasattr(item, "isoformat"):  # datetime
            addline(
                convert_kv(
                    key=item_name,
                    val=item.isoformat(),
                    attr_type=attr_type,
                    attr=attr,
                    cdata=cdata,
                )
            )

        elif isinstance(item, dict):
            addline(
                dict2xml_str(
                    attr_type=attr_type,
                    attr=attr,
                    item=item,
                    item_func=item_func,
                    cdata=cdata,
                    item_name=item_name,
                    item_wrap=item_wrap,
                    parentIsList=True,
                    parent=parent,
                    list_headers=list_headers
                )
            )

        elif isinstance(item, Sequence):
            addline(
                list2xml_str(
                    attr_type=attr_type,
                    attr=attr,
                    item=item,
                    item_func=item_func,
                    cdata=cdata,
                    item_name=item_name,
                    item_wrap=item_wrap,
                    list_headers=list_headers
                )
            )

        elif item is None:
            addline(convert_none(item_name, attr_type, attr, cdata))

        else:
            raise TypeError(f"Unsupported data type: {item} ({type(item).__name__})")
    return "".join(output)


def convert_kv(
    key: str,
    val: str | numbers.Number,
    attr_type: bool,
    attr: dict[str, Any] = {},
    cdata: bool = False,
) -> str:
    """Converts a number or string into an XML element"""
    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr["type"] = get_xml_type(val)
    attr_string = make_attrstring(attr)
    return f"<{key}{attr_string}>{wrap_cdata(val) if cdata else escape_xml(val)}</{key}>"


def convert_bool(
    key: str, val: bool, attr_type: bool, attr: dict[str, Any] = {}, cdata: bool = False
) -> str:
    """Converts a boolean into an XML element"""
    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr["type"] = get_xml_type(val)
    attr_string = make_attrstring(attr)
    return f"<{key}{attr_string}>{str(val).lower()}</{key}>"


def convert_none(
    key: str, attr_type: bool, attr: dict[str, Any] = {}, cdata: bool = False
) -> str:
    """Converts a null value into an XML element"""
    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr["type"] = get_xml_type(None)
    attr_string = make_attrstring(attr)
    return f"<{key}{attr_string}></{key}>"


def dicttoxml(
    obj: dict[str, Any],
    root: bool = True,
    custom_root: str = "root",
    ids: list[int] | None = None,
    attr_type: bool = True,
    item_wrap: bool = True,
    item_func: Callable[[str], str] = default_item_func,
    cdata: bool = False,
    xml_namespaces: dict[str, Any] = {},
    list_headers: bool = False
) -> bytes:
    """
    Converts a python object into XML.

    :param dict obj:
        dictionary

    :param bool root:
        Default is True
        specifies wheter the output is wrapped in an XML root element

    :param custom_root:
        Default is 'root'
        allows you to specify a custom root element.

    :param bool ids:
        Default is False
        specifies whether elements get unique ids.

    :param bool attr_type:
        Default is True
        specifies whether elements get a data type attribute.

    :param bool item_wrap:
        Default is True
        specifies whether to nest items in array in <item/> Example if True

        ..code-block:: python

            data = {'bike': ['blue', 'green']}

        .. code-block:: xml

            <bike>
            <item>blue</item>
            <item>green</item>
            </bike>

        Example if False

        ..code-block:: python

            data = {'bike': ['blue', 'green']}

        ..code-block:: xml

            <bike>blue</bike>
            <bike>green</bike>'

    :param item_func:
        items in a list. Default is 'item'
        specifies what function should generate the element name for

    :param bool cdata:
        Default is False
        specifies whether string values should be wrapped in CDATA sections.

    :param xml_namespaces:
        is a dictionary where key is xmlns prefix and value the urn, Default is {}. Example:

        .. code-block:: python

            { 'flex': 'http://www.w3.org/flex/flexBase', 'xsl': "http://www.w3.org/1999/XSL/Transform"}

        results in

        .. code-block:: xml

            <root xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:flex="http://www.w3.org/flex/flexBase">

    :param bool list_headers:
        Default is False
        Repeats the header for every element in a list. Example if True:

        .. code-block:: python

            "Bike": [
            {'frame_color': 'red'},
            {'frame_color': 'green'}
            ]}

        results in

        .. code-block:: xml

            <Bike><frame_color>red</frame_color></Bike>
            <Bike><frame_color>green</frame_color></Bike>

    Dictionaries-keys with special char '@' has special meaning:
    @attrs: This allows custom xml attributes:

    .. code-block:: python

        {'@attr':{'a':'b'}, 'x':'y'}

    results in

    .. code-block:: xml

        <root a="b"><x>y</x></root>

    @flat: If a key ends with @flat (or dict contains key '@flat'),
    encapsulating node is omitted. Similar to item_wrap.
    @val: @attrs requires complex dict type. If primitive type should be used, then @val is used as key.
    To add custom xml-attributes on a list {'list': [4, 5, 6]}, you do this:

    .. code-block:: python

        {'list': {'@attrs': {'a':'b','c':'d'}, '@val': [4, 5, 6]}

    which results in

    .. code-block:: xml

        <list a="b" c="d"><item>4</item><item>5</item><item>6</item></list>

    """
    output = []
    namespace_str = ""
    for prefix in xml_namespaces:
        if prefix == 'xsi':
            for schema_att in xml_namespaces[prefix]:
                if schema_att == 'schemaInstance':
                    ns = xml_namespaces[prefix]['schemaInstance']
                    namespace_str += f' xmlns:{prefix}="{ns}"'
                elif schema_att == 'schemaLocation':
                    ns = xml_namespaces[prefix][schema_att]
                    namespace_str += f' xsi:{schema_att}="{ns}"'

        elif prefix == 'xmlns':
            # xmns needs no prefix
            ns = xml_namespaces[prefix]
            namespace_str += f' xmlns="{ns}"'

        else:
            ns = xml_namespaces[prefix]
            namespace_str += f' xmlns:{prefix}="{ns}"'
    if root:
        output.append('<?xml version="1.0" encoding="UTF-8" ?>')
        output_elem = convert(
            obj, ids, attr_type, item_func, cdata, item_wrap, parent=custom_root, list_headers=list_headers
        )
        output.append(f"<{custom_root}{namespace_str}>{output_elem}</{custom_root}>")
    else:
        output.append(
            convert(obj, ids, attr_type, item_func, cdata, item_wrap, parent="", list_headers=list_headers)
        )

    return "".join(output).encode("utf-8")
