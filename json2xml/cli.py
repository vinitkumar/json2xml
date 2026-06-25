#!/usr/bin/env python3
"""
json2xml-py - Command-line tool to convert JSON data to XML format.

Usage:
    json2xml-py [flags] [input-file]

Flags:
    -w, --wrapper string    Wrapper element name (default "all")
    -r, --root              Include root element (default true)
    -p, --pretty            Pretty print output (default true)
    -t, --type              Include type attributes (default true)
    -i, --item-wrap         Wrap list items in <item> elements (default true)
    -x, --xpath             Use XPath 3.1 json-to-xml format
    -o, --output string     Output file (default: stdout)
    -u, --url string        Read JSON from URL
    -s, --string string     Read JSON from string
    -c, --cdata             Wrap string values in CDATA sections
    -l, --list-headers      Repeat headers for each list item
    -h, --help              Show help message
    -v, --version           Show version information

Examples:
    # Convert a JSON file to XML
    json2xml-py data.json

    # Convert with custom wrapper
    json2xml-py -w root data.json

    # Read from URL
    json2xml-py -u https://api.example.com/data.json

    # Read from string
    json2xml-py -s '{"name": "John", "age": 30}'

    # Output to file
    json2xml-py -o output.xml data.json

    # Use XPath 3.1 format
    json2xml-py -x data.json
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from json2xml import __version__
from json2xml.json2xml import Json2xml
from json2xml.types import JSONValue
from json2xml.utils import (
    JSONReadError,
    StringReadError,
    URLReadError,
    readfromjson,
    readfromstring,
    readfromurl,
)

AUTHOR = "Vinit Kumar"
EMAIL = "mail@vinitkumar.me"


@dataclass(frozen=True, slots=True)
class CLIConversionOptions:
    """Parsed CLI options normalized for the conversion workflow."""

    input_file: str | None
    url: str | None
    string: str | None
    output: str | None
    wrapper: str
    root: bool
    pretty: bool
    attr_type: bool
    item_wrap: bool
    xpath_format: bool
    cdata: bool
    list_headers: bool

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "CLIConversionOptions":
        return cls(
            input_file=args.input_file,
            url=args.url,
            string=args.string,
            output=args.output,
            wrapper=args.wrapper,
            root=args.root,
            pretty=args.pretty,
            attr_type=args.attr_type,
            item_wrap=args.item_wrap,
            xpath_format=args.xpath_format,
            cdata=args.cdata,
            list_headers=args.list_headers,
        )


def exit_with_error(message: str) -> NoReturn:
    """Print an error message and terminate CLI processing."""
    print(message, file=sys.stderr)
    raise SystemExit(1)


class CLIApplication:
    """Thin command adapter around input resolution, conversion, and output."""

    def read_input(self, options: CLIConversionOptions) -> JSONValue:
        if options.url:
            try:
                return readfromurl(options.url)
            except URLReadError as error:
                exit_with_error(f"Error reading from URL: {error}")

        if options.string:
            try:
                return readfromstring(options.string)
            except StringReadError as error:
                exit_with_error(
                    "Error: Invalid JSON in --string input. "
                    "Pass a valid JSON object, array, string, number, boolean, or null. "
                    f"({error})"
                )

        if options.input_file:
            if options.input_file == "-":
                return read_from_stdin()
            if not Path(options.input_file).is_file():
                exit_with_error(
                    f"Error: JSON file not found: {options.input_file}. "
                    "Check the path or use - to read JSON from stdin."
                )
            try:
                return readfromjson(options.input_file)
            except JSONReadError as error:
                exit_with_error(
                    f"Error: Could not parse JSON file: {options.input_file}. "
                    f"Check that the file contains valid JSON. ({error})"
                )

        if not sys.stdin.isatty():
            return read_from_stdin()

        exit_with_error(
            "Error: No input provided. Pass a JSON file, use - for stdin, "
            "or provide --string/--url."
        )

    def read_from_stdin(self) -> JSONValue:
        try:
            json_str = sys.stdin.read().strip()
            if not json_str:
                exit_with_error(
                    "Error: Empty stdin. Pipe JSON into stdin or pass a file/--string."
                )
            return readfromstring(json_str)
        except StringReadError as error:
            exit_with_error(
                "Error: Invalid JSON from stdin. Pipe valid JSON into stdin "
                f"or pass a file/--string. ({error})"
            )

    def convert(self, data: JSONValue, options: CLIConversionOptions) -> str | bytes:
        converter = Json2xml(
            data=data,
            wrapper=options.wrapper,
            root=options.root,
            pretty=options.pretty,
            attr_type=options.attr_type,
            item_wrap=options.item_wrap,
            xpath_format=options.xpath_format,
            cdata=options.cdata,
            list_headers=options.list_headers,
        )
        xml_output = converter.to_xml()
        if xml_output is None:
            raise ValueError("Empty data, no XML generated")
        return xml_output

    def write_output(self, output: str | bytes, output_file: str | None) -> None:
        if isinstance(output, bytes):
            output = output.decode("utf-8")

        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as file_obj:
                    file_obj.write(output)
            except OSError as error:
                print(f"Error writing to file: {error}", file=sys.stderr)
                sys.exit(1)
            return

        print(output)


_APP = CLIApplication()


# @lat: [[architecture#CLI entrypoint]]
def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="json2xml-py",
        description="Convert JSON to XML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Convert a JSON file to XML
  json2xml-py data.json

  # Convert with custom wrapper
  json2xml-py -w root data.json

  # Read from URL
  json2xml-py -u https://api.example.com/data.json

  # Read from string
  json2xml-py -s '{"name": "John", "age": 30}'

  # Read from stdin
  cat data.json | json2xml-py -

  # Output to file
  json2xml-py -o output.xml data.json

  # Use XPath 3.1 format
  json2xml-py -x data.json

  # Disable pretty printing and type attributes
  json2xml-py --no-pretty --no-type data.json
""",
    )

    # Input options
    input_group = parser.add_argument_group("Input Options")
    input_group.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help="Read JSON from file (use - for stdin)",
    )
    input_group.add_argument(
        "-u",
        "--url",
        dest="url",
        default=None,
        help="Read JSON from URL",
    )
    input_group.add_argument(
        "-s",
        "--string",
        dest="string",
        default=None,
        help="Read JSON from string",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "-o",
        "--output",
        dest="output",
        default=None,
        help="Output file (default: stdout)",
    )

    # Conversion options
    conv_group = parser.add_argument_group("Conversion Options")
    conv_group.add_argument(
        "-w",
        "--wrapper",
        dest="wrapper",
        default="all",
        help='Wrapper element name (default: "all")',
    )
    conv_group.add_argument(
        "-r",
        "--root",
        dest="root",
        action="store_true",
        default=True,
        help="Include root element (default: true)",
    )
    conv_group.add_argument(
        "--no-root",
        dest="root",
        action="store_false",
        help="Exclude root element",
    )
    conv_group.add_argument(
        "-p",
        "--pretty",
        dest="pretty",
        action="store_true",
        default=True,
        help="Pretty print output (default: true)",
    )
    conv_group.add_argument(
        "--no-pretty",
        dest="pretty",
        action="store_false",
        help="Disable pretty printing",
    )
    conv_group.add_argument(
        "-t",
        "--type",
        dest="attr_type",
        action="store_true",
        default=True,
        help="Include type attributes (default: true)",
    )
    conv_group.add_argument(
        "--no-type",
        dest="attr_type",
        action="store_false",
        help="Exclude type attributes",
    )
    conv_group.add_argument(
        "-i",
        "--item-wrap",
        dest="item_wrap",
        action="store_true",
        default=True,
        help="Wrap list items in <item> elements (default: true)",
    )
    conv_group.add_argument(
        "--no-item-wrap",
        dest="item_wrap",
        action="store_false",
        help="Don't wrap list items",
    )
    conv_group.add_argument(
        "-x",
        "--xpath",
        dest="xpath_format",
        action="store_true",
        default=False,
        help="Use XPath 3.1 json-to-xml format",
    )
    conv_group.add_argument(
        "-c",
        "--cdata",
        dest="cdata",
        action="store_true",
        default=False,
        help="Wrap string values in CDATA sections",
    )
    conv_group.add_argument(
        "-l",
        "--list-headers",
        dest="list_headers",
        action="store_true",
        default=False,
        help="Repeat headers for each list item",
    )

    # Other options
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"json2xml-py version {__version__}\nAuthor: {AUTHOR} <{EMAIL}>",
    )

    return parser


# @lat: [[behavior#Input readers]]
def read_input(args: argparse.Namespace) -> JSONValue:
    """Read JSON input from the specified source."""
    return _APP.read_input(CLIConversionOptions.from_namespace(args))


def read_from_stdin() -> JSONValue:
    """Read JSON from standard input."""
    return _APP.read_from_stdin()


def write_output(output: str | bytes, output_file: str | None) -> None:
    """Write XML output to the specified destination."""
    _APP.write_output(output, output_file)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        data = read_input(args)
    except Exception as error:
        print(f"Error reading input: {error}", file=sys.stderr)
        return 1

    try:
        options = CLIConversionOptions.from_namespace(args)
        xml_output = _APP.convert(data, options)
        write_output(xml_output, options.output)
    except Exception as error:
        print(f"Error converting to XML: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
