"""Tests for the json2xml CLI."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


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
