---
lat:
  require-code-mention: true
---
# Tests

This file defines a small, high-signal test slice that anchors the initial lat.md setup to behavior the project should keep stable.

## CLI input resolution

These tests lock down how the CLI chooses among competing input sources so callers get deterministic behavior instead of surprise precedence games.

### URL input takes priority

When both URL and string inputs are present, the CLI should read from the URL first so the documented source precedence remains stable.

### Dash argument reads stdin

When the positional input is `-`, the CLI should read stdin instead of trying to open a file literally named `-`.

## Input readers

These tests verify the concrete reader helpers against realistic source behavior so parsing and error wrapping stay aligned with production use.

### URL reader uses real HTTP and wraps failures

URL input should read valid JSON over HTTP and wrap status, network, and decoding failures in `URLReadError`.

## CLI failure messages

These tests verify common command-line failures return short messages that name the broken input source and point users at the next valid action.

### No input is actionable

Running the CLI without JSON should fail with a message that tells users to pass a file, stdin, string, or URL instead of only reporting a generic error.

### Invalid file JSON names the source

Malformed JSON read from an existing file should mention that file path so users can distinguish file parsing failures from missing-file, string, stdin, or conversion failures.

### No-input guard stays total if exit helper is bypassed

The CLI no-input branch should still fail loudly with its internal assertion if the exit helper is replaced during tests or embedding, so the control flow cannot fall through silently.

## Performance benchmarks

These tests pin the benchmark script configuration rules so contributors can rerun published measurements without inheriting one machine's filesystem layout.

### Benchmark script derives interpreter paths from configurable uv base dir

The multi-interpreter benchmark should derive default interpreter paths from `JSON2XML_UV_PYTHON_DIR` so the documented uv layout stays portable across machines.

### Benchmark script lets explicit interpreter env vars override uv defaults

The multi-interpreter benchmark should let per-interpreter environment variables override uv-derived defaults so unusual local layouts remain runnable without editing the script.

## Conversion behavior

These tests pin the XML shapes that matter most for interoperability, especially the modes that intentionally diverge from the default serializer.

### XPath format adds functions namespace

XPath mode should emit the W3C XPath functions namespace and typed child elements so downstream consumers receive standards-shaped XML.

### XPath format wraps root scalars

XPath mode should wrap root scalar payloads in a namespace-qualified map so the output remains a single well-formed XML document.

### Item-wrap false repeats parent tag

Disabling item wrapping should repeat the parent element name for primitive list items instead of producing nested `<item>` tags.

### Default xml namespaces stay empty

Calling `dicttoxml` without `xml_namespaces` should preserve the legacy root output and avoid adding namespace declarations or `xsi:` attributes implicitly.

### Explicit xml namespaces emit schema attributes

Supplying namespace prefixes and an `xsi` mapping should emit the expected `xmlns:*` declarations plus supported schema attributes without mutating the caller input.

### Xml namespace inputs are not mutated across calls

Reusing one `xml_namespaces` mapping across multiple `dicttoxml` calls should return identical XML each time so namespace declarations never accumulate on the shared dict.

### Falsy JSON values convert to XML

Falsy JSON values such as empty objects, empty arrays, zero, false, and empty strings should convert through the public API instead of being treated as missing data.

### Special attributes do not mutate input

Converting dictionaries that use `@attrs` and `@val` should preserve the caller's original data so objects can be reused safely.

### Special attributes accept coercible pairs

Attribute metadata that can be coerced with `dict()` should keep working so memory optimizations do not narrow legacy caller input.

### Invalid XML names normalize without double escaping

Invalid element names should fall back to `<key name="...">` with the original name escaped exactly once in the emitted attribute.

### Flat suffix never creates invalid XML tags

Keys ending in `@flat` should keep their flattening behavior where supported and must never leak the suffix into scalar or dict element names.

### Rust and Python XML name parity

The Rust accelerator and Python serializer should agree on supported XML name normalization cases so fast-path output does not drift silently.

### Invalid list item names preserve metadata

Generated list item names that are not valid XML should emit `<key>` elements with the original name preserved in a `name` attribute across scalar item types.

### Valid-name scalar helper formats dates

The scalar helper used after key validation should still ISO-format date values before assigning type metadata and serializing element text.

### Fast wrapper uses Rust for supported options

When the optional Rust callable is available and the selected options are Rust-backed, the fast wrapper should dispatch directly to that callable.

### Fast wrapper exposes backend metadata

Backend metadata helpers should report whether Rust is active and name the selected backend so callers can diagnose fallback behavior.

### Fast helper functions use Python fallback

Helper exports for XML escaping and CDATA wrapping should preserve Python behavior when Rust helper callables are unavailable.

### Backend selector detects Python-only payload markers

The backend selector should recognize nested `@attrs`, `@val`, and `@flat` markers so Rust is skipped before semantics drift.

### Backend selector fails loudly with no compatible backend

If every backend rejects a conversion request, the selector should raise a clear error instead of silently returning bad output.

### Json2xml uses fast backend selection

The public `Json2xml` wrapper should delegate through the fast backend selector so regular library and CLI conversions can use the Rust accelerator when installed.

### Special keys force Python fallback

Special dictionary keys such as `@attrs` and `@val` should bypass the Rust callable so the Python serializer can preserve legacy attribute semantics.

### Root scalars keep Python fallback

Root scalar payloads should bypass the Rust callable until the accelerator preserves the legacy Python `<item>` wrapper shape under the configured root element.

### Custom root names normalize before raw output

Invalid custom root names should use the serializer's existing XML-name normalization before raw bytes are returned so `pretty=False` cannot emit malformed root tags.

### Invalid custom attributes are rejected

Custom `@attrs` keys that are not valid XML attribute names should fail explicitly because attributes have no safe metadata fallback equivalent to element `<key name="...">` output.

## XML helper behavior

These tests pin low-level XML helper contracts so performance refactors keep the same serializer output and caller-side mutation behavior.

### Numeric fast path preserves general Number support

Common built-in numbers should avoid abstract-class dispatch while `Decimal`, `Fraction`, complex, and custom `Number` implementations remain supported.

### Exact-type dispatch preserves subclass fallbacks

Exact native JSON types should use direct hot paths while compatible numeric, string, dictionary, and sequence subclasses retain the established fallback behavior.

### Valid-name helpers preserve caller attrs

Helpers that receive prevalidated XML names should add type metadata only to the emitted element and must not mutate caller-owned attribute dictionaries.

### Container helpers preserve caller attrs

Dict and list element helpers should add container type metadata only to emitted XML and must not mutate caller-owned attribute dictionaries.

### Typed attributes preserve caller attrs

Valid-name scalar helpers should overwrite emitted type metadata while preserving caller attribute order and never mutating the input dictionary.

### XML name validity fast and cached paths

XML name validation should agree across the ASCII fast path, parser-backed path, and repeated cached calls so optimization does not change accepted names.

### XML attribute name validation

Attribute name validation should reject malformed custom attribute keys while preserving parser-accepted edge names such as underscores, hyphens, and xml-prefixed names.

### Rust invalid-name attrs escape once

Rust XML-name helpers should return raw invalid keys for later attribute escaping so borrowed-name optimizations cannot reintroduce double escaping.

### Rust XML escape scanner

Rust XML escaping should locate every escapable byte while allowing clean text spans to be copied in bulk, including UTF-8 text and all five XML substitutions.
