#!/usr/bin/env python3
"""
json2xml-py - Command-line tool to convert JSON data to XML format.

Usage:
    json2xml-py [flags] [input-file]

Flags:
    -w, --wrapper string    Wrapper element name (default "all")
    -r, --root              Include root element (default true)
    -p, --pretty            Pretty print output (default false)
    -t, --type              Include type attributes (default true)
    -i, --item-wrap         Wrap list items in <item> elements (default true)
    -x, --xpath             Use XPath 3.1 json-to-xml format
    -o, --output string     Output file (default: stdout)
    -u, --url string        Read JSON from URL
    -s, --string string     Read JSON from string
    --jsonl                 Force JSON Lines framing for the input
    --no-jsonl              Force whole-document JSON framing for the input
    -c, --cdata             Wrap string values in CDATA sections
    -l, --list-headers      Repeat headers for each list item
    --invalid-xml-chars     Handle XML 1.0-forbidden characters
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

    # Convert a JSON Lines file (.jsonl and .ndjson are detected)
    json2xml-py records.jsonl

    # Read JSON Lines from stdin
    cat records.jsonl | json2xml-py --jsonl -

    # Read a whole JSON document despite the .jsonl name
    json2xml-py --no-jsonl records.jsonl

    # Replace characters forbidden by XML 1.0
    json2xml-py --invalid-xml-chars replace data.json

    # Output to file
    json2xml-py -o output.xml data.json

    # Use XPath 3.1 format
    json2xml-py -x data.json
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, BinaryIO, NoReturn, TextIO

from json2xml import __version__
from json2xml.json2xml import Json2xml
from json2xml.jsonl import JsonlConversionOptions, stream_jsonl_to_xml
from json2xml.types import JSONValue
from json2xml.utils import (
    JSON_FILE_ENCODING,
    LINE_SEPARATOR,
    JSONReadError,
    StringReadError,
    URLReadError,
    readfromjson,
    readfromjsonl,
    readfromjsonlstring,
    readfromstring,
    readfromurl,
    strip_byte_order_mark,
)
from json2xml.xml_chars import InvalidXMLPolicy, transform_json_xml_chars

AUTHOR = "Vinit Kumar"
EMAIL = "mail@vinitkumar.me"
JSONL_SUFFIXES = (".jsonl", ".ndjson")
DEFAULT_FILE_PERMISSIONS = 0o666


class InputFormat(Enum):
    """Framing of the selected input source."""

    JSON = "json"
    JSONL = "jsonl"


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
    jsonl: bool | None = None
    invalid_xml_policy: InvalidXMLPolicy = InvalidXMLPolicy.REJECT

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> CLIConversionOptions:
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
            jsonl=vars(args).get("jsonl"),
            invalid_xml_policy=vars(args).get(
                "invalid_xml_policy", InvalidXMLPolicy.REJECT
            ),
        )


def invalid_xml_policy(value: str) -> InvalidXMLPolicy:
    """Convert the flag text to a policy, naming the valid choices on failure."""
    try:
        return InvalidXMLPolicy(value)
    except ValueError:
        choices = ", ".join(str(policy) for policy in InvalidXMLPolicy)
        raise argparse.ArgumentTypeError(
            f"invalid choice: '{value}' (choose from {choices})"
        ) from None


def exit_with_error(message: str) -> NoReturn:
    """Print an error message and terminate CLI processing."""
    print(message, file=sys.stderr)
    raise SystemExit(1)


def needs_whole_document(options: CLIConversionOptions) -> bool:
    """Return whether the requested layout needs every record materialized."""
    return options.pretty or options.xpath_format or options.list_headers


def output_file_mode(output_path: Path) -> int:
    """Return the mode a plain `open()` would leave on the destination."""
    try:
        return stat.S_IMODE(output_path.stat().st_mode)
    except OSError:
        umask = os.umask(0)
        os.umask(umask)
        return DEFAULT_FILE_PERMISSIONS & ~umask


class CLIApplication:
    """Thin command adapter around input resolution, conversion, and output."""

    def _resolve_input_format(self, options: CLIConversionOptions) -> InputFormat:
        """Return the framing of the selected source, honoring an explicit flag."""
        if options.jsonl is not None:
            return InputFormat.JSONL if options.jsonl else InputFormat.JSON
        if options.input_file and options.input_file != "-":
            if Path(options.input_file).suffix.lower() in JSONL_SUFFIXES:
                return InputFormat.JSONL
        return InputFormat.JSON

    def uses_jsonl_stream(self, options: CLIConversionOptions) -> bool:
        """Return whether the selected source can convert one record at a time."""
        if options.url or options.string:
            return False
        if self._resolve_input_format(options) is not InputFormat.JSONL:
            return False
        return not needs_whole_document(options)

    def stream_jsonl(self, options: CLIConversionOptions) -> None:
        """Stream the selected JSONL source to stdout or an atomic output file."""
        stream_options = JsonlConversionOptions(
            wrapper=options.wrapper,
            root=options.root,
            attr_type=options.attr_type,
            item_wrap=options.item_wrap,
            cdata=options.cdata,
            invalid_xml_policy=options.invalid_xml_policy,
        )
        if options.input_file and options.input_file != "-":
            self._require_existing_file(options.input_file)
            try:
                source = open(
                    options.input_file,
                    encoding=JSON_FILE_ENCODING,
                    newline=LINE_SEPARATOR,
                )
            except OSError as error:
                raise JSONReadError(
                    f"Could not read JSONL file: {options.input_file}"
                ) from error
            with source:
                try:
                    self._write_jsonl(source, options.output, stream_options)
                except UnicodeDecodeError as error:
                    raise JSONReadError("Invalid JSONL File") from error
            return

        self._write_jsonl(sys.stdin, options.output, stream_options)

    def _write_jsonl(
        self,
        source: TextIO,
        output_file: str | None,
        options: JsonlConversionOptions,
    ) -> None:
        if output_file is None:
            destination = self._stdout_buffer()
            stream_jsonl_to_xml(source, destination, options)
            destination.write(b"\n")
            return

        output_path = Path(output_file)
        # Resolve the final mode first: NamedTemporaryFile creates 0600, which
        # os.replace would otherwise carry onto the destination.
        file_mode = output_file_mode(output_path)
        temporary_path: Path | None = None
        try:
            with self._temporary_output(output_path) as destination:
                temporary_path = Path(destination.name)
                stream_jsonl_to_xml(source, destination, options)
            os.chmod(temporary_path, file_mode)
            os.replace(temporary_path, output_path)
        except BaseException:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _temporary_output(output_path: Path) -> IO[bytes]:
        """Open a sibling temporary file, naming the destination on failure."""
        try:
            return NamedTemporaryFile(
                mode="wb",
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                delete=False,
            )
        except OSError as error:
            raise OSError(f"{output_path}: {error.strerror}") from error

    @staticmethod
    def _require_existing_file(input_file: str) -> None:
        """Exit when the selected input file does not exist."""
        if Path(input_file).is_file():
            return
        exit_with_error(
            f"Error: JSON file not found: {input_file}. "
            "Check the path or use - to read JSON from stdin."
        )

    @staticmethod
    def _stdout_buffer() -> BinaryIO:
        destination = getattr(sys.stdout, "buffer", None)
        if destination is None:
            raise OSError("Binary stdout is unavailable")
        return destination

    def read_input(self, options: CLIConversionOptions) -> JSONValue:
        if options.url:
            try:
                return readfromurl(options.url)
            except URLReadError as error:
                exit_with_error(f"Error reading from URL: {error}")

        if options.string:
            if self._resolve_input_format(options) is InputFormat.JSONL:
                try:
                    return readfromjsonlstring(options.string)
                except JSONReadError as error:
                    exit_with_error(
                        f"Error: Invalid JSON Lines in --string input. ({error})"
                    )
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
                if self._resolve_input_format(options) is InputFormat.JSONL:
                    return self.read_from_stdin(InputFormat.JSONL)
                return read_from_stdin()
            self._require_existing_file(options.input_file)
            try:
                if self._resolve_input_format(options) is InputFormat.JSONL:
                    return readfromjsonl(options.input_file)
                return readfromjson(options.input_file)
            except JSONReadError as error:
                exit_with_error(
                    f"Error: Could not parse JSON file: {options.input_file}. "
                    f"Check that the file contains valid JSON. ({error})"
                )

        if not sys.stdin.isatty():
            if self._resolve_input_format(options) is InputFormat.JSONL:
                return self.read_from_stdin(InputFormat.JSONL)
            return read_from_stdin()

        exit_with_error(
            "Error: No input provided. Pass a JSON file, use - for stdin, or provide --string/--url."
        )
        raise AssertionError("unreachable")

    def read_from_stdin(
        self, input_format: InputFormat = InputFormat.JSON
    ) -> JSONValue:
        json_str = strip_byte_order_mark(sys.stdin.read())
        if not json_str.strip():
            exit_with_error(
                "Error: Empty stdin. Pipe JSON into stdin or pass a file/--string."
            )

        if input_format is InputFormat.JSONL:
            try:
                return readfromjsonlstring(json_str)
            except JSONReadError as error:
                exit_with_error(f"Error: Invalid JSONL from stdin. ({error})")

        try:
            return readfromstring(json_str)
        except StringReadError as error:
            exit_with_error(
                f"Error: Invalid JSON from stdin. Pipe valid JSON into stdin or pass a file/--string. ({error})"
            )

    def convert(self, data: JSONValue, options: CLIConversionOptions) -> str | bytes:
        transformed_data = transform_json_xml_chars(data, options.invalid_xml_policy)
        converter = Json2xml(
            data=transformed_data,
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

  # Convert a JSON Lines file (.jsonl and .ndjson are detected)
  json2xml-py records.jsonl

  # Read JSON Lines from stdin
  cat records.jsonl | json2xml-py --jsonl -

  # Read a whole JSON document despite the .jsonl name
  json2xml-py --no-jsonl records.jsonl

  # Replace characters forbidden by XML 1.0
  json2xml-py --invalid-xml-chars replace data.json

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
        help="Read JSON, or stream .jsonl/.ndjson, from file (use - for stdin)",
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
    input_group.add_argument(
        "--jsonl",
        dest="jsonl",
        action="store_true",
        default=None,
        help="Force JSON Lines framing (.jsonl and .ndjson files are detected automatically)",
    )
    input_group.add_argument(
        "--no-jsonl",
        dest="jsonl",
        action="store_false",
        help="Force whole-document JSON framing for a .jsonl or .ndjson file",
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
        default=False,
        help="Pretty print output (default: false)",
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
    conv_group.add_argument(
        "--invalid-xml-chars",
        dest="invalid_xml_policy",
        type=invalid_xml_policy,
        choices=tuple(InvalidXMLPolicy),
        default=InvalidXMLPolicy.REJECT,
        metavar="{reject,replace,escape,remove}",
        help="Handle characters forbidden by XML 1.0 (default: reject)",
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
def read_input(args: argparse.Namespace | CLIConversionOptions) -> JSONValue:
    """Read JSON input from the specified source."""
    options = (
        args
        if isinstance(args, CLIConversionOptions)
        else CLIConversionOptions.from_namespace(args)
    )
    return _APP.read_input(options)


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
    if args.jsonl and args.url:
        parser.error("--jsonl cannot be combined with --url")
    options = CLIConversionOptions.from_namespace(args)

    if _APP.uses_jsonl_stream(options):
        try:
            _APP.stream_jsonl(options)
        except JSONReadError as error:
            if options.input_file and options.input_file != "-":
                print(
                    f"Error: Could not parse JSON file: {options.input_file}. "
                    f"Check that the file contains valid JSON. ({error})",
                    file=sys.stderr,
                )
            else:
                print(f"Error: Invalid JSONL from stdin. ({error})", file=sys.stderr)
            return 1
        except OSError as error:
            print(f"Error writing to file: {error}", file=sys.stderr)
            return 1
        except Exception as error:
            print(f"Error converting to XML: {error}", file=sys.stderr)
            return 1
        return 0

    try:
        data = read_input(options)
    except Exception as error:
        print(f"Error reading input: {error}", file=sys.stderr)
        return 1

    try:
        xml_output = _APP.convert(data, options)
        write_output(xml_output, options.output)
    except Exception as error:
        print(f"Error converting to XML: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
