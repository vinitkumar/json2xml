Rust Memory Benchmark
=====================

This benchmark compares peak memory usage before and after the Rust serializer started writing directly into Python ``bytes``.

Summary
-------

The current branch reduces serializer peak RSS by about **77.44 MiB** on a 100,000-record payload that produces **78.17 MiB** of XML. That is a **49.1% reduction** in serializer memory delta compared with the previous PR commit.

.. list-table::
   :header-rows: 1
   :widths: 24 22 22 22 22

   * - Version
     - Commit
     - Avg peak RSS
     - Avg serializer delta
     - Avg time
   * - Previous
     - ``7dd86b0``
     - 349.15 MiB
     - 157.70 MiB
     - 0.180s
   * - Current
     - ``07d840f``
     - 271.65 MiB
     - 80.26 MiB
     - 0.265s

The memory result matches the implementation change: the previous version held roughly one final XML payload in Rust plus one Python ``bytes`` payload, while the current version writes into the Python ``bytes`` object directly.

Methodology
-----------

The benchmark uses ``benchmark_memory_rust.py`` with a deterministic generated payload so the Rust fast path can be measured without file parsing or pure-Python fallback behavior.

* Machine: Apple Silicon arm64
* OS: macOS 26.5
* Python: 3.14.0
* Build: ``python3 -m maturin develop --release --offline``
* Payload: 100,000 nested records
* Input JSON size: 44.31 MiB
* Output XML size: 78.17 MiB
* Measurement: process ``ru_maxrss`` after payload creation versus peak after ``json2xml_rs.dicttoxml(payload, attr_type=True)``
* Sampling: three fresh Python processes per version

The baseline RSS is captured after the large Python payload is already built. The reported serializer delta is ``peak_rss - baseline_rss``, which focuses the comparison on output construction rather than payload allocation.

Raw Samples
-----------

.. list-table::
   :header-rows: 1
   :widths: 24 18 18 18 18

   * - Run
     - Baseline RSS
     - Peak RSS
     - Serializer delta
     - Time
   * - previous-release-1
     - 191.53 MiB
     - 349.22 MiB
     - 157.69 MiB
     - 0.182s
   * - previous-release-2
     - 191.39 MiB
     - 349.09 MiB
     - 157.70 MiB
     - 0.179s
   * - previous-release-3
     - 191.44 MiB
     - 349.14 MiB
     - 157.70 MiB
     - 0.178s
   * - current-release-1
     - 191.45 MiB
     - 271.77 MiB
     - 80.31 MiB
     - 0.265s
   * - current-release-2
     - 191.48 MiB
     - 271.64 MiB
     - 80.16 MiB
     - 0.272s
   * - current-release-3
     - 191.25 MiB
     - 271.55 MiB
     - 80.30 MiB
     - 0.258s

Tradeoff
--------

The memory improvement comes with a throughput cost in this release benchmark. Average conversion time increased from 0.180s to 0.265s, about **47.5% slower** for this payload.

That cost is likely from routing every XML write through ``std::io::Write`` and PyO3's bytes writer. The memory win is substantial for large outputs, but latency-sensitive callers may want more timing data before treating the bytes-writer path as a universal improvement.

Reproduction
------------

Run each version in a fresh process after installing the desired Rust extension build.

.. code-block:: bash

   python3 -m maturin develop --release --offline
   python3 benchmark_memory_rust.py --records 100000 --label current-release-1

For the previous comparison, install commit ``7dd86b0`` in a temporary worktree, then run the same command from the main checkout so the benchmark script stays identical.
