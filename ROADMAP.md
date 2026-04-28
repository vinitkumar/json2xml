# json2xml Roadmap

json2xml is a small, practical JSON-to-XML toolkit for Python users, CLI workflows, and performance experiments across native implementations.

This roadmap keeps the project direction visible for users and contributors.

## Current Focus

- Make the README and examples easier for new users to scan.
- Keep the Python API stable while improving typed, tested behavior.
- Maintain the Rust acceleration path as the fastest option for Python callers.
- Keep Python, Rust, Go, and Zig benchmark results reproducible.

## Near-Term Work

### Documentation and Examples

- Add examples for converting API responses, local files, stdin, and string payloads.
- Document the differences between pure Python, Rust extension, Go CLI, and Zig CLI usage.
- Add a short "choose the right implementation" guide.
- Expand troubleshooting docs for installation and native wheel fallback.

### CLI Experience

- Improve error messages for invalid JSON, missing input, and unsupported option combinations.
- Add more CLI examples for shell pipelines and output files.
- Confirm behavior is consistent across macOS, Linux, and Windows.

### Performance and Benchmarks

- Keep `BENCHMARKS.md` updated when benchmark scripts or implementation details change.
- Add benchmark notes that explain process startup overhead for CLI tools.
- Add larger input fixtures that reflect real integration workloads.
- Make it easy for contributors to reproduce benchmark runs locally.

### Rust Extension

- Continue improving fallback behavior when native support is unavailable.
- Add tests for unsupported or partially supported conversion features.
- Keep PyO3 and packaging configuration current.
- Verify wheels across supported Python and platform versions.

## Good First Issues

These are intentionally small and useful:

- Add one new README example for a real-world JSON shape.
- Add a regression test for a documented conversion option.
- Improve one CLI help message or error case.
- Add a short benchmark reproduction note.
- Clarify one section of `CONTRIBUTING.rst`.

## Larger Ideas

- Streaming support for very large JSON inputs.
- More explicit XML namespace handling examples.
- Better comparison docs against adjacent JSON-to-XML tools.
- A small gallery of before/after JSON and XML examples.

If you want to help, open an issue with a focused proposal or pick an existing issue labeled `good first issue`, `help wanted`, `docs`, `cli`, or `performance`.
