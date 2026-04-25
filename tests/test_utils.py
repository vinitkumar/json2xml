"""Test module for json2xml.utils functionality."""
import json
import socket
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, ClassVar
from unittest.mock import Mock, patch

import pytest

from json2xml.utils import (
    InvalidDataError,
    JSONReadError,
    StringReadError,
    URLReadError,
    readfromjson,
    readfromstring,
    readfromurl,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch


class JsonTestHandler(BaseHTTPRequestHandler):
    """Tiny HTTP handler for exercising the real URL reader."""

    responses: ClassVar[dict[str, tuple[int, bytes]]] = {
        "/data.json": (200, b'{"key": "value", "number": 42}'),
        "/api": (200, b'{"result": "success"}'),
        "/invalid.json": (200, b"invalid json content"),
        "/error.json": (500, b'{"error": true}'),
        "/api.json": (200, b'{"api": "response", "status": "ok"}'),
    }

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        status, body = self.responses.get(path, (404, b'{"error": "not found"}'))
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
# @lat: [[tests#Input readers#URL reader uses real HTTP and wraps failures]]
def json_server() -> "Iterator[str]":
    server = ThreadingHTTPServer(("127.0.0.1", 0), JsonTestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host = server.server_address[0]
        port = server.server_address[1]
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


class TestExceptions:
    """Test custom exception classes."""

    def test_json_read_error(self) -> None:
        """Test JSONReadError exception."""
        with pytest.raises(JSONReadError) as exc_info:
            raise JSONReadError("Test error message")
        assert str(exc_info.value) == "Test error message"

    def test_invalid_data_error(self) -> None:
        """Test InvalidDataError exception."""
        with pytest.raises(InvalidDataError) as exc_info:
            raise InvalidDataError("Invalid data")
        assert str(exc_info.value) == "Invalid data"

    def test_url_read_error(self) -> None:
        """Test URLReadError exception."""
        with pytest.raises(URLReadError) as exc_info:
            raise URLReadError("URL error")
        assert str(exc_info.value) == "URL error"

    def test_string_read_error(self) -> None:
        """Test StringReadError exception."""
        with pytest.raises(StringReadError) as exc_info:
            raise StringReadError("String error")
        assert str(exc_info.value) == "String error"


class TestReadFromJson:
    """Test readfromjson function."""

    def test_readfromjson_valid_file(self) -> None:
        """Test reading a valid JSON file."""
        test_data = {"key": "value", "number": 42}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_filename = f.name

        try:
            result = readfromjson(temp_filename)
            assert result == test_data
        finally:
            import os
            os.unlink(temp_filename)

    def test_readfromjson_invalid_json_content(self) -> None:
        """Test reading a file with invalid JSON content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json content}')  # Invalid JSON
            temp_filename = f.name

        try:
            with pytest.raises(JSONReadError, match="Invalid JSON File"):
                readfromjson(temp_filename)
        finally:
            import os
            os.unlink(temp_filename)

    def test_readfromjson_file_not_found(self) -> None:
        """Test reading a non-existent file."""
        with pytest.raises(JSONReadError, match="Invalid JSON File"):
            readfromjson("non_existent_file.json")

    @patch('builtins.open')
    def test_readfromjson_permission_error(self, mock_open: Mock) -> None:
        """Test reading a file with permission issues."""
        # Mock open to raise PermissionError
        mock_open.side_effect = PermissionError("Permission denied")

        with pytest.raises(JSONReadError, match="Invalid JSON File"):
            readfromjson("some_file.json")

    @patch('builtins.open')
    def test_readfromjson_os_error(self, mock_open: Mock) -> None:
        """Test reading a file with OS error."""
        # Mock open to raise OSError (covers line 34-35 in utils.py)
        mock_open.side_effect = OSError("Device not ready")

        with pytest.raises(JSONReadError, match="Invalid JSON File"):
            readfromjson("some_file.json")


class TestReadFromUrl:
    """Test readfromurl function."""

    def test_readfromurl_success(self, json_server: str) -> None:
        """Test successful URL reading."""
        result = readfromurl(f"{json_server}/data.json")

        assert result == {"key": "value", "number": 42}

    def test_readfromurl_success_with_params(self, json_server: str) -> None:
        """Test successful URL reading with parameters."""
        params = {"param1": "value1", "param2": "value2"}
        result = readfromurl(f"{json_server}/api", params=params)

        assert result == {"result": "success"}

    def test_readfromurl_http_error(self, json_server: str) -> None:
        """Test URL reading with HTTP error status."""
        with pytest.raises(URLReadError, match="URL is not returning correct response"):
            readfromurl(f"{json_server}/nonexistent.json")

    def test_readfromurl_server_error(self, json_server: str) -> None:
        """Test URL reading with server error status."""
        with pytest.raises(URLReadError, match="URL is not returning correct response"):
            readfromurl(f"{json_server}/error.json")

    def test_readfromurl_invalid_json_response(self, json_server: str) -> None:
        """Test URL reading with invalid JSON response."""
        with pytest.raises(URLReadError, match="URL did not return valid JSON"):
            readfromurl(f"{json_server}/invalid.json")

    def test_readfromurl_network_error(self) -> None:
        """Test network failures are wrapped as URLReadError."""
        with socket.socket() as unused_socket:
            unused_socket.bind(("127.0.0.1", 0))
            port = unused_socket.getsockname()[1]

        with pytest.raises(URLReadError, match="URL could not be read"):
            readfromurl(f"http://127.0.0.1:{port}/data.json")


class TestReadFromString:
    """Test readfromstring function."""

    def test_readfromstring_valid_json(self) -> None:
        """Test reading valid JSON string."""
        json_string = '{"key": "value", "number": 42, "boolean": true}'
        result = readfromstring(json_string)
        assert result == {"key": "value", "number": 42, "boolean": True}

    def test_readfromstring_empty_object(self) -> None:
        """Test reading empty JSON object."""
        json_string = '{}'
        result = readfromstring(json_string)
        assert result == {}

    def test_readfromstring_complex_object(self) -> None:
        """Test reading complex JSON object."""
        json_string = '{"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}], "total": 2}'
        result = readfromstring(json_string)
        expected = {
            "users": [
                {"name": "John", "age": 30},
                {"name": "Jane", "age": 25}
            ],
            "total": 2
        }
        assert result == expected

    def test_readfromstring_invalid_type_int(self) -> None:
        """Test reading with integer input."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring(123)  # type: ignore[arg-type]

    def test_readfromstring_invalid_type_list(self) -> None:
        """Test reading with list input."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring(["not", "a", "string"])  # type: ignore[arg-type]

    def test_readfromstring_invalid_type_dict(self) -> None:
        """Test reading with dict input."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring({"not": "a string"})  # type: ignore[arg-type]

    def test_readfromstring_invalid_type_none(self) -> None:
        """Test reading with None input."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring(None)  # type: ignore[arg-type]

    def test_readfromstring_invalid_json_syntax(self) -> None:
        """Test reading string with invalid JSON syntax."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring('{"invalid": json, syntax}')

    def test_readfromstring_invalid_json_incomplete(self) -> None:
        """Test reading incomplete JSON string."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring('{"incomplete":')

    def test_readfromstring_invalid_json_extra_comma(self) -> None:
        """Test reading JSON string with trailing comma."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring('{"key": "value",}')

    def test_readfromstring_invalid_json_single_quotes(self) -> None:
        """Test reading JSON string with single quotes."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring("{'key': 'value'}")

    def test_readfromstring_empty_string(self) -> None:
        """Test reading empty string."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring("")

    def test_readfromstring_plain_text(self) -> None:
        """Test reading plain text."""
        with pytest.raises(StringReadError, match="Input is not a proper JSON string"):
            readfromstring("this is just plain text")


class TestIntegration:
    """Integration tests combining multiple utilities."""

    def test_readfromstring_then_convert_to_xml(self) -> None:
        """Test reading JSON string and converting to XML."""
        from json2xml import dicttoxml

        json_string = '{"name": "test", "value": 123}'
        data = readfromstring(json_string)
        xml_result = dicttoxml.dicttoxml(data, attr_type=False, root=False)

        assert b"<name>test</name>" in xml_result
        assert b"<value>123</value>" in xml_result

    def test_readfromurl_then_convert_to_xml(self, json_server: str) -> None:
        """Test reading from URL and converting to XML."""
        from json2xml import dicttoxml

        data = readfromurl(f"{json_server}/api.json")
        xml_result = dicttoxml.dicttoxml(data, attr_type=False, root=False)

        assert b"<api>response</api>" in xml_result
        assert b"<status>ok</status>" in xml_result
