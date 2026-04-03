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

## Conversion behavior

These tests pin the XML shapes that matter most for interoperability, especially the modes that intentionally diverge from the default serializer.

### XPath format adds functions namespace

XPath mode should emit the W3C XPath functions namespace and typed child elements so downstream consumers receive standards-shaped XML.

### Item-wrap false repeats parent tag

Disabling item wrapping should repeat the parent element name for primitive list items instead of producing nested `<item>` tags.