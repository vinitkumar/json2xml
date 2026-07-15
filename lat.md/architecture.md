# Architecture

This file documents the main execution paths that turn JSON input into XML output across the library, CLI, and optional Rust accelerator.

## Core pipeline

The standard pipeline reads JSON into Python objects, passes that data through [[json2xml/json2xml.py#Json2xml]], and delegates serialization through the fast backend selector in [[json2xml/dicttoxml_fast.py#dicttoxml]].

Library callers usually construct [[json2xml/json2xml.py#Json2xml]] with decoded JSON data. CLI callers reach the same conversion path through [[json2xml/cli.py#read_input]], which resolves the input source before creating the converter. Pretty output is produced by reparsing the generated XML so callers get indented text when requested.

## Conversion engine

The pure Python serializer recursively maps Python values to XML elements, attributes, and text while preserving the project-specific options around wrappers, list handling, and type metadata.

[[json2xml/dicttoxml.py#dicttoxml]] is the public serializer. It handles the XML declaration, root wrapper, namespace emission, XPath mode, and then routes nested values through helper functions such as [[json2xml/dicttoxml.py#convert]], [[json2xml/dicttoxml.py#convert_dict]], and [[json2xml/dicttoxml.py#convert_list]]. [[json2xml/dicttoxml.py#get_xml_type]] and [[json2xml/dicttoxml.py#convert]] accept broad caller input and classify unsupported values at runtime, so tests can probe failure paths without lying to the type checker. Invalid XML names are normalized by [[json2xml/dicttoxml.py#make_valid_xml_name]] instead of crashing immediately on user keys; common ASCII names use cached fast validation, while parser validation remains available for non-ASCII or unusual names. Dict and list scalar paths reuse validated element names and specialize generated type attributes so common payloads avoid repeated normalization and escaping work. Special `@attrs`/`@val` handling avoids mutating caller data.

The `dicttoxml()` entry point now normalizes options into `SerializerConfig` and delegates document shaping to a small renderer seam inside [[json2xml/dicttoxml.py#dicttoxml]]. That keeps XPath document framing, namespace emission, and root wrapping separate from the recursive element walkers.

The recursive serializer still streams normal and XPath serialization through [[json2xml/dicttoxml.py#_XMLWriter]] so dict and list payloads do not allocate a complete string for each nested subtree. Public helpers such as `convert_dict()` still return strings for compatibility by delegating to the same append path, while library and CLI conversions write UTF-8 bytes incrementally and return the final `bytes` object. Attribute formatting stays centralized through `make_attrstring()`, and `@attrs`/`@val` normalization stays local to dict element handling so caller-owned metadata is never mutated.

## Backend selection

The fast-path module prefers the Rust extension when it can preserve Python semantics, and falls back to the Python serializer for unsupported features.

[[json2xml/dicttoxml_fast.py#dicttoxml]] now normalizes each call into a shared conversion request and asks a tiny backend selector seam to choose Rust or Python. The Rust adapter accepts only requests whose semantics it can preserve, namely no `ids`, custom `item_func`, XML namespaces, XPath mode, root scalar payloads, or special `@` keys.

The backend adapter protocol exposes its diagnostic name as a read-only property, matching the frozen adapter implementations while still allowing selector code to inspect backend metadata.

A local stub for the optional `json2xml_rs` module keeps static analysis aligned with that fallback design, so type checking still passes when the extension is not installed. This keeps fast installs fast without letting the optimized path silently change behavior.

The Rust backend writes serializer output into Python's bytes writer instead of building a Rust string and copying it across the extension boundary. This keeps the fast path's peak output memory closer to the final `bytes` object.

The Rust extension crate targets the Rust 2024 edition and pins `rust-version` to the current stable toolchain so native builds fail clearly on older compilers.

The Cargo feature layout separates normal Rust/PyO3 tests from extension-module builds. `cargo test` uses the default `python` feature without extension-module linking, while maturin enables the `extension-module` feature for wheel builds.

Release and CI workflows install the pinned Rust toolchain before building wheels or running Rust checks, so hosted runners do not silently use an older default compiler. The macOS release build also provisions Python 3.10 explicitly so maturin emits wheels for the oldest supported interpreter even when runner images omit it.

## Release packaging

Package releases keep the Python wrapper and Rust accelerator requirements aligned so optional fast installs receive compatible wheels.

The Python package version lives in `pyproject.toml` and `json2xml/__init__.py`. The Rust accelerator version lives in both `rust/Cargo.toml` and `rust/pyproject.toml`, and the Python `fast` extra should require the Rust package version that contains any expected accelerator behavior. Release notes live in `HISTORY.rst`, with the current release also summarized in `RELEASE_NOTES.md` for tag and PyPI copy.

## Performance benchmarks

The benchmark docs record measured implementation tradeoffs so users can choose between Python, Rust, Go, and Zig without guessing.

The May 2026 benchmark on Apple Silicon shows the Rust extension as the best option for Python library calls, with 4-14x speedups over the optimized pure Python path and no process overhead. Go and Zig remain useful for native CLI workflows where startup cost is acceptable.

Reproduction docs require contributors to record machine, OS, Python, and tool availability before comparing results. `benchmark_all.py` mixes library calls and CLI subprocesses intentionally, so its Go and Zig rows include process startup overhead.

The June 2026 Rust memory benchmark uses [[benchmark_memory_rust.py#main]] under hyperfine to compare release builds in fresh Python processes. The bytes-writer implementation cuts serializer peak RSS by about half for large outputs, with a documented throughput tradeoff.

The June 2026 multi-interpreter CLI rerun uses [[benchmark_multi_python.py#main]] with per-interpreter virtual environments. On the recorded Apple Silicon run, CPython 3.15.0b3 beat CPython 3.14.6 on every case, PyPy 3.11.15 only won the largest case, and Go remained the fastest end-to-end CLI path overall.

The Rust serializer's bytes-writer hot path uses monomorphized `Write` helpers and a bounded 16 KiB buffer instead of dynamic dispatch and one output write per XML fragment, reducing CPU overhead while retaining direct output into the final Python bytes object and its lower peak-memory profile. A controlled CPython 3.14 benchmark improved a 5,000-record payload from roughly 4.8 ms to 2.4 ms median while keeping the 100,000-record serializer delta near 80 MiB.

The benchmark script now tracks uv-managed current-series interpreters through a configurable `JSON2XML_UV_PYTHON_DIR` base path plus per-interpreter overrides, with the documented defaults targeting CPython 3.14.6, CPython 3.15.0b3, and PyPy 3.11.15. That keeps the published setup reproducible without hard-coding one contributor's home directory.

The July 2026 CPython 3.15.0b3 flamegraph for a 5,000-record nested payload identified repeated abstract type dispatch inside [[json2xml/dicttoxml.py#_append_convert_dict]] as the pure-Python bottleneck. Exact JSON-native type paths now precede compatibility fallbacks, while [[json2xml/dicttoxml.py#_is_number]] preserves `Decimal`, `Fraction`, complex, and custom `Number` support. The fixed workload improved from 83.0 ms to 57.2 ms per conversion; a 20-loop tracing profile fell from 8.311 s and 48.17 million calls to 5.782 s and 30.13 million calls. The committed [before](../docs/flamegraphs/python315-before.svg) and [after](../docs/flamegraphs/python315-after.svg) flamegraphs preserve the call-tree evidence.

The July 2026 native Rust flamegraph identified the scalar byte loop in the XML escape writer as the largest avoidable Rust cost. The shared scanner now uses `memchr` word/SIMD search for the five XML escape bytes and copies clean UTF-8 spans in bulk without changing the bounded bytes writer. A bounded sparse fast path switches to monotonic scanners after four matches, retaining normal-payload speed while keeping dense escape input linear. On the same deterministic 5,000-record CPython 3.15.0b3 workload, paired release medians improved from 6.007 ms to 5.632 ms per conversion, or 6.23%, while the escape writer's exclusive native sample share fell from 14.31% to 7.97%. A follow-up 4–128 KiB capacity sweep retained the 16 KiB buffer: the stable range plateaued at 16–64 KiB, and an interleaved confirmation measured 16 KiB about 0.8% faster than 32 KiB without extra per-call memory. The committed [Rust before](../docs/flamegraphs/rust-before.svg) and [Rust after](../docs/flamegraphs/rust-after.svg) flamegraphs preserve the symbolized native-stack evidence.

## Dependency security

Dependency floors and lockfiles keep known vulnerable packages out of runtime and development environments.

Runtime dependencies are declared in `pyproject.toml` and mirrored by `uv.lock`; legacy requirements inputs remain pinned for tooling that still consumes requirements files. Security fixes should update both resolver paths so `uv audit` and requirements-based installs agree.

## Workflow supply-chain hardening

GitHub Actions workflows run with read-only tokens by default and use full SHA pins so third-party action updates are explicit.

The `.github/workflows/` files declare the minimum `permissions:` scopes needed by each workflow, with CodeQL retaining `security-events: write` for result upload and TestPyPI retaining `id-token: write` for explicit trusted-publishing runs. Release-branch pushes build distributions and run Twine checks; TestPyPI upload is a manual opt-in because that external registry requires separate publisher configuration. Action references are pinned to immutable commits with the upstream tag retained in comments for reviewability, and `.github/dependabot.yml` checks the `github-actions` ecosystem weekly so those pins do not silently age. The Python test matrix pins its PyPy 3.11 job to an explicit PyPy release so CI keeps exercising the intended CPython 3.11.15-compatible runtime instead of silently drifting with runner cache updates. It also exercises regular CPython 3.15.0b3 while leaving that beta's free-threaded builds out of CI until the runner support is less brittle.

Rust extension CI triggers on Rust sources, Rust integration tests, and Python fast-path files such as [[json2xml/backend_selector.py]] and [[json2xml/dicttoxml_fast.py]]. That keeps native backend tests attached to the Python dispatch code that decides whether the accelerator is used.

## CLI entrypoint

The CLI is a thin adapter that parses options, resolves one input source, and forwards those options into the same converter used by the library API.

[[json2xml/cli.py#create_parser]] defines the user-facing flags. A small `CLIApplication` seam now owns source resolution, stdin parsing, conversion, and output writing, while [[json2xml/cli.py#read_input]] and [[json2xml/cli.py#main]] remain the stable wrapper functions used by tests and callers. Command-line use and library use still meet at [[json2xml/json2xml.py#Json2xml]].
