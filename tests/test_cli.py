"""Tests for the json2xml CLI."""
from __future__ import annotations

import io
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from json2xml.cli import create_parser, main, read_from_stdin, read_input, write_output

if TYPE_CHECKING:
    from pytest import CaptureFixture


class TestCLI:
    """Test cases for the CLI module."""

    def test_help_flag(self) -> None:
        """Test --help flag shows usage information."""
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "json2xml-py" in result.stdout
        assert "Convert JSON to XML" in result.stdout

    def test_version_flag(self) -> None:
        """Test --version flag shows version information."""
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "json2xml-py version" in result.stdout
        assert "Vinit Kumar" in result.stdout

    def test_string_input(self) -> None:
        """Test -s/--string flag for inline JSON."""
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "-s", '{"name": "John"}'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<name" in result.stdout
        assert "John" in result.stdout

    def test_file_input(self) -> None:
        """Test file input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "test.json"
            json_file.write_text('{"key": "value"}')

            result = subprocess.run(
                [sys.executable, "-m", "json2xml.cli", str(json_file)],
                capture_output=True,
                text=True,
            )

        assert result.returncode == 0
        assert "<key" in result.stdout
        assert "value" in result.stdout

    def test_output_file(self) -> None:
        """Test -o/--output flag for file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.xml"

            result = subprocess.run(
                [
                    sys.executable, "-m", "json2xml.cli",
                    "-s", '{"test": "data"}',
                    "-o", str(output_file),
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert output_file.exists()
            content = output_file.read_text()
            assert "<test" in content
            assert "data" in content

    def test_wrapper_option(self) -> None:
        """Test -w/--wrapper flag for custom wrapper element."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"name": "John"}',
                "-w", "root",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<root>" in result.stdout

    def test_no_root_option(self) -> None:
        """Test --no-root flag."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"name": "John"}',
                "--no-root",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Without root, there should be no wrapper element
        assert "<all>" not in result.stdout

    def test_no_pretty_option(self) -> None:
        """Test --no-pretty flag disables pretty printing."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"name": "John"}',
                "--no-pretty",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Output should be XML on a single line (not indented)
        # Pretty mode adds newlines and indentation, non-pretty is compact
        lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
        # Non-pretty output should be more compact (typically 1-2 lines)
        assert len(lines) <= 2
        assert "<name" in result.stdout

    def test_no_type_option(self) -> None:
        """Test --no-type flag excludes type attributes."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"name": "John", "age": 30}',
                "--no-type",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'type="str"' not in result.stdout
        assert 'type="int"' not in result.stdout

    def test_xpath_format(self) -> None:
        """Test -x/--xpath flag for XPath 3.1 format."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"name": "John"}',
                "-x",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "http://www.w3.org/2005/xpath-functions" in result.stdout

    def test_stdin_input(self) -> None:
        """Test reading from stdin with - argument."""
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "-"],
            input='{"stdin": "test"}',
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<stdin" in result.stdout
        assert "test" in result.stdout

    def test_invalid_json_string(self) -> None:
        """Test error handling for invalid JSON string."""
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "-s", "not valid json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_no_input_error(self) -> None:
        """Test error when no input is provided."""
        # Force isatty to return True by using a pty-like environment
        # For now, just test with explicit empty args
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli"],
            capture_output=True,
            text=True,
            input="",  # Empty stdin
        )
        # Should fail with no input error
        assert result.returncode == 1

    def test_list_input(self) -> None:
        """Test handling of JSON array input."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '[1, 2, 3]',
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<item" in result.stdout

    def test_nested_json(self) -> None:
        """Test handling of nested JSON structures."""
        nested_json = '{"outer": {"inner": {"value": 42}}}'
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "-s", nested_json],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<outer" in result.stdout
        assert "<inner" in result.stdout
        assert "42" in result.stdout

    def test_cdata_option(self) -> None:
        """Test -c/--cdata flag wraps string values in CDATA sections."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"message": "Hello <World>"}',
                "-c",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<![CDATA[" in result.stdout

    def test_list_headers_option(self) -> None:
        """Test -l/--list-headers flag repeats headers for each list item."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"items": [1, 2, 3]}',
                "-l",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # The flag should be accepted and produce valid output
        assert "<item" in result.stdout
        assert "1" in result.stdout

    def test_stdin_empty_with_dash(self) -> None:
        """Test error handling when stdin is empty with - argument."""
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "-"],
            input="",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Empty input" in result.stderr or "Error" in result.stderr

    def test_stdin_whitespace_only(self) -> None:
        """Test error handling when stdin contains only whitespace."""
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "-"],
            input="   \n\t  ",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Empty input" in result.stderr or "Error" in result.stderr

    def test_no_item_wrap_option(self) -> None:
        """Test --no-item-wrap flag disables wrapping list items."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '[1, 2, 3]',
                "--no-item-wrap",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Without item wrap, there should be no <item> elements
        assert "<item" not in result.stdout

    def test_nonexistent_file_error(self) -> None:
        """Test error handling for nonexistent input file."""
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "/nonexistent/path/file.json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_invalid_json_file(self) -> None:
        """Test error handling for file with invalid JSON content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "invalid.json"
            json_file.write_text("this is not valid json {{{")

            result = subprocess.run(
                [sys.executable, "-m", "json2xml.cli", str(json_file)],
                capture_output=True,
                text=True,
            )

        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_output_file_permission_error(self) -> None:
        """Test error handling when output file cannot be written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a directory where we'll try to write a file with same name
            output_path = Path(tmpdir) / "readonly_dir"
            output_path.mkdir()

            result = subprocess.run(
                [
                    sys.executable, "-m", "json2xml.cli",
                    "-s", '{"test": "data"}',
                    "-o", str(output_path / "subdir" / "file.xml"),
                ],
                capture_output=True,
                text=True,
            )

        assert result.returncode == 1
        assert "Error" in result.stderr

    def test_boolean_values(self) -> None:
        """Test handling of JSON boolean values."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"active": true, "deleted": false}',
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "true" in result.stdout.lower() or "True" in result.stdout
        assert "false" in result.stdout.lower() or "False" in result.stdout

    def test_null_values(self) -> None:
        """Test handling of JSON null values."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"value": null}',
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<value" in result.stdout

    def test_numeric_values(self) -> None:
        """Test handling of JSON numeric values (int and float)."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"integer": 42, "float": 3.14}',
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "42" in result.stdout
        assert "3.14" in result.stdout

    def test_combined_flags(self) -> None:
        """Test combining multiple flags together."""
        result = subprocess.run(
            [
                sys.executable, "-m", "json2xml.cli",
                "-s", '{"items": [1, 2]}',
                "-w", "data",
                "--no-pretty",
                "--no-type",
                "--no-item-wrap",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Custom wrapper should be present when root is true
        # Type attributes should not be present
        assert 'type="' not in result.stdout


class TestCLIUnitTests:
    """Unit tests for CLI functions (not subprocess-based)."""

    def test_create_parser(self) -> None:
        """Test create_parser returns a valid ArgumentParser."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "json2xml-py"

    def test_create_parser_parses_all_args(self) -> None:
        """Test parser handles all argument combinations."""
        parser = create_parser()
        args = parser.parse_args([
            "-s", '{"test": 1}',
            "-w", "custom",
            "--no-root",
            "--no-pretty",
            "--no-type",
            "--no-item-wrap",
            "-x",
            "-c",
            "-l",
            "-o", "output.xml",
        ])
        assert args.string == '{"test": 1}'
        assert args.wrapper == "custom"
        assert args.root is False
        assert args.pretty is False
        assert args.attr_type is False
        assert args.item_wrap is False
        assert args.xpath_format is True
        assert args.cdata is True
        assert args.list_headers is True
        assert args.output == "output.xml"

    def test_main_with_string_input(self, capsys: CaptureFixture[str]) -> None:
        """Test main function with string input."""
        exit_code = main(["-s", '{"name": "test"}'])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "<name" in captured.out

    def test_main_with_invalid_json(self, capsys: CaptureFixture[str]) -> None:
        """Test main function with invalid JSON string."""
        with pytest.raises(SystemExit) as exc_info:
            main(["-s", "not valid json"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_main_returns_error_for_empty_data(self, capsys: CaptureFixture[str]) -> None:
        """Test main returns error when converter returns None."""
        with patch("json2xml.cli.Json2xml") as mock_converter:
            mock_instance = MagicMock()
            mock_instance.to_xml.return_value = None
            mock_converter.return_value = mock_instance

            exit_code = main(["-s", '{"test": "data"}'])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Empty data" in captured.err

    def test_main_handles_conversion_exception(self, capsys: CaptureFixture[str]) -> None:
        """Test main handles exceptions during conversion."""
        with patch("json2xml.cli.Json2xml") as mock_converter:
            mock_converter.side_effect = ValueError("Conversion failed")

            exit_code = main(["-s", '{"test": "data"}'])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error converting to XML" in captured.err

    def test_write_output_with_bytes(self, capsys: CaptureFixture[str]) -> None:
        """Test write_output handles bytes input."""
        write_output(b"<xml>test</xml>", None)
        captured = capsys.readouterr()
        assert "<xml>test</xml>" in captured.out

    def test_write_output_with_string(self, capsys: CaptureFixture[str]) -> None:
        """Test write_output handles string input."""
        write_output("<xml>test</xml>", None)
        captured = capsys.readouterr()
        assert "<xml>test</xml>" in captured.out

    def test_write_output_to_file(self) -> None:
        """Test write_output writes to file correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.xml"
            write_output("<xml>test</xml>", str(output_file))
            assert output_file.exists()
            assert output_file.read_text() == "<xml>test</xml>"

    def test_read_from_stdin_valid_json(self) -> None:
        """Test read_from_stdin with valid JSON."""
        with patch("sys.stdin", io.StringIO('{"key": "value"}')):
            result = read_from_stdin()
        assert result == {"key": "value"}

    def test_read_from_stdin_empty_raises_system_exit(self) -> None:
        """Test read_from_stdin raises SystemExit on empty input."""
        with patch("sys.stdin", io.StringIO("")):
            with pytest.raises(SystemExit) as exc_info:
                read_from_stdin()
        assert exc_info.value.code == 1

    def test_read_from_stdin_invalid_json_raises_system_exit(self) -> None:
        """Test read_from_stdin raises SystemExit on invalid JSON."""
        with patch("sys.stdin", io.StringIO("not json")):
            with pytest.raises(SystemExit) as exc_info:
                read_from_stdin()
        assert exc_info.value.code == 1

    def test_read_input_url_error(self, capsys: CaptureFixture[str]) -> None:
        """Test read_input handles URL read errors."""
        from json2xml.utils import URLReadError

        with patch("json2xml.cli.readfromurl") as mock_read:
            mock_read.side_effect = URLReadError("Connection failed")

            args = MagicMock()
            args.url = "http://example.com/data.json"
            args.string = None
            args.input_file = None

            with pytest.raises(SystemExit) as exc_info:
                read_input(args)

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error reading from URL" in captured.err

    def test_read_input_json_file_error(self, capsys: CaptureFixture[str]) -> None:
        """Test read_input handles JSON file read errors."""
        from json2xml.utils import JSONReadError

        with patch("json2xml.cli.readfromjson") as mock_read:
            mock_read.side_effect = JSONReadError("File not found")

            args = MagicMock()
            args.url = None
            args.string = None
            args.input_file = "nonexistent.json"

            with pytest.raises(SystemExit) as exc_info:
                read_input(args)

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error reading JSON file" in captured.err

    def test_read_input_no_input_tty(self, capsys: CaptureFixture[str]) -> None:
        """Test read_input exits when no input provided and stdin is a tty."""
        with patch("sys.stdin.isatty", return_value=True):
            args = MagicMock()
            args.url = None
            args.string = None
            args.input_file = None

            with pytest.raises(SystemExit) as exc_info:
                read_input(args)

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No input provided" in captured.err

    def test_read_input_stdin_when_not_tty(self) -> None:
        """Test read_input reads from stdin when not a tty."""
        with (
            patch("sys.stdin.isatty", return_value=False),
            patch("json2xml.cli.read_from_stdin") as mock_stdin,
        ):
            mock_stdin.return_value = {"key": "value"}

            args = MagicMock()
            args.url = None
            args.string = None
            args.input_file = None

            result = read_input(args)
            assert result == {"key": "value"}
            mock_stdin.assert_called_once()

    def test_read_input_priority_url_over_string(self) -> None:
        """Test URL input takes priority over string input."""
        with patch("json2xml.cli.readfromurl") as mock_url:
            mock_url.return_value = {"from": "url"}

            args = MagicMock()
            args.url = "http://example.com/data.json"
            args.string = '{"from": "string"}'
            args.input_file = None

            result = read_input(args)
            assert result == {"from": "url"}
            mock_url.assert_called_once_with("http://example.com/data.json")

    def test_read_input_priority_string_over_file(self) -> None:
        """Test string input takes priority over file input."""
        with patch("json2xml.cli.readfromstring") as mock_string:
            mock_string.return_value = {"from": "string"}

            args = MagicMock()
            args.url = None
            args.string = '{"from": "string"}'
            args.input_file = "somefile.json"

            result = read_input(args)
            assert result == {"from": "string"}
            mock_string.assert_called_once()

    def test_write_output_file_error(self, capsys: CaptureFixture[str]) -> None:
        """Test write_output handles file write errors."""
        with pytest.raises(SystemExit) as exc_info:
            write_output("<xml/>", "/nonexistent/path/file.xml")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error writing to file" in captured.err

    def test_main_with_file_input(self, capsys: CaptureFixture[str]) -> None:
        """Test main function with file input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "test.json"
            json_file.write_text('{"key": "value"}')

            exit_code = main([str(json_file)])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "<key" in captured.out

    def test_main_with_output_file(self) -> None:
        """Test main function with output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.xml"

            exit_code = main(["-s", '{"key": "value"}', "-o", str(output_file)])

            assert exit_code == 0
            assert output_file.exists()
            content = output_file.read_text()
            assert "<key" in content

    def test_read_input_stdin_dash_argument(self) -> None:
        """Test read_input with '-' as input_file reads from stdin."""
        with patch("json2xml.cli.read_from_stdin") as mock_stdin:
            mock_stdin.return_value = {"from": "stdin"}

            args = MagicMock()
            args.url = None
            args.string = None
            args.input_file = "-"

            result = read_input(args)
            assert result == {"from": "stdin"}
            mock_stdin.assert_called_once()

    def test_main_handles_generic_read_exception(self, capsys: CaptureFixture[str]) -> None:
        """Test main handles generic exceptions from read_input."""
        with patch("json2xml.cli.read_input") as mock_read:
            mock_read.side_effect = RuntimeError("Unexpected error")

            exit_code = main(["-s", '{"test": "data"}'])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error reading input" in captured.err

    def test_main_module_execution(self) -> None:
        """Test the __main__ block is executable."""
        result = subprocess.run(
            [sys.executable, "-m", "json2xml.cli", "-s", '{"test": 1}'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<test" in result.stdout
