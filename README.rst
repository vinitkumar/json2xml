========
json2xml
========


.. image:: https://img.shields.io/pypi/v/json2xml.svg
        :target: https://pypi.python.org/pypi/json2xml

.. image:: https://img.shields.io/travis/vinitkumar/json2xml.svg
        :target: https://travis-ci.org/vinitkumar/json2xml

.. image:: https://readthedocs.org/projects/json2xml/badge/?version=latest
        :target: https://json2xml.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/vinitkumar/json2xml/shield.svg
     :target: https://pyup.io/repos/github/vinitkumar/json2xml/
     :alt: Updates

.. image:: https://coveralls.io/repos/github/vinitkumar/json2xml/badge.svg?branch=master
     :target: https://coveralls.io/github/vinitkumar/json2xml?branch=master




Simple Python Library to convert JSON to XML


* Free software: Apache Software License 2.0
* Documentation: https://json2xml.readthedocs.io.


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

    from json2xml import json2xml, readfromurl, readfromstring, readfromjson

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


** Custom Wrappers and indent***

By defualt, a wrapper `all` and indent `2` is set. However, you can change this easily in your code like this:

.. code-block:: python

    from json2xml import json2xml, readfromurl, readfromstring, readfromjson
    data = readfromstring(
        '{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}'
    )
    print(json2xml.Json2xml(data, wrapper="custom", indent=8).to_xml())


Outputs this:

.. code-block:: xml

    <custom>
        <avatar_url>https://avatars0.githubusercontent.com/u/1?v=4</avatar_url>
        <id>1</id>
        <login>mojombo</login>
    </custom>

The methods are simple and easy to use and there are also checks inside of code to exit cleanly
in case any of the input(file, string or API URL) returns invalid JSON.

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
