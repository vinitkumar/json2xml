# Unreleased

## Security

- Public URL reads now pin connections to a validated DNS address while preserving the requested Host header and HTTPS certificate hostname, preventing DNS-rebinding bypasses of private-network blocking.
- Gzip and deflate responses are decoded incrementally with bounded zlib output, so compressed bodies cannot allocate beyond `max_response_bytes` before rejection.
- `allow_private_networks` accepts only `True` or `False`; strings, numbers, and other values now raise `URLReadError` instead of relying on truthiness.
- Malformed Unicode hostnames now consistently raise `URLReadError` when IDNA encoding or DNS resolution fails.

## Migration guidance

- URL reads continue to reject redirects and private, loopback, link-local, and other non-global destinations by default. Trusted callers that intentionally read a private endpoint must pass `allow_private_networks=True` as an actual boolean.
- Decoded URL responses remain limited to 10 MiB by default. Set `max_response_bytes` explicitly when a trusted endpoint needs a different positive limit.
- URL response compression is limited to `gzip`, `x-gzip`, `deflate`, and `identity`. Servers returning Brotli, Zstandard, stacked encodings, or malformed compressed streams must be reconfigured or read outside `readfromurl()`.
- XML 1.0-forbidden characters are now rejected instead of being serialized. Low-level serializer functions raise `ValueError`; `Json2xml.to_xml()` raises `InvalidDataError`.

## Release prerequisite

Publish a compatible accelerator version newer than `json2xml-rs==0.4.2`, then raise the `json2xml[fast]` and `uv.lock` minimum to that published version. Until then, the compatibility probe safely disables 0.4.2 and uses the Python backend.


# json2xml 6.5.0

Released 2026-07-15.

## Highlights

- Reduced pure Python serializer time by 31.1% on the deterministic 5,000-record workload by using exact native-type dispatch on hot paths while preserving subclass fallbacks.
- Added explicit regression coverage for `Decimal`, `Fraction`, complex, custom `Number`, string, dictionary, list, and tuple subclasses.
- Made the complete Python suite an exact 100% statement-coverage gate: 421 tests cover all 762 statements.
- Updated `json2xml[fast]` to require the published `json2xml-rs>=0.4.2` accelerator.

## Performance

All profiles used uv-managed CPython 3.15.0b3 and the same deterministic 5,000-record nested payload.

| Pure Python metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| Conversion time | 83.0 ms | 57.2 ms | 31.1% lower |
| 20-loop traced time | 8.311 s | 5.782 s | 30.4% lower |
| Function calls | 48.17 million | 30.13 million | 37.4% fewer |
| `isinstance` calls | 11.70 million | 2.80 million | 76.1% fewer |

The Rust 0.4.2 accelerator released first and improved its paired release median from 6.007 ms to 5.632 ms, or 6.23%, with identical 4,093,244-byte output. Its hybrid scanner keeps dense XML escape input linear, and the measured 16 KiB streaming buffer remains unchanged.

## Package Versions

- Python package: `json2xml==6.5.0`
- Rust accelerator: `json2xml-rs==0.4.2`
- Fast install: `pip install "json2xml[fast]==6.5.0"`

## Profiling Evidence

- [Python before flamegraph](docs/flamegraphs/python315-before.svg)
- [Python after flamegraph](docs/flamegraphs/python315-after.svg)
- [Rust before flamegraph](docs/flamegraphs/rust-before.svg)
- [Rust after flamegraph](docs/flamegraphs/rust-after.svg)

## Verification

The release passed the full cross-platform Python matrix, Rust formatting and Clippy checks, 48 Rust unit tests, 421 Python tests with exactly 100% statement coverage, and install tests against the published Rust 0.4.2 wheels.


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
