Rust Memory Benchmark
=====================

This benchmark compares peak memory usage before and after the Rust serializer started writing directly into Python ``bytes``.

Summary
-------

The current branch still reduces serializer peak RSS by about **77.43 MiB** on a 100,000-record payload that produces **78.17 MiB** of XML. That is a **49.1% reduction** in serializer memory delta compared with the previous PR commit.

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
     - ``43543e8`` + worktree
     - 270.91 MiB
     - 80.27 MiB
     - 0.232s

The memory result matches the implementation change: the previous version held roughly one final XML payload in Rust plus one Python ``bytes`` payload, while the current version writes into the Python ``bytes`` object directly.

Methodology
-----------

The benchmark uses ``benchmark_memory_rust.py`` with a deterministic generated payload so the Rust fast path can be measured without file parsing or pure-Python fallback behavior.

* Machine: Apple Silicon arm64
* OS: macOS 26.5.1
* Python: 3.14.0
* Build: ``python3 -m maturin develop --release --offline``
* Payload: 100,000 nested records
* Input JSON size: 44.31 MiB
* Output XML size: 78.17 MiB
* Measurement: process ``ru_maxrss`` after payload creation versus peak after ``json2xml_rs.dicttoxml(payload, attr_type=True)``
* Sampling: five fresh Python processes for the current version using ``hyperfine 1.20.0 --runs 5 --show-output --export-json``

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
   * - current-hyperfine-1
     - 190.77 MiB
     - 271.12 MiB
     - 80.36 MiB
     - 0.233s
   * - current-hyperfine-2
     - 190.66 MiB
     - 271.02 MiB
     - 80.36 MiB
     - 0.234s
   * - current-hyperfine-3
     - 190.62 MiB
     - 270.98 MiB
     - 80.36 MiB
     - 0.234s
   * - current-hyperfine-4
     - 190.78 MiB
     - 270.84 MiB
     - 80.06 MiB
     - 0.231s
   * - current-hyperfine-5
     - 190.38 MiB
     - 270.61 MiB
     - 80.23 MiB
     - 0.229s

Hyperfine Result
----------------

Hyperfine measured full fresh-process runtime for the current benchmark command at **684.3 ms +/- 26.5 ms** across five runs, with a range of **664.1 ms to 728.0 ms**. The exported hyperfine memory sample was **272.59 MiB**, which is consistent with the script's average peak RSS of **270.91 MiB**.

Tradeoff
--------

The memory improvement comes with a throughput cost in this release benchmark. Average conversion time increased from the previous 0.180s to the current hyperfine-sampled 0.232s, about **29.0% slower** for this payload.

That cost is likely from routing every XML write through ``std::io::Write`` and PyO3's bytes writer. The memory win is substantial for large outputs, but latency-sensitive callers may want more timing data before treating the bytes-writer path as a universal improvement.

Reproduction
------------

Run each version in a fresh process after installing the desired Rust extension build.

.. code-block:: bash

   python3 -m maturin develop --release --offline
   hyperfine --runs 5 --show-output --export-json /private/tmp/json2xml-rust-memory-hyperfine.json \
     'python3 benchmark_memory_rust.py --records 100000 --label current-hyperfine'

For the previous comparison, install commit ``7dd86b0`` in a temporary worktree, then run the same command from the main checkout so the benchmark script stays identical.
