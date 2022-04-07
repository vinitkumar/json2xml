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
.. image:: https://coveralls.io/repos/github/vinitkumar/json2xml/badge.svg?branch=master
     :target: https://coveralls.io/github/vinitkumar/json2xml?branch=master


Simple Python Library to convert JSON to XML

* Free software: Apache Software License 2.0
* Documentation: https://json2xml.readthedocs.io.


Update
------

The dict2xml project has been integrated in the project itself. This helped with cleaning up the code
and making improvements. Long term goal for the project is to reduce the number of dependencies.

Features
--------

It lets you convert json to xml in following ways:

* from a `json` string
* from a `json` file
* from an API that emits `json` data

Usage
-----

The usage is simple:


.. code-block:: python

    from json2xml import json2xml
    from json2xml.utils import readfromurl, readfromstring, readfromjson

    # get the xml from an URL that return json
    data = readfromurl("https://coderwall.com/vinitcool76.json")
    print(json2xml.Json2xml(data).to_xml())

    # get the xml from a json string
    data = readfromstring(
        '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
    )
    print(json2xml.Json2xml(data).to_xml())

    # get the data from an URL
    data = readfromjson("examples/licht.json")
    print(json2xml.Json2xml(data).to_xml())


Custom Wrappers and indent
--------------------------

By default, a wrapper `all` and pretty `True` is set. However, you can change this easily in your code like this:

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
--------------

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
-------------------------------

Now, we can also specify if the output xml needs to have type specified or not. Here is the usage:

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

Testing
-------

This is provided by pytest, which is straight forward.

 .. code-block:: bash

    python3.8 -mvenv venv
    source venv/bin/activate
    python setup.py test


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
