# Architecture

This file documents the main execution paths that turn JSON input into XML output across the library, CLI, and optional Rust accelerator.

## Core pipeline

The standard pipeline reads JSON into Python objects, passes that data through [[json2xml/json2xml.py#Json2xml]], and delegates serialization to [[json2xml/dicttoxml.py#dicttoxml]].

Library callers usually construct [[json2xml/json2xml.py#Json2xml]] with a decoded `dict` or `list`. CLI callers reach the same conversion path through [[json2xml/cli.py#read_input]], which resolves the input source before creating the converter. Pretty output is produced by reparsing the generated XML so callers get indented text when requested.

## Conversion engine

The pure Python serializer recursively maps Python values to XML elements, attributes, and text while preserving the project-specific options around wrappers, list handling, and type metadata.

[[json2xml/dicttoxml.py#dicttoxml]] is the public serializer. It handles the XML declaration, root wrapper, namespace emission, XPath mode, and then routes nested values through helper functions such as [[json2xml/dicttoxml.py#convert]], [[json2xml/dicttoxml.py#convert_dict]], and [[json2xml/dicttoxml.py#convert_list]]. [[json2xml/dicttoxml.py#get_xml_type]] and [[json2xml/dicttoxml.py#convert]] accept broad caller input and classify unsupported values at runtime, so tests can probe failure paths without lying to the type checker. Invalid XML names are normalized by [[json2xml/dicttoxml.py#make_valid_xml_name]] instead of crashing immediately on user keys.

## Backend selection

The fast-path module prefers the Rust extension when it can preserve Python semantics, and falls back to the Python serializer for unsupported features.

[[json2xml/dicttoxml_fast.py#dicttoxml]] uses the Rust backend only when optional features such as `ids`, custom `item_func`, XML namespaces, XPath mode, or special `@` keys are not involved. A local stub for the optional `json2xml_rs` module keeps static analysis aligned with that fallback design, so type checking still passes when the extension is not installed. This keeps fast installs fast without letting the optimized path silently change behavior.

## CLI entrypoint

The CLI is a thin adapter that parses options, resolves one input source, and forwards those options into the same converter used by the library API.

[[json2xml/cli.py#create_parser]] defines the user-facing flags. [[json2xml/cli.py#read_input]] enforces the source priority rules, and [[json2xml/cli.py#main]] constructs [[json2xml/json2xml.py#Json2xml]] so command-line use and library use stay aligned.