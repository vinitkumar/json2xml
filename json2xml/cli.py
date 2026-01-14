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
from typing import Any

from json2xml import __version__
from json2xml.json2xml import Json2xml
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


def read_input(args: argparse.Namespace) -> dict[str, Any] | list[Any]:
    """
    Read JSON input from the specified source.

    Priority: URL > String > File > Stdin

    Args:
        args: Parsed command line arguments.

    Returns:
        Parsed JSON data as dict or list.

    Raises:
        SystemExit: When no input is provided or reading fails.
    """
    # Priority: URL > String > File > Stdin
    if args.url:
        try:
            return readfromurl(args.url)
        except URLReadError as e:
            print(f"Error reading from URL: {e}", file=sys.stderr)
            sys.exit(1)

    if args.string:
        try:
            return readfromstring(args.string)
        except StringReadError as e:
            print(f"Error parsing JSON string: {e}", file=sys.stderr)
            sys.exit(1)

    if args.input_file:
        if args.input_file == "-":
            # Read from stdin
            return read_from_stdin()
        try:
            return readfromjson(args.input_file)
        except JSONReadError as e:
            print(f"Error reading JSON file: {e}", file=sys.stderr)
            sys.exit(1)

    # Check if there's data on stdin
    if not sys.stdin.isatty():
        return read_from_stdin()

    print("Error: No input provided. Use -h for help.", file=sys.stderr)
    sys.exit(1)


def read_from_stdin() -> dict[str, Any] | list[Any]:
    """
    Read JSON from standard input.

    Returns:
        Parsed JSON data.

    Raises:
        SystemExit: When stdin is empty or contains invalid JSON.
    """
    try:
        json_str = sys.stdin.read().strip()
        if not json_str:
            print("Error: Empty input", file=sys.stderr)
            sys.exit(1)
        return readfromstring(json_str)
    except StringReadError as e:
        print(f"Error parsing JSON from stdin: {e}", file=sys.stderr)
        sys.exit(1)


def write_output(output: str | bytes, output_file: str | None) -> None:
    """
    Write XML output to the specified destination.

    Args:
        output: XML content to write.
        output_file: Path to output file, or None for stdout.
    """
    if isinstance(output, bytes):
        output = output.decode("utf-8")

    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output)
        except OSError as e:
            print(f"Error writing to file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Read input data
    try:
        data = read_input(args)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        return 1

    # Convert to XML
    try:
        converter = Json2xml(
            data=data,
            wrapper=args.wrapper,
            root=args.root,
            pretty=args.pretty,
            attr_type=args.attr_type,
            item_wrap=args.item_wrap,
            xpath_format=args.xpath_format,
            cdata=args.cdata,
            list_headers=args.list_headers,
        )
        xml_output = converter.to_xml()

        if xml_output is None:
            print("Error: Empty data, no XML generated", file=sys.stderr)
            return 1

        write_output(xml_output, args.output)

    except Exception as e:
        print(f"Error converting to XML: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
