"""Bounded-memory JSON Lines to XML conversion."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from .dicttoxml import make_attrstring, make_valid_xml_name
from .json2xml import Json2xml
from .utils import InvalidDataError, JSONReadError
from .xml_chars import InvalidXMLPolicy, transform_json_xml_chars

XML_DECLARATION = b'<?xml version="1.0" encoding="UTF-8" ?>'


class ByteWriter(Protocol):
    """Destination that accepts serialized XML bytes."""

    def write(self, data: bytes, /) -> Any:
        """Write bytes to the destination."""
        ...


@dataclass(frozen=True, slots=True)
class JsonlConversionOptions:
    """Options supported by record-at-a-time JSONL conversion."""

    wrapper: str = "all"
    root: bool = True
    attr_type: bool = True
    item_wrap: bool = True
    cdata: bool = False
    invalid_xml_policy: InvalidXMLPolicy = InvalidXMLPolicy.REJECT


def stream_jsonl_to_xml(
    lines: Iterable[str],
    destination: ByteWriter,
    options: JsonlConversionOptions = JsonlConversionOptions(),
) -> int:
    """Convert JSON Lines into one XML stream and return the record count.

    Blank lines are skipped. Malformed records raise `JSONReadError` with the
    physical line number after any earlier records have already been written.
    """
    root_name = ""
    if options.root:
        root_name, root_attrs = make_valid_xml_name(options.wrapper, {})
        destination.write(XML_DECLARATION)
        destination.write(
            f"<{root_name}{make_attrstring(root_attrs)}>".encode("utf-8")
        )

    record_count = 0
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise JSONReadError(f"Invalid JSONL at line {line_number}") from error

        try:
            transformed_record = transform_json_xml_chars(
                record, options.invalid_xml_policy
            )
            fragment = Json2xml(
                [transformed_record],
                root=False,
                attr_type=options.attr_type,
                item_wrap=options.item_wrap,
                cdata=options.cdata,
            ).to_xml()
        except InvalidDataError as error:
            raise InvalidDataError(
                f"Error converting JSONL line {line_number}: {error}"
            ) from error
        assert isinstance(fragment, bytes)
        destination.write(fragment)
        record_count += 1

    if options.root:
        destination.write(f"</{root_name}>".encode("utf-8"))
    return record_count
