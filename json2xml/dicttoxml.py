# coding: utf-8

"""
Converts a Python dictionary or other native data type into a valid XML string.
Supports item (`int`, `float`, `long`, `decimal.Decimal`, `bool`, `str`, `unicode`, `datetime`, `none` and other
        number-like objects) and collection (`list`, `set`, `tuple` and `dict`, as well as iterable and
                dict-like objects) data types, with arbitrary nesting for the collections.
        Items with a `datetime` type are converted to ISO format strings.
        Items with a `None` type become empty XML elements.
This module works with Python 3.7+
"""

import collections
import logging
import numbers
from random import randint
from defusedxml.minidom import parseString

from typing import Dict, Any

LOG = logging.getLogger("dicttoxml")


ids = []  # initialize list of unique ids


def make_id(element, start=100000, end=999999):
    """Returns a random integer"""
    return f"{element}_{randint(start, end)}"


def get_unique_id(element):
    """Returns a unique id for a given element"""
    this_id = make_id(element)
    dup = True
    while dup:
        if this_id not in ids:
            dup = False
            ids.append(this_id)
        else:
            this_id = make_id(element)
    return ids[-1]


def get_xml_type(val):
    """Returns the data type for the xml type attribute"""
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
    if type(val).__name__ == "NoneType":
        return "null"
    if isinstance(val, dict):
        return "dict"
    if isinstance(val, collections.abc.Iterable):
        return "list"
    return type(val).__name__


def escape_xml(s: str) -> str:
    if isinstance(s, str):
        s = str(s)  # avoid UnicodeDecodeError
        s = s.replace("&", "&amp;")
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&apos;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
    return s


def make_attrstring(attr):
    """Returns an attribute string in the form key="val" """
    attrstring = " ".join([f'{k}="{v}"' for k, v in attr.items()])
    return f'{" " if attrstring != "" else ""}{attrstring}'


def key_is_valid_xml(key):
    """Checks that a key is a valid XML name"""
    LOG.info(f'Inside key_is_valid_xml(). Testing "{str(key)}"')
    test_xml = f'<?xml version="1.0" encoding="UTF-8" ?><{key}>foo</{key}>'
    try:
        parseString(test_xml)
        return True
    except Exception:  # minidom does not implement exceptions well
        return False


def make_valid_xml_name(key, attr: Dict[str, Any]):
    """Tests an XML name and fixes it if invalid"""
    LOG.info(
        f'Inside make_valid_xml_name(). Testing key "{str(key)}" with attr "{str(attr)}"'
    )
    key = escape_xml(key)
    # nothing happens at escape_xml if attr is not a string, we don't
    # need to pass it to the method at all.
    # attr = escape_xml(attr)

    # pass through if key is already valid
    if key_is_valid_xml(key):
        return key, attr

    # prepend a lowercase n if the key is numeric
    if key.isdigit():
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


def wrap_cdata(s: str) -> str:
    """Wraps a string into CDATA sections"""
    s = str(s).replace("]]>", "]]]]><![CDATA[>")
    return "<![CDATA[" + s + "]]>"


def default_item_func(parent):
    return "item"


def convert(obj, ids, attr_type, item_func, cdata, item_wrap, parent="root"):
    """Routes the elements of an object to the right function to convert them
    based on their data type"""
    LOG.info(f'Inside convert(). type(obj)="{type(obj).__name__}"')
    # avoid cpu consuming object serialization => extra if
    if LOG.getEffectiveLevel() <= logging.DEBUG: LOG.debug(f'  obj="{str(obj)}"')

    item_name = item_func(parent)

    # since bool is also a subtype of number.Number and int, the check for bool
    # never comes and hence we get wrong value for the xml type bool
    # here, we just change order and check for bool first, because no other
    # type other than bool can be true for bool check
    if isinstance(obj, bool):
        return convert_bool(item_name, obj, attr_type, cdata)

    if isinstance(obj, (numbers.Number, str)):
        return convert_kv(
            key=item_name, val=obj, attr_type=attr_type, attr={}, cdata=cdata
        )

    if hasattr(obj, "isoformat"):
        return convert_kv(
            key=item_name,
            val=obj.isoformat(),
            attr_type=attr_type,
            attr={},
            cdata=cdata,
        )

    if obj is None:
        return convert_none(item_name, "", attr_type, cdata)

    if isinstance(obj, dict):
        return convert_dict(obj, ids, parent, attr_type, item_func, cdata, item_wrap)

    if isinstance(obj, collections.abc.Iterable):
        return convert_list(obj, ids, parent, attr_type, item_func, cdata, item_wrap)

    raise TypeError(f"Unsupported data type: {obj} ({type(obj).__name__})")

def is_primitive_type(val):
    t = get_xml_type(val)
    return t in {'str', 'int', 'float', 'bool', 'number', 'null'}

def dict2xml_str(attr_type, attr, item, item_func, cdata, item_name, item_wrap):
    keys_str = ', '.join(key for key in item)
    LOG.info(f'Inside dict_item2xml_str: type(obj)="{type(item).__name__}", keys="{keys_str}"')
    # avoid cpu consuming object serialization => extra if
    if LOG.getEffectiveLevel() <= logging.DEBUG: LOG.debug(f'  item="{str(item)}"')

    if attr_type:
        attr["type"] = get_xml_type(item)
    attr = item.pop("@attrs", attr)  # update attr with custom @attr if exists
    rawitem = item["@val"] if "@val" in item else item
    subtree = rawitem if is_primitive_type(rawitem) else convert(rawitem, ids, attr_type, item_func, cdata, item_wrap, item_name) # we can not use convert_dict, because rawitem could be non-dict
    if item.get("@flat", False): return subtree
    attrstring = make_attrstring(attr)
    return f"<{item_name}{attrstring}>{subtree}</{item_name}>"

def list2xml_str(attr_type, attr, item, item_func, cdata, item_name, item_wrap):
    if attr_type:
        attr["type"] = get_xml_type(item)
    key_name = item_func(item_name)
    if item_name.endswith('@flat'): item_name = item_name[0:-5]
    subtree = convert_list(item, ids, item_name, attr_type, item_func, cdata, item_wrap)
    if key_name.endswith('@flat'): return subtree
    if len(item)>0 and is_primitive_type(item[0]) and not item_wrap: return subtree
    attrstring = make_attrstring(attr)
    return f"<{item_name}{attrstring}>{subtree}</{item_name}>"

def convert_dict(obj, ids, parent, attr_type, item_func, cdata, item_wrap):
    """Converts a dict into an XML string."""
    keys_str = ', '.join(key for key in obj)
    LOG.info(f'Inside convert_dict(): type(obj)="{type(obj).__name__}", keys="{keys_str}"')
    # avoid cpu consuming object serialization => extra if
    if LOG.getEffectiveLevel() <= logging.DEBUG: LOG.debug(f'  obj="{str(obj)}"')

    output = []
    addline = output.append

    for key, val in obj.items():
        LOG.info(f'Looping inside convert_dict(): key="{str(key)}", type(val)="{type(val).__name__}"')
        if LOG.getEffectiveLevel() <= logging.DEBUG: LOG.debug(f'  val="{str(val)}"')

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
            addline(dict2xml_str(attr_type, attr, val, item_func, cdata, key, item_wrap))

        elif isinstance(val, collections.abc.Iterable):
            addline(list2xml_str(attr_type, attr, val, item_func, cdata, key, item_wrap))

        elif not val:
            addline(convert_none(key, val, attr_type, attr, cdata))

        else:
            raise TypeError(f"Unsupported data type: {val} ({type(val).__name__})")

    return "".join(output)


def convert_list(items, ids, parent, attr_type, item_func, cdata, item_wrap):
    """Converts a list into an XML string."""
    LOG.info(f'Inside convert_list(): type(items)="{type(items).__name__}"')
    # avoid cpu consuming object serialization => extra if
    if LOG.getEffectiveLevel() <= logging.DEBUG: LOG.debug(f'  items="{str(items)}"')

    output = []
    addline = output.append

    item_name = item_func(parent)
    if item_name.endswith('@flat'): item_name = item_name[:-5]
    this_id = None
    if ids:
        this_id = get_unique_id(parent)

    for i, item in enumerate(items):
        LOG.info(f'Looping inside convert_list(): index="{str(i)}", type="{type(item).__name__}"')
        # avoid cpu consuming object serialization => extra if
        if LOG.getEffectiveLevel() <= logging.DEBUG: LOG.debug(f'  item="{str(item)}"')

        attr = {} if not ids else {"id": f"{this_id}_{i + 1}"}
        if isinstance(item, (numbers.Number, str)):
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

        elif isinstance(item, bool):
            addline(convert_bool(item_name, item, attr_type, attr, cdata))

        elif isinstance(item, dict):
            addline(dict2xml_str(attr_type, attr, item, item_func, cdata, item_name, item_wrap))

        elif isinstance(item, collections.abc.Iterable):
            addline(list2xml_str(attr_type, attr, item, item_func, cdata, item_name, item_wrap))

        elif item is None:
            addline(convert_none(item_name, None, attr_type, attr, cdata))

        else:
            raise TypeError(f"Unsupported data type: {item} ({type(item).__name__})")
    return "".join(output)


def convert_kv(key, val, attr_type, attr={}, cdata: bool = False):
    """Converts a number or string into an XML element"""
    LOG.info(
        f'Inside convert_kv(): key="{str(key)}", val="{str(val)}", type(val) is: "{type(val).__name__}"'
    )

    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr["type"] = get_xml_type(val)
    attrstring = make_attrstring(attr)
    return f"<{key}{attrstring}>{wrap_cdata(val) if cdata else escape_xml(val)}</{key}>"


def convert_bool(key, val, attr_type, attr={}, cdata=False):
    """Converts a boolean into an XML element"""
    LOG.info(
        f'Inside convert_bool(): key="{str(key)}", val="{str(val)}", type(val) is: "{type(val).__name__}"'
    )

    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr["type"] = get_xml_type(val)
    attrstring = make_attrstring(attr)
    return f"<{key}{attrstring}>{str(val).lower()}</{key}>"


def convert_none(key, val, attr_type, attr={}, cdata=False):
    """Converts a null value into an XML element"""
    LOG.info(f'Inside convert_none(): key="{str(key)}"')

    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr["type"] = get_xml_type(val)
    attrstring = make_attrstring(attr)
    return f"<{key}{attrstring}></{key}>"


def dicttoxml(
    obj,
    root: bool = True,
    custom_root="root",
    ids=False,
    attr_type=True,
    item_wrap=True,
    item_func=default_item_func,
    cdata=False,
    xml_namespaces={}
):
    """Converts a python object into XML.
    Arguments:
    - root specifies whether the output is wrapped in an XML root element
      Default is True
    - custom_root allows you to specify a custom root element.
      Default is 'root'
    - ids specifies whether elements get unique ids.
      Default is False
    - attr_type specifies whether elements get a data type attribute.
      Default is True
    - item_func specifies what function should generate the element name for
      items in a list.
      Default is 'item'
    - item_wrap specifies whether to nest items in array in <item/>
      Default is True
    - cdata specifies whether string values should be wrapped in CDATA sections.
      Default is False
    - xml_namespaces is a dictionary where key is xmlns prefix and value the urn,
      e.g. { 'flex': 'http://www.w3.org/flex/flexBase', 'xsl': "http://www.w3.org/1999/XSL/Transform"}
      will result in <root xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:flex="http://www.w3.org/flex/flexBase">...
      Default is {}

    Dictionaries-keys with special char '@' has special meaning:
    @attrs: This allows custom xml attributes. Sample {'@attr':{'a':'b'}, 'x':'y'} results in <root a="b"><x>y</x></root>
    @flat: If a key ends with @flat (or dict contains key '@flat'), encapsulating node is omitted. Similar to item_wrap parameter for lists.
    @val: @attrs required compelex dict type. If primitive type should be used, then @val is used as key. Sample {'@attr':{'a':'b'}, '@val':'y'} results in <root a="b">y</root>
          Esp. if item['x'] is primitive type, you can set: item['x'] = {'@val': item['x'], '@attrs':{'a':'b'}}
    """
    LOG.info(f'Inside dicttoxml(): type(obj) is: "{type(obj).__name__}"')
    # avoid cpu consuming object serialization (problem for large objects) => extra if
    if LOG.getEffectiveLevel() <= logging.DEBUG: LOG.debug(f'  obj="{str(obj)}"')

    output = []
    namespacestr = ''
    for prefix in xml_namespaces:
        ns = xml_namespaces[prefix]
        namespacestr += f' xmlns:{prefix}="{ns}"'
    if root:
        output.append('<?xml version="1.0" encoding="UTF-8" ?>')
        output_elem = convert(
            obj, ids, attr_type, item_func, cdata, item_wrap, parent=custom_root
        )
        output.append(f"<{custom_root}{namespacestr}>{output_elem}</{custom_root}>")
    else:
        output.append(
            convert(obj, ids, attr_type, item_func, cdata, item_wrap, parent="")
        )

    return "".join(output).encode("utf-8")
