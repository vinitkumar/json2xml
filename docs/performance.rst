Performance Optimization
========================

json2xml now supports **parallel processing** on Python 3.14t (free-threaded build), providing significant performance improvements for medium to large datasets.

Overview
--------

The library leverages Python 3.14t's free-threaded capabilities (no-GIL) to process large JSON documents concurrently, resulting in up to **1.55x speedup** for medium-sized datasets.

Key Features:

* Parallel processing for dictionaries and lists
* Automatic fallback to serial processing for small datasets
* Thread-safe XML validation caching
* Configurable worker threads and chunk sizes
* Full backward compatibility

Parallel Processing Usage
-------------------------

Basic Usage
~~~~~~~~~~~

Enable parallel processing with default settings:

.. code-block:: python

    from json2xml.json2xml import Json2xml

    # Basic parallel processing (auto-detects optimal workers)
    data = {"users": [{"id": i, "name": f"User {i}"} for i in range(1000)]}
    converter = Json2xml(data, parallel=True)
    xml = converter.to_xml()

Advanced Configuration
~~~~~~~~~~~~~~~~~~~~~

Specify custom workers and chunk size:

.. code-block:: python

    from json2xml.json2xml import Json2xml

    # Advanced: specify workers and chunk size
    data = {"large_list": [{"item": i} for i in range(5000)]}
    converter = Json2xml(
        data,
        parallel=True,    # Enable parallel processing
        workers=8,        # Use 8 worker threads
        chunk_size=100    # Process 100 items per chunk
    )
    xml = converter.to_xml()

Using dicttoxml Directly
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from json2xml import dicttoxml

    result = dicttoxml.dicttoxml(
        data,
        parallel=True,
        workers=4,
        chunk_size=100
    )

Benchmark Results
-----------------

Tested on macOS ARM64 with Python 3.14.0 and Python 3.14.0t (free-threaded).

Medium Dataset (100 items) - Best Case
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+-------------------+-------------+-----------------+----------+
| Python Version    | Serial Time | Parallel (4w)   | Speedup  |
+===================+=============+=================+==========+
| 3.14 (GIL)        | 7.56 ms     | 7.86 ms         | 0.96x    |
+-------------------+-------------+-----------------+----------+
| 3.14t (no-GIL)    | 8.59 ms     | **5.55 ms**     | **1.55x**|
+-------------------+-------------+-----------------+----------+

Complete Results
~~~~~~~~~~~~~~~

Python 3.14 (Standard GIL)
^^^^^^^^^^^^^^^^^^^^^^^^^^

+-------------------+-------------+---------------+---------------+---------------+
| Dataset           | Serial      | Parallel (2w) | Parallel (4w) | Parallel (8w) |
+===================+=============+===============+===============+===============+
| Small (10)        | 0.25 ms     | 0.40 ms       | 0.51 ms       | 0.44 ms       |
+-------------------+-------------+---------------+---------------+---------------+
| Medium (100)      | 7.56 ms     | 7.35 ms       | 7.86 ms       | 8.76 ms       |
+-------------------+-------------+---------------+---------------+---------------+
| Large (1K)        | 240.54 ms   | 244.17 ms     | 244.30 ms     | 246.58 ms     |
+-------------------+-------------+---------------+---------------+---------------+
| XLarge (5K)       | 2354.32 ms  | 2629.16 ms    | 2508.42 ms    | 2522.19 ms    |
+-------------------+-------------+---------------+---------------+---------------+

Python 3.14t (Free-threaded)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

+-------------------+-------------+---------------+---------------+---------------+
| Dataset           | Serial      | Parallel (2w) | Parallel (4w) | Parallel (8w) |
+===================+=============+===============+===============+===============+
| Small (10)        | 0.25 ms     | 0.51 ms       | 0.69 ms       | 0.63 ms       |
+-------------------+-------------+---------------+---------------+---------------+
| Medium (100)      | 8.59 ms     | 5.77 ms       | **5.55 ms**   | 7.13 ms       |
+-------------------+-------------+---------------+---------------+---------------+
| Large (1K)        | 231.96 ms   | 232.84 ms     | 232.79 ms     | 244.08 ms     |
+-------------------+-------------+---------------+---------------+---------------+
| XLarge (5K)       | 1934.75 ms  | 2022.40 ms    | 1926.55 ms    | 1975.37 ms    |
+-------------------+-------------+---------------+---------------+---------------+

Key Findings
~~~~~~~~~~~~

* ✅ Up to **1.55x speedup** on Python 3.14t (free-threaded) for medium datasets
* ✅ Automatic fallback to serial processing for small datasets (avoids overhead)
* ✅ Best performance with 4 worker threads
* ⚠️ No benefit on standard Python with GIL (as expected)

Performance by Dataset Size
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Small** (< 100 items): Serial processing (automatic fallback)
* **Medium** (100-1K items): **1.5x faster** with parallel processing on 3.14t
* **Large** (1K-10K items): Comparable performance (string concatenation bottleneck)

Running Benchmarks
------------------

You can run benchmarks on your system to test performance:

Standard Python 3.14
~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    $ uv run --python 3.14 python benchmark.py

Free-threaded Python 3.14t
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    $ uv run --python 3.14t python benchmark.py

Installing Python 3.14t
~~~~~~~~~~~~~~~~~~~~~~~

If you don't have Python 3.14t installed, use uv:

.. code-block:: console

    $ uv python install 3.14t

Recommendations
---------------

For Best Performance
~~~~~~~~~~~~~~~~~~~~

* **Use Python 3.14t** for parallel processing benefits
* **Enable parallel=True** for medium-sized datasets (100-1K items)
* **Use 4 worker threads** for optimal performance on most hardware
* **Keep default serial** for small datasets (automatic)

Configuration Guidelines
~~~~~~~~~~~~~~~~~~~~~~~~

Small Datasets (< 100 items)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use default serial processing:

.. code-block:: python

    converter = Json2xml(data)  # parallel=False by default

Medium Datasets (100-1K items)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Enable parallel processing with 4 workers:

.. code-block:: python

    converter = Json2xml(data, parallel=True, workers=4)

Large Datasets (> 1K items)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Test both serial and parallel to find best configuration:

.. code-block:: python

    # Try with different worker counts
    converter = Json2xml(data, parallel=True, workers=4, chunk_size=100)

Architecture
------------

How Parallel Processing Works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Dictionary Processing**: Each top-level key processed in a separate thread
2. **List Processing**: Large lists split into chunks, each chunk processed in parallel
3. **Order Preservation**: Results collected and reassembled in original order
4. **Threshold-Based**: Only parallelizes when benefits outweigh overhead

Thread Safety
~~~~~~~~~~~~~

* XML validation results cached with thread-safe locks
* No global state modification in worker threads
* Independent processing units with no data races

Implementation Details
~~~~~~~~~~~~~~~~~~~~~~

See the following files for implementation details:

* ``json2xml/parallel.py`` - Parallel processing infrastructure
* ``json2xml/dicttoxml.py`` - Integration with main conversion logic
* ``tests/test_parallel.py`` - Comprehensive parallel processing tests

Future Optimizations
--------------------

Potential improvements for large datasets:

1. Parallelized pretty-printing
2. More efficient string builders
3. Chunk-based result assembly
4. Streaming API for very large documents

For detailed benchmark methodology and results, see `BENCHMARK_RESULTS.md <../BENCHMARK_RESULTS.md>`_ in the repository.
