.. highlight:: shell

============
Installation
============


Stable release
--------------

To install json2xml, run this command in your terminal:

.. code-block:: console

    $ pip install json2xml

This is the preferred method to install json2xml, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


Using uv (recommended)
----------------------

`uv`_ is a fast Python package installer. You can install json2xml using:

.. code-block:: console

    $ uv pip install json2xml

.. _uv: https://github.com/astral-sh/uv


From sources
------------

The sources for json2xml can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/vinitkumar/json2xml

Or download the `tarball`_:

.. code-block:: console

    $ curl -OL https://github.com/vinitkumar/json2xml/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ pip install .

Or for development (editable install):

.. code-block:: console

    $ pip install -e .


Development Setup
-----------------

For contributing to json2xml, set up a development environment:

.. code-block:: console

    # Create and activate virtual environment (using uv - recommended)
    $ uv venv
    $ source .venv/bin/activate  # On Windows: .venv\Scripts\activate

    # Install dependencies
    $ uv pip install -r requirements-dev.txt
    $ uv pip install -e .


Requirements
------------

json2xml requires Python 3.10 or later and depends on:

* ``defusedxml`` - For secure XML parsing
* ``urllib3`` - For fetching JSON from URLs


.. _Github repo: https://github.com/vinitkumar/json2xml
.. _tarball: https://github.com/vinitkumar/json2xml/tarball/master
