# json2xml_rs - Rust Extension for json2xml

A high-performance Rust implementation of the dicttoxml module using PyO3.

## Building

### Prerequisites

- Rust (1.70+)
- Python (3.9+)
- maturin (`pip install maturin`)

### Development Build

```bash
cd rust
maturin develop --release
```

This builds the extension and installs it in your current Python environment.

### Production Build

```bash
cd rust
maturin build --release
```

The wheel will be in `target/wheels/`.

## Usage

```python
# Direct usage
from json2xml_rs import dicttoxml

data = {"name": "John", "age": 30, "active": True}
xml_bytes = dicttoxml(data)
print(xml_bytes.decode())

# Or use the hybrid module that auto-selects the fastest backend
from json2xml import dicttoxml_fast
xml_bytes = dicttoxml_fast.dicttoxml(data)
```

## API

### `dicttoxml(obj, root=True, custom_root="root", attr_type=True, item_wrap=True, cdata=False, list_headers=False) -> bytes`

Convert a Python dict or list to XML.

**Parameters:**
- `obj`: The Python object to convert (dict or list)
- `root`: Include XML declaration and root element (default: True)
- `custom_root`: Name of the root element (default: "root")
- `attr_type`: Include type attributes on elements (default: True)
- `item_wrap`: Wrap list items in `<item>` tags (default: True)
- `cdata`: Wrap string values in CDATA sections (default: False)
- `list_headers`: Repeat parent tag for each list item (default: False)

**Returns:** UTF-8 encoded XML as bytes

### `escape_xml_py(s: str) -> str`

Escape special XML characters (&, ", ', <, >) in a string.

### `wrap_cdata_py(s: str) -> str`

Wrap a string in a CDATA section.

## Performance

The Rust implementation is expected to be 5-15x faster than pure Python for:

- String escaping (single-pass vs. multiple `.replace()` calls)
- Type dispatch (compiled match statements vs. `isinstance()` chains)
- String building (pre-allocated buffers vs. f-string concatenation)

## Limitations

The Rust implementation currently does not support:

- `ids` parameter (unique IDs for elements)
- `item_func` parameter (custom item naming function)
- `xml_namespaces` parameter
- `xpath_format` parameter
- `@attrs`, `@val`, `@flat` special dict keys

For these features, fall back to the pure Python implementation.

## Development

### Running Tests

```bash
cd rust
maturin develop
python -m pytest ../tests/
```

### Benchmarking

```bash
cd ..
python benchmark_rust.py
```
