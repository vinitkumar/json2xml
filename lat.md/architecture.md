# Architecture

This file documents the main execution paths that turn JSON input into XML output across the library, CLI, and optional Rust accelerator.

## Core pipeline

The standard pipeline reads JSON into Python objects, passes that data through [[json2xml/json2xml.py#Json2xml]], and delegates serialization through the fast backend selector in [[json2xml/dicttoxml_fast.py#dicttoxml]].

Library callers usually construct [[json2xml/json2xml.py#Json2xml]] with decoded JSON data. CLI callers reach the same conversion path through [[json2xml/cli.py#read_input]], which resolves the input source before creating the converter. Pretty output is produced by reparsing the generated XML so callers get indented text when requested.

## Conversion engine

The pure Python serializer recursively maps Python values to XML elements, attributes, and text while preserving the project-specific options around wrappers, list handling, and type metadata.

[[json2xml/dicttoxml.py#dicttoxml]] is the public serializer. It handles the XML declaration, root wrapper, namespace emission, XPath mode, and then routes nested values through helper functions such as [[json2xml/dicttoxml.py#convert]], [[json2xml/dicttoxml.py#convert_dict]], and [[json2xml/dicttoxml.py#convert_list]]. [[json2xml/dicttoxml.py#get_xml_type]] and [[json2xml/dicttoxml.py#convert]] accept broad caller input and classify unsupported values at runtime, so tests can probe failure paths without lying to the type checker. Invalid XML names are normalized by [[json2xml/dicttoxml.py#make_valid_xml_name]] instead of crashing immediately on user keys; common ASCII names use cached fast validation, while parser validation remains available for non-ASCII or unusual names. Dict and list scalar paths reuse validated element names and specialize generated type attributes so common payloads avoid repeated normalization and escaping work. Special `@attrs`/`@val` handling avoids mutating caller data.

The root wrapper path releases the unwrapped XML body before UTF-8 encoding the final document. That keeps peak memory closer to the returned byte size without changing the recursive serializer contract.

## Backend selection

The fast-path module prefers the Rust extension when it can preserve Python semantics, and falls back to the Python serializer for unsupported features.

[[json2xml/dicttoxml_fast.py#dicttoxml]] uses the Rust backend only when optional features such as `ids`, custom `item_func`, XML namespaces, XPath mode, root scalar payloads, or special `@` keys are not involved. A local stub for the optional `json2xml_rs` module keeps static analysis aligned with that fallback design, so type checking still passes when the extension is not installed. This keeps fast installs fast without letting the optimized path silently change behavior.

The Rust backend writes serializer output into Python's bytes writer instead of building a Rust string and copying it across the extension boundary. This keeps the fast path's peak output memory closer to the final `bytes` object.

## Performance benchmarks

The benchmark docs record measured implementation tradeoffs so users can choose between Python, Rust, Go, and Zig without guessing.

The May 2026 benchmark on Apple Silicon shows the Rust extension as the best option for Python library calls, with 4-14x speedups over the optimized pure Python path and no process overhead. Go and Zig remain useful for native CLI workflows where startup cost is acceptable.

Reproduction docs require contributors to record machine, OS, Python, and tool availability before comparing results. `benchmark_all.py` mixes library calls and CLI subprocesses intentionally, so its Go and Zig rows include process startup overhead.

The June 2026 Rust memory benchmark uses [[benchmark_memory_rust.py#main]] to compare release builds in fresh Python processes. The bytes-writer implementation cuts serializer peak RSS by about half for large outputs, with a documented throughput tradeoff.

## Dependency security

Dependency floors and lockfiles keep known vulnerable packages out of runtime and development environments.

Runtime dependencies are declared in `pyproject.toml` and mirrored by `uv.lock`; legacy requirements inputs remain pinned for tooling that still consumes requirements files. Security fixes should update both resolver paths so `uv audit` and requirements-based installs agree.

## Workflow supply-chain hardening

GitHub Actions workflows run with read-only tokens by default and use full SHA pins so third-party action updates are explicit.

The `.github/workflows/` files declare the minimum `permissions:` scopes needed by each workflow, with CodeQL retaining `security-events: write` for result upload. Action references are pinned to immutable commits with the upstream tag retained in comments for reviewability, and `.github/dependabot.yml` checks the `github-actions` ecosystem weekly so those pins do not silently age.

## CLI entrypoint

The CLI is a thin adapter that parses options, resolves one input source, and forwards those options into the same converter used by the library API.

[[json2xml/cli.py#create_parser]] defines the user-facing flags. [[json2xml/cli.py#read_input]] enforces the source priority rules, and [[json2xml/cli.py#main]] constructs [[json2xml/json2xml.py#Json2xml]] so command-line use and library use stay aligned.
