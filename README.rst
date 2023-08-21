========
json2xml
========

.. image:: https://badge.fury.io/py/json2xml.svg
.. image:: https://static.pepy.tech/personalized-badge/json2xml?period=total&units=international_system&left_color=blue&right_color=orange&left_text=Downloads
        :target: https://pepy.tech/project/json2xml

.. image:: https://github.com/vinitkumar/json2xml/actions/workflows/pythonpackage.yml/badge.svg
.. image:: https://img.shields.io/pypi/pyversions/json2xml.svg
.. image:: https://readthedocs.org/projects/json2xml/badge/?version=latest
        :target: https://json2xml.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status
.. image:: https://codecov.io/gh/vinitkumar/json2xml/branch/master/graph/badge.svg?token=Yt2h55eTL2
      :target: https://codecov.io/gh/vinitkumar/json2xml

json2xml is a Python library that allows you to convert JSON data into XML format. It's simple, efficient, and easy to use.

Documentation: https://json2xml.readthedocs.io.

The library was initially dependent on the `dict2xml` project, but it has now been integrated into json2xml itself. This has led to cleaner code, the addition of types and tests, and overall improved performance.

Features
^^^^^^^^

json2xml supports the following features:

* Conversion from a `json` string to XML
* Conversion from a `json` file to XML
* Conversion from an API that emits `json` data to XML

Usage
^^^^^

You can use the json2xml library in the following ways:


.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromurl, readfromstring, readfromjson

    # Convert JSON data from a URL to XML
    data = readfromurl("https://api.publicapis.org/entries")
    print(json2xml.Json2xml(data).to_xml())

    # Convert a JSON string to XML
    data = readfromstring(
        '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
    )
    print(json2xml.Json2xml(data).to_xml())

    # Convert a JSON file to XML
    data = readfromjson("examples/licht.json")
    print(json2xml.Json2xml(data).to_xml())


Custom Wrappers and Indentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, a wrapper `all` and pretty `True` is set. However, you can easily change this in your code like this:

.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromurl, readfromstring, readfromjson

    data = readfromstring(
        '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
    )
    print(json2xml.Json2xml(data, wrapper="all", pretty=True).to_xml())


Outputs this:

.. code-block:: xml

    <?xml version="1.0" ?>
    <all>
      <login type="str">mojombo</login>
      <id type="int">1</id>
      <avatar_url type="str">https://avatars0.githubusercontent.com/u/1?v=4</avatar_url>
    </all>

Omit List item
^^^^^^^^^^^^^^

Assume the following json input

.. code-block:: json

    {
      "my_items": [
        { "my_item": { "id": 1 } },
        { "my_item": { "id": 2 } }
      ],
      "my_str_items": ["a", "b"]
    }

By default, items in an array are wrapped in <item></item>.

Default output:

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
      <empty type="list"/>
    </all>

However, you can change this behavior using the item_wrap property like this:

.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromurl, readfromstring, readfromjson

    data = readfromstring('{"my_items":[{"my_item":{"id":1} },{"my_item":{"id":2} }],"my_str_items":["a","b"]}')
    print(json2xml.Json2xml(data, item_wrap=False).to_xml())

Outputs this:

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

Optional Attribute Type Support
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also specify if the output XML needs to have type specified or not. Here is the usage:

 .. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromurl, readfromstring, readfromjson

    data = readfromstring(
        '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
    )
    print(json2xml.Json2xml(data, wrapper="all", pretty=True, attr_type=False).to_xml())


Outputs this:

.. code-block:: xml

    <?xml version="1.0" ?>
    <all>
      <login>mojombo</login>
      <id>1</id>
      <avatar_url>https://avatars0.githubusercontent.com/u/1?v=4</avatar_url>
    </all>


The methods are simple and easy to use and there are also checks inside of code to exit cleanly
in case any of the input(file, string or API URL) returns invalid JSON.

How to run tests
^^^^^^^^^^^^^^^^

This is provided by pytest, which is straight forward.

 .. code-block:: console

    virtualenv venv -p $(which python3.9)
    pip install -r requirements-dev.txt
    python setup.py install
    pytest -vv


Help and Support to maintain this project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- You can sponsor my work for this plugin here: https://github.com/sponsors/vinitkumar/

