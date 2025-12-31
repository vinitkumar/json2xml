# json2xml Documentation

**json2xml** is a Python library that allows you to convert JSON data into XML format. It's simple, efficient, and easy to use.

## Quick Start

```python
from json2xml import json2xml
from json2xml.utils import readfromstring

data = readfromstring('{"name": "John", "age": 30}')
print(json2xml.Json2xml(data).to_xml())
```

## Features

- Conversion from a JSON string to XML
- Conversion from a JSON file to XML
- Conversion from an API that emits JSON data to XML
- XPath 3.1 compliant output format (optional)
- Customizable root element wrapper
- Optional type attributes on elements
- Configurable list item wrapping

## Documentation

For detailed documentation, visit [json2xml.readthedocs.io](https://json2xml.readthedocs.io).

## Source Code

The source code is available on [GitHub](https://github.com/vinitkumar/json2xml).
