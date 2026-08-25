# Behavior

This file captures the observable conversion and input rules that matter more than the implementation details hiding underneath.

## Input readers

The input helpers convert files, strings, URLs, and stdin into Python data structures while surfacing source-specific errors to callers.

[[json2xml/utils.py#readfromjson]] wraps file and JSON decoding failures in `JSONReadError`. [[json2xml/utils.py#readfromjsonl]] decodes each non-empty JSON Lines record into an ordered list and wraps filesystem, malformed-record, and invalid UTF-8 failures in the same error type. [[json2xml/utils.py#readfromjsonlstring]] splits text only at LF so leading blank lines remain countable and valid U+2028/U+2029 string content stays inside its record. [[json2xml/utils.py#readfromstring]] rejects non-string inputs and malformed JSON with `StringReadError`.

[[json2xml/utils.py#readfromurl]] lazily initializes the HTTP client, performs a bounded GET request, and raises `URLReadError` for hostname encoding, network, status, size, decoding, and JSON failures.

## Streaming JSONL conversion

JSONL command-line conversion keeps memory bounded to one source record and one serialized fragment instead of materializing the complete file.

[[json2xml/jsonl.py#stream_jsonl_to_xml]] skips blank lines, preserves physical line numbers in parse and conversion errors, validates each record independently through [[json2xml/json2xml.py#Json2xml]], and writes each fragment before requesting the next line. The standard root is opened and closed once around all fragments.

Supported root, wrapper, type, item-wrap, CDATA, and invalid-character options match regular list conversion. Pretty, XPath, and list-header modes fail before output because their whole-document layouts are not implemented for this stream. Stdout may contain a partial document after a late failure.

For `-o`, [[json2xml/cli.py#CLIApplication#stream_jsonl]] writes to a temporary file beside the destination and calls `os.replace` only after the stream succeeds. Failed conversions remove the temporary file and preserve any prior destination. Invalid UTF-8 is wrapped as `JSONReadError`, so the CLI reports it through the JSON-file parse path.

## URL security boundaries

Remote JSON reads default to public, credential-free HTTP(S) targets and bounded decoded responses so callers do not accidentally expose internal services or unlimited memory.

[[json2xml/utils.py#readfromurl]] disables redirects, rejects non-global resolved addresses, and pins each public request to a validated address while retaining the original Host header and TLS hostname. It incrementally decodes gzip and deflate bodies with 10 MiB encoded and decoded limits, honors valid `Content-Length` values, and rejects unsupported encodings. Trusted library callers can opt into private-network access only with an actual boolean while retaining the response limits.

## User examples

The public examples favor realistic API, file, and stdin flows with compact before-and-after output that can be checked against the real converter.

README and docs examples use `pretty=False` for scan-friendly output and avoid hidden fixtures. They cover Python API conversion, local JSON and JSONL exports, and shell pipelines so users can choose the right entry point quickly.

## Conversion output

Default output includes an XML declaration, wraps content in `all`, stays compact, and annotates elements with their source type unless callers change those features.

[[json2xml/json2xml.py#Json2xml#to_xml]] calls [[json2xml/dicttoxml_fast.py#dicttoxml]] with the configured wrapper, root, `attr_type`, `item_wrap`, `cdata`, and `list_headers` options. It treats only `None` as absent input, so falsy JSON values still serialize. Compact output is the safe default and returns the serializer's UTF-8 bytes directly; explicit pretty output requests an indent unit from the same serializer call and is decoded to Unicode text. When `item_wrap=False`, list values repeat the parent tag instead of creating `<item>` children.

The fast backend selector falls back to the pure Python serializer for root scalar payloads so values like `0`, `false`, and `""` keep the historical `<item>` element inside the configured root wrapper.

The Rust fast path in [[rust/src/lib.rs#write_dict_contents]] and [[rust/src/lib.rs#write_convert_list]] mirrors those Python list-wrapper rules. `list_headers=True` suppresses the outer list container and repeats the parent tag only for nested dict items, while primitive items still use the same scalar tags that Python emits.

## XPath 3.1 format

XPath mode swaps the project-specific XML shape for the W3C `json-to-xml` mapping with typed element names and the XPath functions namespace.

When `xpath_format=True`, [[json2xml/dicttoxml.py#dicttoxml]] delegates payload conversion to [[json2xml/dicttoxml.py#convert_to_xpath31]] and emits the `http://www.w3.org/2005/xpath-functions` namespace on the root `map` or `array` element. Scalars become `string`, `number`, `boolean`, or `null` elements, and object keys move into `key` attributes.

## Invalid XML payloads

Opt-in pretty printing indents during serialization, so no generated XML is ever parsed back.

[[json2xml/json2xml.py#Json2xml#to_xml]] rejects excessive depth and item counts before conversion, then passes an indent unit to the serializer when pretty output is requested. Compact and pretty output are both bounded as UTF-8 bytes are emitted, and indentation is counted in that budget because the writer emits it. Because the library never reads XML back, malformed markup, DTDs, and entities have no formatter to reach.

## Generated documents are well formed

Every option combination emits markup an XML 1.0 parser accepts.

Element names are normalized wherever one is written, including the parent name a dictionary borrows under `list_headers`. A rootless document has no parent name to borrow, so that member falls back to `key` and carries the empty original as metadata, exactly as a scalar in the same position already does. Namespace prefixes are out of scope: a key such as `k:v` is emitted verbatim and binding its prefix is the caller's responsibility.

## XML output safety

Every serializer mode rejects XML 1.0-forbidden characters by default and treats namespace metadata as attributes so raw output cannot bypass well-formedness or escaping checks.

[[json2xml/xml_chars.py#is_xml10_char]] is the shared XML 1.0 predicate used by [[json2xml/dicttoxml.py#escape_xml]] and CDATA writers. CLI callers may explicitly select replace, visible `\\uXXXX` escape, or removal through [[json2xml/xml_chars.py#transform_json_xml_chars]]; replacement transforms values and keys without recursion and rejects key collisions. Namespace prefixes are validated, while namespace and custom attribute values use the shared XML escaping path.
