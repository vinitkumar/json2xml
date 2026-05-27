Benchmarks
==========

Comprehensive performance comparison between all json2xml implementations.

Test Environment
----------------

* **Machine**: Apple Silicon (arm64)
* **OS**: macOS 26.5 (Darwin 25.5.0)
* **Python**: 3.14.4
* **Date**: May 27, 2026
* **CLI tools**: ``json2xml-go`` and ``json2xml-zig`` from ``/Users/vinitkumar/.local/bin``

Implementations Tested
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Implementation
     - Type
     - Notes
   * - Python
     - Library
     - Pure Python ``json2xml``
   * - Rust
     - Library
     - Native extension via PyO3, imported as ``json2xml_rs``
   * - Go
     - CLI
     - Standalone ``json2xml-go`` binary
   * - Zig
     - CLI
     - Standalone ``json2xml-zig`` binary

Test Data
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 55 25

   * - Size
     - Description
     - Bytes
   * - Small
     - Simple object ``{"name": "John", "age": 30, "city": "New York"}``
     - 47
   * - Medium
     - 10 generated records with nested structures
     - 3,215
   * - bigexample.json
     - Real-world patent data
     - 2,018
   * - Large
     - 100 generated records with nested structures
     - 32,206
   * - Very Large
     - 1,000 generated records with nested structures
     - 323,131

Results
-------

Performance Summary
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 18 18 18 18

   * - Test Case
     - Python
     - Rust
     - Go
     - Zig
   * - Small (47B)
     - 3.19µs
     - 0.86µs
     - 6.05ms
     - 3.08ms
   * - Medium (3.2KB)
     - 214.83µs
     - 18.41µs
     - 5.85ms
     - 3.12ms
   * - bigexample (2KB)
     - 91.20µs
     - 7.32µs
     - 5.76ms
     - 3.08ms
   * - Large (32KB)
     - 2.07ms
     - 175.46µs
     - 5.89ms
     - 3.73ms
   * - Very Large (323KB)
     - 21.20ms
     - 1.48ms
     - 6.82ms
     - 7.82ms

Speedup vs Pure Python
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 34 22 22 22

   * - Test Case
     - Rust
     - Go
     - Zig
   * - Small (47B)
     - **3.7x**
     - 0.0x*
     - 0.0x*
   * - Medium (3.2KB)
     - **11.7x**
     - 0.0x*
     - 0.1x*
   * - bigexample (2KB)
     - **12.5x**
     - 0.0x*
     - 0.0x*
   * - Large (32KB)
     - **11.8x**
     - 0.4x*
     - 0.6x*
   * - Very Large (323KB)
     - **14.4x**
     - **3.1x**
     - **2.7x**

*CLI tools have process spawn overhead of about 3-6ms, which dominates for small inputs.*

Key Observations
----------------

Rust remains the best option for Python library calls. It avoids process overhead and is about 4-14x faster than the optimized pure Python path in this run.

Recent pure Python improvements substantially reduced conversion time. Medium and large inputs are roughly an order of magnitude faster than the April 2026 baseline, so relative Rust speedups are lower even though Rust is still fastest.

Go and Zig remain useful for native CLI workflows. They are slower for small and medium inputs because startup dominates, but both beat Python on the 323KB workload when full CLI process time is measured.

When to Use Each Implementation
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 40 25 35

   * - Use Case
     - Recommended
     - Why
   * - Python library calls
     - **Rust**
     - 4-14x faster, no process overhead
   * - Small files via CLI
     - **Zig**
     - Fastest startup among native CLIs in this run
   * - Large files via CLI
     - **Go** or **Zig**
     - Both are faster than Python at 323KB
   * - Batch processing
     - **Go** or **Rust**
     - Choose based on shell vs Python integration
   * - Pure Python required
     - **Python**
     - Always available

Running the Benchmarks
----------------------

Run benchmarks from a clean checkout with the project installed in an isolated environment.

.. code-block:: bash

   uv venv
   source .venv/bin/activate
   uv pip install -e .
   python benchmark_all.py

For Rust benchmarks, install the extension into the same environment.

.. code-block:: bash

   uv pip install maturin
   cd rust
   maturin develop --release
   cd ..

For native CLI benchmarks, install the external tools and verify that the commands are visible.

.. code-block:: bash

   go install github.com/vinitkumar/json2xml-go@latest
   which json2xml-go
   which json2xml-zig
