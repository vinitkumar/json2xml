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
