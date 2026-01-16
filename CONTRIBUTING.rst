.. highlight:: shell

============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/vinitkumar/json2xml/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

json2xml could always use more documentation, whether as part of the
official json2xml docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/vinitkumar/json2xml/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `json2xml` for local development.

1. Fork the `json2xml` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/json2xml.git

3. Install your local copy using uv (recommended) or pip::

    $ cd json2xml/
    $ uv venv
    $ source .venv/bin/activate
    $ uv pip install -r requirements-dev.txt
    $ uv pip install -e .

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass linting and the
   tests::

    $ make check-all  # Runs lint, typecheck, and tests
    
    # Or individually:
    $ ruff check json2xml tests
    $ mypy json2xml tests
    $ pytest tests/

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Rust Extension Development
--------------------------

The ``json2xml-rs`` Rust extension provides ~29x faster performance. If you want to contribute to the Rust extension:

**Prerequisites**

Install Rust and maturin::

    $ curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
    $ uv pip install maturin

**Building the Extension**

::

    # Build and install in development mode
    $ cd rust
    $ uv pip install -e .
    
    # Or using maturin directly
    $ maturin develop --release

**Running Rust Tests**

::

    $ pytest tests/test_rust_dicttoxml.py -v

**Running Benchmarks**

::

    $ python benchmark_rust.py

**Rust Code Structure**

The Rust code is located in ``rust/src/lib.rs`` and includes:

- ``escape_xml()`` - XML character escaping
- ``wrap_cdata()`` - CDATA section wrapping
- ``convert_dict()`` - Dictionary to XML conversion
- ``convert_list()`` - List to XML conversion
- ``dicttoxml()`` - Main entry point exposed to Python

When making changes to the Rust code:

1. Ensure all existing tests pass
2. Add tests for new functionality
3. Run ``cargo fmt`` to format Rust code
4. Run ``cargo clippy`` for linting
5. Verify Python compatibility tests pass

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for 3.7+, and for PyPy. Make sure that the tests pass for all supported Python versions.

Tips
----

To run a subset of tests::


    $ python -m unittest tests.test_json2xml

Deploying
---------

A reminder for the maintainers on how to deploy.
Make sure all your changes are committed (including an entry in HISTORY.rst).
Then run::

$ bumpversion patch # possible: major / minor / patch
$ git push
$ git push --tags

Travis will then deploy to PyPI if tests pass.
