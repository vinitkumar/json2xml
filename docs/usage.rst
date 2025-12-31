=====
Usage
=====

Basic Usage
-----------

The json2xml library provides three main ways to read JSON data:

* From a JSON file using ``readfromjson``
* From a URL using ``readfromurl``
* From a string using ``readfromstring``

Here's how to use each method:

.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromurl, readfromstring, readfromjson

    # Convert JSON data from a URL to XML
    data = readfromurl("https://api.example.com/data")
    print(json2xml.Json2xml(data).to_xml())

    # Convert a JSON string to XML
    data = readfromstring(
        '{"login":"mojombo","id":1,"avatar_url":"https://example.com/avatar.png"}'
    )
    print(json2xml.Json2xml(data).to_xml())

    # Convert a JSON file to XML
    data = readfromjson("examples/licht.json")
    print(json2xml.Json2xml(data).to_xml())


Constructor Parameters
----------------------

The ``Json2xml`` class accepts the following parameters:

* ``data`` - The JSON data (dict or list) to convert
* ``wrapper`` (default: ``"all"``) - Custom root element name
* ``root`` (default: ``True``) - Whether to include the XML declaration and root element
* ``pretty`` (default: ``True``) - Whether to pretty-print the XML output
* ``attr_type`` (default: ``True``) - Whether to include type attributes on elements
* ``item_wrap`` (default: ``True``) - Whether to wrap list items in ``<item>`` tags
* ``xpath_format`` (default: ``False``) - Whether to use XPath 3.1 compliant output format


Custom Wrappers and Indentation
-------------------------------

By default, a wrapper ``all`` and ``pretty=True`` is set. You can customize these:

.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromstring

    data = readfromstring(
        '{"login":"mojombo","id":1,"avatar_url":"https://example.com/avatar.png"}'
    )
    print(json2xml.Json2xml(data, wrapper="all", pretty=True).to_xml())


Outputs:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <all>
      <login type="str">mojombo</login>
      <id type="int">1</id>
      <avatar_url type="str">https://example.com/avatar.png</avatar_url>
    </all>


Omit List Item Wrapping
-----------------------

By default, items in an array are wrapped in ``<item></item>`` tags.

Given this JSON input:

.. code-block:: json

    {
      "my_items": [
        { "my_item": { "id": 1 } },
        { "my_item": { "id": 2 } }
      ],
      "my_str_items": ["a", "b"]
    }

Default output (``item_wrap=True``):

.. code-block:: xml

    <?xml version="1.0" ?>
    <all>
      <my_items type="list">
        <item type="dict">
          <my_item type="dict">
            <id type="int">1</id>
          </my_item>
        </item>
        <item type="dict">
          <my_item type="dict">
            <id type="int">2</id>
          </my_item>
        </item>
      </my_items>
      <my_str_items type="list">
        <item type="str">a</item>
        <item type="str">b</item>
      </my_str_items>
    </all>

To disable item wrapping:

.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromstring

    data = readfromstring('{"my_items":[{"my_item":{"id":1}},{"my_item":{"id":2}}],"my_str_items":["a","b"]}')
    print(json2xml.Json2xml(data, item_wrap=False).to_xml())


Output with ``item_wrap=False``:

.. code-block:: xml

    <?xml version="1.0" ?>
    <all>
      <my_items type="list">
        <my_item type="dict">
          <id type="int">1</id>
        </my_item>
        <my_item type="dict">
          <id type="int">2</id>
        </my_item>
      </my_items>
      <my_str_items type="str">a</my_str_items>
      <my_str_items type="str">b</my_str_items>
    </all>


Disabling Type Attributes
-------------------------

You can disable the type attributes on elements:

.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromstring

    data = readfromstring(
        '{"login":"mojombo","id":1,"avatar_url":"https://example.com/avatar.png"}'
    )
    print(json2xml.Json2xml(data, wrapper="all", pretty=True, attr_type=False).to_xml())


Outputs:

.. code-block:: xml

    <?xml version="1.0" ?>
    <all>
      <login>mojombo</login>
      <id>1</id>
      <avatar_url>https://example.com/avatar.png</avatar_url>
    </all>


XPath 3.1 Compliance
--------------------

The library supports XPath 3.1 ``json-to-xml`` function specification from
`W3C <https://www.w3.org/TR/xpath-functions-31/#func-json-to-xml>`_.

When ``xpath_format=True``, the XML output uses standardized type-based element names
(``map``, ``array``, ``string``, ``number``, ``boolean``, ``null``) with ``key`` attributes:

.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromstring

    data = readfromstring(
        '{"login":"mojombo","id":1,"avatar_url":"https://example.com/avatar.png"}'
    )
    print(json2xml.Json2xml(data, xpath_format=True).to_xml())


Outputs:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8" ?>
    <map xmlns="http://www.w3.org/2005/xpath-functions">
      <string key="login">mojombo</string>
      <number key="id">1</number>
      <string key="avatar_url">https://example.com/avatar.png</string>
    </map>


Error Handling
--------------

The library provides custom exceptions for error handling:

* ``JSONReadError`` - Raised when there's an error reading a JSON file
* ``URLReadError`` - Raised when there's an error fetching data from a URL
* ``StringReadError`` - Raised when there's an error parsing a JSON string
* ``InvalidDataError`` - Raised when the data cannot be converted to valid XML

Example:

.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromstring, StringReadError

    try:
        data = readfromstring("invalid json")
    except StringReadError as e:
        print(f"Error: {e}")
