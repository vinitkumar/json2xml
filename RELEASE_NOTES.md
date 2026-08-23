# json2xml 7.0.0

Released 2026-08-23.

## Highlights

- Makes compact UTF-8 `bytes` the default output for the Python API and CLI, avoiding a second XML formatting pass on the common path.
- Generates explicit pretty output during serialization instead of re-tokenizing completed XML, improving measured pretty conversion time by 46-53%.
- Enforces output limits against the exact generated UTF-8 bytes so valid payloads are no longer rejected by a conservative size estimate.
- Requires the independently published `json2xml-rs>=0.5.0`, whose native capability gate preserves byte-for-byte parity with the Python serializer.
- Fixes malformed rootless `list_headers` output, inconsistent date-like values, unsupported falsy objects serialized as null, and caller attribute dictionaries being mutated.

## Breaking changes and migration guidance

- `Json2xml(...).to_xml()` now returns compact `bytes` by default. Pass `pretty=True` to retain pretty Unicode `str` output, or decode compact output explicitly when text is required.
- The CLI now writes compact XML by default. Pass `--pretty` to retain indented output.
- Unsupported falsy objects now raise `TypeError` instead of silently serializing as XML null. Convert such values to a supported JSON-native type before serialization.
- Pretty output keeps empty elements such as `<h type="null"></h>` on one line because indentation is generated from serializer structure rather than reconstructed from markup.

## Correctness and performance

- The Rust selector admits only payloads whose names and values the native backend reproduces exactly; unsupported inputs continue through Python without losing functionality.
- Conversion depth and item limits remain preflight checks, while compact and pretty byte limits include the exact emitted markup, indentation, and trailing newline.
- `datetime.time` and other date-like values now serialize consistently at the root, in dictionaries, and in lists.
- ASCII XML attribute-name validation avoids constructing a DOM for the common case.
- The Rust 1,000-record capability gate improved from 1.14 ms to 0.09 ms, reducing the complete accelerated conversion from 1.51 ms to 0.49 ms.

## Package Versions

- Python package: `json2xml==7.0.0`
- Rust accelerator: `json2xml-rs==0.5.0`
- Fast install: `pip install "json2xml[fast]==7.0.0"`

## Verification

The release passed Ruff, ty, 596 Python tests with 100% statement coverage, Rust formatting, Clippy with warnings denied, 47 Rust unit tests, package builds, and the complete hosted Python and Rust compatibility matrices. The published Rust 0.5.0 wheel was also installed and smoke-tested before the Python dependency floor was raised.


# json2xml_rs 0.5.0

Released 2026-08-23.

## Highlights

- Makes the Rust serializer byte-identical to the Python serializer for every payload routed to it, correcting CDATA handling, nested list shapes, list member tags, dictionary type metadata, rootless output, and names beginning with `xml`.
- Adds a native payload capability gate so non-JSON-native values and parser-resolved names fall back to Python instead of producing different XML.
- Cuts the 1,000-record payload gate from 1.14 ms to 0.09 ms and the complete accelerated conversion from 1.51 ms to 0.49 ms.
- Normalizes borrowed list member names so rootless dictionaries under `list_headers` remain well-formed.

## Migration guidance

The native backend now accepts only the subset it can reproduce exactly: dictionaries, lists, tuples, and exact string, boolean, integer, float, and null values with mutually compatible element names. Other payloads continue to work through the Python serializer.

Python wrappers should require `json2xml-rs>=0.5.0` before relying on the native `payload_is_supported()` gate. Older extensions remain safe with the current wrapper because the missing capability causes automatic fallback to Python.

## Package Version

- Rust accelerator: `json2xml-rs==0.5.0`

## Verification

The release passed Rust formatting, Clippy with warnings denied, 47 Rust unit tests, and 596 Python tests with 100% statement coverage. Publication is additionally gated on built-wheel tests across Linux, macOS, Windows, CPython 3.10-3.15, and PyPy.


# json2xml 6.5.1

Released 2026-08-05.

## Highlights

- Pins public URL connections to the validated DNS address while preserving the requested Host header and TLS certificate hostname, preventing DNS-rebinding bypasses of private-network blocking.
- Bounds encoded input and incremental gzip or deflate output so compressed responses cannot consume unbounded network I/O or memory before rejection.
- Rejects XML 1.0-forbidden characters consistently across the Python serializer and the newly published Rust accelerator instead of emitting invalid XML.
- Updates `json2xml[fast]` to require the compatible `json2xml-rs>=0.4.3` release.

## Security

- URL reads reject redirects and private, loopback, link-local, and other non-global destinations by default, including destinations reached through DNS rebinding.
- Encoded and decoded response bodies are independently limited to 10 MiB by default.
- Only `gzip`, `x-gzip`, `deflate`, and `identity` content encodings are accepted; malformed or stacked encodings are rejected.
- `allow_private_networks` accepts only `True` or `False`, avoiding truthiness-based policy bypasses.
- Malformed Unicode hostnames consistently raise `URLReadError` when IDNA encoding or DNS resolution fails.

## Migration guidance

- Trusted callers that intentionally read private endpoints must pass `allow_private_networks=True` as an actual boolean.
- Set `max_response_bytes` explicitly when a trusted endpoint needs a positive response limit other than the 10 MiB default.
- Servers returning Brotli, Zstandard, stacked encodings, or malformed compressed streams must be reconfigured or read outside `readfromurl()`.
- Inputs containing forbidden XML 1.0 characters now fail validation. Low-level serializer functions raise `ValueError`; `Json2xml.to_xml()` raises `InvalidDataError`.

## Package Versions

- Python package: `json2xml==6.5.1`
- Rust accelerator: `json2xml-rs==0.4.3`
- Fast install: `pip install "json2xml[fast]==6.5.1"`

## Verification

The release passed 496 tests with 100% statement coverage, Ruff, ty, sdist and wheel builds, Twine metadata checks, and an isolated install against the published `json2xml-rs==0.4.3` wheel. The pull request also runs the complete cross-platform Python matrix before merge.


# json2xml_rs 0.4.3

Released 2026-08-05.

## Highlights

- Rejects XML 1.0-forbidden characters in serialized text, attributes, CDATA, and the exported `escape_xml_py()` and `wrap_cdata_py()` helpers instead of emitting invalid XML.
- Gives the Python package a compatible accelerator that passes its XML-safety probe, restoring automatic Rust dispatch for supported payloads.
- Updates PyO3 from 0.28.2 to 0.29.1 while preserving the existing Python 3.9+ package contract and wheel matrix.

## Migration guidance

Inputs containing forbidden XML 1.0 characters now raise `ValueError`. Remove or replace those characters before conversion; callers must not depend on invalid XML being emitted.

## Package Version

- Rust accelerator: `json2xml-rs==0.4.3`

## Verification

The release passed Rust formatting, Clippy with warnings denied, 48 Rust unit tests, and built-wheel tests across Linux, macOS, Windows, CPython 3.9-3.15, free-threaded builds, and PyPy before PyPI publication.


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
