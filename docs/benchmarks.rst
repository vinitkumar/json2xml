Benchmarks
==========

Comprehensive performance comparison between Python implementations and the Go version of json2xml.

Test Environment
----------------

* **Machine**: Apple Silicon (aarch64)
* **OS**: macOS
* **Date**: January 14, 2026

Implementations Tested
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Implementation
     - Version
     - Notes
   * - CPython
     - 3.14.2
     - Homebrew installation
   * - CPython
     - 3.15.0a4
     - Latest alpha via uv
   * - PyPy
     - 3.10.16
     - JIT-compiled Python
   * - Go
     - 1.0.0
     - json2xml-go

Test Data
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 50 30

   * - Size
     - Description
     - Bytes
   * - Small
     - Simple object ``{"name": "John", "age": 30, "city": "New York"}``
     - 47
   * - Medium
     - ``bigexample.json`` (patent data)
     - 2,598
   * - Large
     - 1,000 generated records with nested structures
     - 323,130
   * - Very Large
     - 5,000 generated records with nested structures
     - 1,619,991

Results
-------

Individual Test Results
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 20 15

   * - Test
     - CPython 3.14.2
     - CPython 3.15.0a4
     - PyPy 3.10.16
     - Go
   * - **Small JSON** (47 bytes)
     - 75.46ms
     - 55.74ms (1.4x faster)
     - 121.47ms (1.6x slower)
     - 3.69ms (20.4x faster)
   * - **Medium JSON** (2.6KB)
     - 73.87ms
     - 57.98ms (1.3x faster)
     - 125.73ms (1.7x slower)
     - 4.32ms (17.1x faster)
   * - **Large JSON** (323KB)
     - 419.67ms
     - 328.98ms (1.3x faster)
     - 517.51ms (1.2x slower)
     - 67.13ms (6.3x faster)
   * - **Very Large JSON** (1.6MB)
     - 2.09s
     - 1.86s (1.1x faster)
     - 1.42s (1.5x faster)
     - 287.58ms (7.3x faster)

Summary (Average Across All Tests)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Implementation
     - Avg Time
     - vs CPython 3.14.2
   * - **Go**
     - 90.68ms
     - **7.34x faster** 🚀
   * - **PyPy 3.10.16**
     - 545.58ms
     - **1.22x faster**
   * - **CPython 3.15.0a4**
     - 575.45ms
     - **1.16x faster**
   * - **CPython 3.14.2**
     - 665.23ms
     - baseline

Key Observations
----------------

1. Go is the Clear Winner
~~~~~~~~~~~~~~~~~~~~~~~~~

Go outperforms all Python implementations by a significant margin:

* **7.34x faster** than CPython 3.14.2 on average
* Up to **20x faster** for small inputs due to minimal startup overhead
* Consistent performance across all input sizes

2. CPython 3.15.0a4 Shows Promising Improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The latest Python alpha demonstrates consistent performance gains:

* **13-35% faster** than CPython 3.14.2 across all test sizes
* Improvements likely due to ongoing interpreter optimizations

3. PyPy Has Interesting Trade-offs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PyPy's JIT compiler creates a unique performance profile:

* **Slower for small/medium inputs**: JIT compilation overhead hurts for quick operations
* **Faster for very large inputs**: JIT shines on the 5K record test (1.5x faster than CPython)
* Best suited for long-running processes or batch processing

4. Startup Overhead Dominates Small Inputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python's interpreter startup time is significant:

* CPython takes **55-75ms** even for 47 bytes of JSON
* Go takes only **3.7ms** for the same operation
* For CLI tools processing small files, Go provides a much better user experience

When to Use Each Implementation
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Use Case
     - Recommended
   * - CLI tool for small/medium files
     - **Go** (json2xml-go)
   * - High-throughput batch processing
     - **Go** or **PyPy**
   * - Integration with Python codebase
     - **CPython 3.15+**
   * - One-off conversions in scripts
     - **CPython** (any version)

Running the Benchmarks
----------------------

Python Multi-Implementation Benchmark
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Set the Go CLI path
   export JSON2XML_GO_CLI=/path/to/json2xml-go

   # Run the benchmark
   python benchmark_multi_python.py

Simple Python vs Go Benchmark
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Set paths via environment variables (optional)
   export JSON2XML_GO_CLI=/path/to/json2xml-go
   export JSON2XML_EXAMPLES_DIR=/path/to/examples

   # Run the benchmark
   python benchmark.py

Reproducing Results
-------------------

1. Install required Python versions using ``uv``:

   .. code-block:: bash

      uv python install 3.14 3.15.0a4 pypy@3.10

2. Build the Go binary:

   .. code-block:: bash

      cd /path/to/json2xml-go
      go build -o json2xml-go ./cmd/json2xml-go

3. Run the multi-Python benchmark:

   .. code-block:: bash

      cd /path/to/json2xml
      python benchmark_multi_python.py
