# json2xml_rs 0.4.2

Released 2026-07-15.

## Highlights

- Replaced scalar XML escape-byte scanning with `memchr` word/SIMD-optimized searches for the five XML escape characters.
- Preserved the bounded 16 KiB streaming writer after a 4–128 KiB capacity sweep found no benefit from increasing it.
- Kept the serialized output byte-for-byte identical at 4,093,244 bytes for the release benchmark payload.

## Performance

The paired CPython 3.15.0b3 release benchmark serialized the deterministic 5,000-record payload in 21 rounds of 50 conversions.

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| Median conversion | 6.007 ms | 5.632 ms | 6.23% lower |
| Mean conversion | 6.013 ms | 5.643 ms | 6.14% lower |
| Escape scanner exclusive samples | 14.31% | 7.97% | 44.3% lower share |

The committed [before](docs/flamegraphs/rust-before.svg) and [after](docs/flamegraphs/rust-after.svg) flamegraphs show the reduced escape-scanner cost. Rejected tag-building and dispatch experiments regressed the same workload by 6–38%, so this release keeps the optimization deliberately narrow.

## Package Version

- Rust accelerator: `json2xml-rs==0.4.2`

## Verification

The release is gated on Rust formatting and Clippy checks, Rust unit tests, the full Python suite, and built-wheel tests for Linux, macOS, and Windows before PyPI publication.


# json2xml 6.4.0 and json2xml_rs 0.4.1

Released 2026-07-13.

## Highlights

- Added bounded 16 KiB buffering to the Rust serializer's direct Python-bytes output path.
- Reduced the 5,000-record benchmark median from roughly 4.8 ms to 2.4 ms while keeping serializer memory near 80 MiB.
- Kept XML output byte-for-byte identical.

## Package Versions

- Python package: `json2xml==6.4.0`
- Rust accelerator package: `json2xml-rs==0.4.1`
- Fast install: `pip install "json2xml[fast]"`

## Verification

The release passed the Python and Rust test suites, Rust wheel builds across supported platforms, and the Rust wheel compatibility matrix.


# json2xml 6.3.0 and json2xml_rs 0.4.0

Released 2026-06-10.

## Highlights

- Reduced allocation pressure in the pure Python serializer hot paths for dicts, lists, scalar values, XML names, and emitted attributes.
- Kept the Python and Rust release line aligned: `json2xml[fast]` now requires `json2xml-rs>=0.4.0`.
- Documented the Rust memory benchmark in enough detail to reproduce the 100,000-record RSS measurement and understand the throughput tradeoff.

## Why Upgrade

This release is focused on large conversion workloads. The 6.2.0 Rust release moved accelerator output directly into Python bytes to reduce peak serializer memory; 6.3.0 follows that with Python-side allocation reductions so fallback and unsupported-option paths also benefit.

No XML shape changes are intended. Existing callers should see the same output for supported options, including invalid-name normalization, `@attrs`/`@val` handling, list wrapping, XPath mode, and pure Python fallback behavior.

## Package Versions

- Python package: `json2xml==6.3.0`
- Rust accelerator package: `json2xml-rs==0.4.0`
- Fast install: `pip install "json2xml[fast]"`

## Changelog

- `feat`: reduce pure Python serializer allocations in hot dict, list, and scalar paths.
- `feat`: preserve XML output semantics while reusing validated element-name and attribute work.
- `perf`: lower peak memory pressure for large conversions after the 6.2.0 Rust bytes-writer release.
- `docs`: add hyperfine Rust memory benchmark notes with reproduction details and the measured throughput tradeoff.
- `chore`: release `json2xml-rs` 0.4.0 and require it from `json2xml[fast]` for accelerated installs.

## Verification

The release changes are covered by the existing serializer, fast-backend, and Rust parity tests. The benchmark documentation records the measurement setup separately from the functional test suite so release consumers can reproduce performance results on their own hardware.
