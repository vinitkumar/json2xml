"""Test module for json2xml.utils functionality."""

import gzip
import json
import socket
import tempfile
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any, ClassVar, cast
from unittest.mock import Mock, patch

import pytest
import urllib3

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


class JsonTestHandler(BaseHTTPRequestHandler):
    """Tiny HTTP handler for exercising the real URL reader."""

    json_responses: ClassVar[dict[str, tuple[int, bytes]]] = {
        "/data.json": (200, b'{"key": "value", "number": 42}'),
        "/api": (200, b'{"result": "success"}'),
        "/invalid.json": (200, b"invalid json content"),
        "/error.json": (500, b'{"error": true}'),
        "/api.json": (200, b'{"api": "response", "status": "ok"}'),
    }

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        status, body = self.json_responses.get(path, (404, b'{"error": "not found"}'))
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json content}')  # Invalid JSON
            temp_filename = f.name

        try:
            with pytest.raises(JSONReadError, match="Invalid JSON File"):
                readfromjson(temp_filename)
        finally:
            import os

            os.unlink(temp_filename)

    # @lat: [[tests#Input readers#File reader distinguishes unreadable files from invalid JSON]]
    def test_readfromjson_file_not_found(self) -> None:
        """Test reading a non-existent file."""
        with pytest.raises(JSONReadError, match="Could not read JSON file"):
            readfromjson("non_existent_file.json")

    @patch("builtins.open")
    def test_readfromjson_permission_error(self, mock_open: Mock) -> None:
        """Test reading a file with permission issues."""
        # Mock open to raise PermissionError
        mock_open.side_effect = PermissionError("Permission denied")

        with pytest.raises(JSONReadError, match="Could not read JSON file"):
            readfromjson("some_file.json")

    @patch("builtins.open")
    def test_readfromjson_os_error(self, mock_open: Mock) -> None:
        """Test reading a file with OS error."""
        # Mock open to raise OSError (covers line 34-35 in utils.py)
        mock_open.side_effect = OSError("Device not ready")

        with pytest.raises(JSONReadError, match="Could not read JSON file"):
            readfromjson("some_file.json")


class TestReadFromUrl:
    """Test readfromurl function."""

    def test_readfromurl_success(self, json_server: str) -> None:
        """Test successful URL reading."""
        result = readfromurl(f"{json_server}/data.json", allow_private_networks=True)

        assert result == {"key": "value", "number": 42}

    def test_readfromurl_success_with_params(self, json_server: str) -> None:
        """Test successful URL reading with parameters."""
        params = {"param1": "value1", "param2": "value2"}
        result = readfromurl(
            f"{json_server}/api", params=params, allow_private_networks=True
        )

        assert result == {"result": "success"}

    def test_readfromurl_http_error(self, json_server: str) -> None:
        """Test URL reading with HTTP error status."""
        with pytest.raises(URLReadError, match="URL is not returning correct response"):
            readfromurl(f"{json_server}/nonexistent.json", allow_private_networks=True)

    def test_readfromurl_server_error(self, json_server: str) -> None:
        """Test URL reading with server error status."""
        with pytest.raises(URLReadError, match="URL is not returning correct response"):
            readfromurl(f"{json_server}/error.json", allow_private_networks=True)

    def test_readfromurl_invalid_json_response(self, json_server: str) -> None:
        """Test URL reading with invalid JSON response."""
        with pytest.raises(URLReadError, match="URL did not return valid JSON"):
            readfromurl(f"{json_server}/invalid.json", allow_private_networks=True)

    def test_readfromurl_network_error(self) -> None:
        """Test network failures are wrapped as URLReadError."""
        with socket.socket() as unused_socket:
            unused_socket.bind(("127.0.0.1", 0))
            port = unused_socket.getsockname()[1]

        with pytest.raises(URLReadError, match="URL could not be read"):
            readfromurl(
                f"http://127.0.0.1:{port}/data.json", allow_private_networks=True
            )

    # @lat: [[tests#Input readers#URL reader rejects unsafe destinations]]
    def test_readfromurl_rejects_private_networks_by_default(self) -> None:
        """Test URL reads cannot reach private or link-local services by default."""
        with pytest.raises(URLReadError, match="public network address"):
            readfromurl("http://127.0.0.1/private.json")

        with pytest.raises(URLReadError, match="public network address"):
            readfromurl("http://169.254.169.254/latest/meta-data/")

    @patch("json2xml.utils.socket.getaddrinfo")
    def test_readfromurl_rejects_hostnames_resolving_to_private_networks(
        self, mock_getaddrinfo: Mock
    ) -> None:
        """Test DNS names cannot bypass the private-network URL policy."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 443))
        ]

        with pytest.raises(URLReadError, match="public network address"):
            readfromurl("https://internal.example/data.json")

    # @lat: [[tests#Input readers#URL reader pins validated DNS addresses]]
    @pytest.mark.parametrize(
        (
            "url",
            "validated_address",
            "expected_port",
            "expected_host",
            "expected_pool_kwargs",
            "uses_dns",
        ),
        [
            (
                "https://rebind.example/data.json?existing=yes",
                "93.184.216.34",
                443,
                "rebind.example",
                {
                    "assert_hostname": "rebind.example",
                    "server_hostname": "rebind.example",
                },
                True,
            ),
            (
                "http://rebind.example/data.json?existing=yes",
                "93.184.216.34",
                80,
                "rebind.example",
                None,
                True,
            ),
            (
                "https://[2606:4700:4700::1111]:8443/data.json?existing=yes",
                "2606:4700:4700::1111",
                8443,
                "[2606:4700:4700::1111]:8443",
                {
                    "assert_hostname": "2606:4700:4700::1111",
                    "server_hostname": "2606:4700:4700::1111",
                },
                False,
            ),
        ],
        ids=["https-default-port", "http-default-port", "https-ipv6"],
    )
    @patch("json2xml.utils._get_http_client")
    @patch("json2xml.utils.socket.getaddrinfo")
    def test_readfromurl_pins_validated_address_with_correct_authority(
        self,
        mock_getaddrinfo: Mock,
        mock_get_http_client: Mock,
        url: str,
        validated_address: str,
        expected_port: int,
        expected_host: str,
        expected_pool_kwargs: dict[str, str] | None,
        uses_dns: bool,
    ) -> None:
        """Test pinned HTTP(S), default ports, and IPv6 authority handling."""
        mock_getaddrinfo.return_value = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (validated_address, expected_port),
            )
        ]
        response = Mock(status=200, headers={"Content-Length": "11"})
        response.read.return_value = b'{"ok":true}'
        pool = Mock()
        pool.request.return_value = response
        http = Mock()
        http.connection_from_host.return_value = pool
        timeout = Mock()
        mock_get_http_client.return_value = (urllib3, http, timeout)

        result = readfromurl(url, params={"added": "yes"})

        assert result == {"ok": True}
        http.request.assert_not_called()
        http.connection_from_host.assert_called_once_with(
            validated_address,
            port=expected_port,
            scheme="https" if url.startswith("https:") else "http",
            pool_kwargs=expected_pool_kwargs,
        )
        pool.request.assert_called_once_with(
            "GET",
            "/data.json?existing=yes",
            fields={"added": "yes"},
            headers={"Host": expected_host},
            timeout=timeout,
            retries=False,
            redirect=False,
            preload_content=False,
        )
        if uses_dns:
            mock_getaddrinfo.assert_called_once()
        else:
            mock_getaddrinfo.assert_not_called()
        response.close.assert_called_once_with()

    @patch("json2xml.utils._get_http_client")
    def test_readfromurl_uses_direct_request_for_private_network_opt_in(
        self, mock_get_http_client: Mock
    ) -> None:
        """Test trusted private-network reads retain the complete request URL."""
        url = "https://private.example/data.json?existing=yes"
        response = Mock(status=200, headers={"Content-Length": "11"})
        response.read.return_value = b'{"ok":true}'
        http = Mock()
        http.request.return_value = response
        timeout = Mock()
        mock_get_http_client.return_value = (urllib3, http, timeout)

        result = readfromurl(
            url,
            params={"added": "yes"},
            allow_private_networks=True,
        )

        assert result == {"ok": True}
        http.connection_from_host.assert_not_called()
        http.request.assert_called_once_with(
            "GET",
            url,
            fields={"added": "yes"},
            timeout=timeout,
            retries=False,
            redirect=False,
            preload_content=False,
        )
        response.close.assert_called_once_with()

    def test_readfromurl_rejects_unsupported_schemes_and_credentials(self) -> None:
        """Test URL reads accept only credential-free HTTP and HTTPS URLs."""
        with pytest.raises(URLReadError, match="HTTP or HTTPS"):
            readfromurl("file:///etc/passwd")

        with pytest.raises(URLReadError, match="credentials"):
            readfromurl("https://user:password@8.8.8.8/data.json")

        with pytest.raises(URLReadError, match="include a hostname"):
            readfromurl("https:///data.json")

        with pytest.raises(URLReadError, match="not valid"):
            readfromurl("https://8.8.8.8:not-a-port/data.json")

    @patch("json2xml.utils.socket.getaddrinfo")
    def test_readfromurl_rejects_unresolvable_hostnames(
        self, mock_getaddrinfo: Mock
    ) -> None:
        """Test DNS failures are reported without attempting an HTTP request."""
        mock_getaddrinfo.side_effect = OSError("DNS unavailable")

        with pytest.raises(URLReadError, match="could not be resolved"):
            readfromurl("https://unresolvable.example/data.json")

    # @lat: [[tests#Input readers#URL reader wraps invalid Unicode hostnames]]
    @patch("json2xml.utils.socket.getaddrinfo")
    def test_readfromurl_wraps_invalid_unicode_hostnames(
        self, mock_getaddrinfo: Mock
    ) -> None:
        """Test malformed IDNA hostnames preserve the URL reader error contract."""
        mock_getaddrinfo.side_effect = UnicodeError("invalid IDNA label")

        with pytest.raises(URLReadError, match="could not be resolved"):
            readfromurl("https://invalid-unicode.example/data.json")

    @patch("json2xml.utils._get_http_client")
    @patch("json2xml.utils.socket.getaddrinfo")
    def test_readfromurl_wraps_idna_failure_when_building_pinned_request(
        self, mock_getaddrinfo: Mock, mock_get_http_client: Mock
    ) -> None:
        """Test IDNA failure after resolution still raises URLReadError."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ]
        http = Mock()
        mock_get_http_client.return_value = (urllib3, http, Mock())

        with pytest.raises(URLReadError, match="could not be resolved"):
            readfromurl("https://\ud800.example/data.json")

        http.connection_from_host.assert_not_called()

    # @lat: [[tests#Input readers#URL reader requires a boolean private-network opt-in]]
    @pytest.mark.parametrize("allow_private_networks", ["false", 1, None])
    def test_readfromurl_rejects_non_boolean_private_network_opt_in(
        self, allow_private_networks: object
    ) -> None:
        """Test only an actual boolean can opt into private-network access."""
        with pytest.raises(URLReadError, match="must be a boolean"):
            readfromurl(
                "http://127.0.0.1/private.json",
                allow_private_networks=cast(Any, allow_private_networks),
            )

    def test_readfromurl_rejects_invalid_response_limit(self) -> None:
        """Test callers cannot disable the response cap with a non-positive value."""
        with pytest.raises(URLReadError, match="positive integer"):
            readfromurl("https://8.8.8.8/data.json", max_response_bytes=0)

    @pytest.mark.parametrize(
        ("content_length", "message"),
        [
            ("17", "maximum size"),
            ("not-a-number", "invalid Content-Length"),
            ("-1", "invalid Content-Length"),
        ],
    )
    @patch("json2xml.utils._get_http_client")
    def test_readfromurl_rejects_invalid_content_lengths(
        self,
        mock_get_http_client: Mock,
        content_length: str,
        message: str,
    ) -> None:
        """Test declared response sizes are validated before reading the body."""
        response = Mock(status=200, headers={"Content-Length": content_length})
        http = Mock()
        http.request.return_value = response
        mock_get_http_client.return_value = (urllib3, http, Mock())

        with pytest.raises(URLReadError, match=message):
            readfromurl(
                "https://8.8.8.8/data.json",
                max_response_bytes=16,
                allow_private_networks=True,
            )

        response.read.assert_not_called()
        response.close.assert_called_once_with()

    @patch("json2xml.utils._get_http_client")
    def test_readfromurl_limits_uncompressed_response_without_length(
        self, mock_get_http_client: Mock
    ) -> None:
        """Test an undeclared uncompressed body cannot exceed the byte limit."""
        response = Mock(status=200, headers={})
        response.read.return_value = b"x" * 17
        http = Mock()
        http.request.return_value = response
        mock_get_http_client.return_value = (urllib3, http, Mock())

        with pytest.raises(URLReadError, match="maximum size"):
            readfromurl(
                "https://8.8.8.8/data.json",
                max_response_bytes=16,
                allow_private_networks=True,
            )

        response.read.assert_called_once_with(17, decode_content=False)

    @pytest.mark.parametrize(
        ("encoding", "compressed"),
        [
            pytest.param(
                "gzip",
                gzip.compress(b'{"ok":true}', mtime=0),
                id="gzip",
            ),
            pytest.param(
                "deflate",
                zlib.compress(b'{"ok":true}'),
                id="zlib-deflate",
            ),
            pytest.param(
                "deflate",
                (
                    lambda compressor: (
                        compressor.compress(b'{"ok":true}') + compressor.flush()
                    )
                )(zlib.compressobj(wbits=-zlib.MAX_WBITS)),
                id="raw-deflate",
            ),
        ],
    )
    @patch("json2xml.utils._get_http_client")
    def test_readfromurl_decodes_supported_compression_incrementally(
        self,
        mock_get_http_client: Mock,
        encoding: str,
        compressed: bytes,
    ) -> None:
        """Test bounded decoding preserves supported compressed responses."""
        response = Mock(status=200, headers={"Content-Encoding": encoding})
        response.read.side_effect = [compressed, b""]
        http = Mock()
        http.request.return_value = response
        mock_get_http_client.return_value = (urllib3, http, Mock())

        result = readfromurl(
            "https://8.8.8.8/data.json",
            allow_private_networks=True,
        )

        assert result == {"ok": True}

    @patch("json2xml.utils._get_http_client")
    def test_readfromurl_respects_compressed_content_length(
        self, mock_get_http_client: Mock
    ) -> None:
        """Test a declared compressed size bounds raw response reads."""
        compressed = gzip.compress(b'{"ok":true}', mtime=0)
        response = Mock(
            status=200,
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            },
        )
        response.read.side_effect = [compressed]
        http = Mock()
        http.request.return_value = response
        mock_get_http_client.return_value = (urllib3, http, Mock())

        result = readfromurl(
            "https://8.8.8.8/data.json",
            allow_private_networks=True,
        )

        assert result == {"ok": True}
        response.read.assert_called_once_with(
            len(compressed),
            decode_content=False,
        )

    @patch("json2xml.utils._get_http_client")
    def test_readfromurl_rejects_compressed_body_over_declared_length(
        self, mock_get_http_client: Mock
    ) -> None:
        """Test compressed reads reject bytes beyond the declared length."""
        compressed = gzip.compress(b'{"ok":true}', mtime=0)
        response = Mock(
            status=200,
            headers={"Content-Encoding": "gzip", "Content-Length": "1"},
        )
        response.read.return_value = compressed
        http = Mock()
        http.request.return_value = response
        mock_get_http_client.return_value = (urllib3, http, Mock())

        with pytest.raises(URLReadError, match="declared Content-Length"):
            readfromurl(
                "https://8.8.8.8/data.json",
                allow_private_networks=True,
            )

    @patch("json2xml.utils._get_http_client")
    def test_readfromurl_rejects_incomplete_compressed_body(
        self, mock_get_http_client: Mock
    ) -> None:
        """Test compressed reads reject EOF before the declared length."""
        compressed = gzip.compress(b'{"ok":true}', mtime=0)
        response = Mock(
            status=200,
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            },
        )
        response.read.side_effect = [compressed[:10], b""]
        http = Mock()
        http.request.return_value = response
        mock_get_http_client.return_value = (urllib3, http, Mock())

        with pytest.raises(URLReadError, match="did not match Content-Length"):
            readfromurl(
                "https://8.8.8.8/data.json",
                allow_private_networks=True,
            )

    # @lat: [[tests#Input readers#URL reader bounds encoded response size]]
    @patch("json2xml.utils._get_http_client")
    def test_readfromurl_caps_compressed_bytes_without_content_length(
        self, mock_get_http_client: Mock
    ) -> None:
        """Test compressed input is bounded even when decoded output is small."""
        compressed = gzip.compress(b'{"ok":true}', mtime=0)
        response = Mock(status=200, headers={"Content-Encoding": "gzip"})
        response.read.side_effect = [compressed]
        http = Mock()
        http.request.return_value = response
        mock_get_http_client.return_value = (urllib3, http, Mock())

        with pytest.raises(URLReadError, match="maximum size"):
            readfromurl(
                "https://8.8.8.8/data.json",
                max_response_bytes=16,
                allow_private_networks=True,
            )

        response.read.assert_called_once_with(17, decode_content=False)

    @pytest.mark.parametrize(
        ("encoding", "compressed"),
        [
            pytest.param("br", b"unsupported", id="unsupported"),
            pytest.param("gzip", b"not a gzip stream", id="invalid-gzip"),
            pytest.param("deflate", b"x", id="invalid-short-deflate"),
            pytest.param(
                "gzip",
                gzip.compress(b'{"ok":true}', mtime=0)[:-8],
                id="truncated-gzip",
            ),
            pytest.param(
                "gzip",
                gzip.compress(b'{"ok":true}', mtime=0) + b"trailing data",
                id="trailing-gzip",
            ),
        ],
    )
    @patch("json2xml.utils._get_http_client")
    def test_readfromurl_rejects_unsafe_or_invalid_compression(
        self,
        mock_get_http_client: Mock,
        encoding: str,
        compressed: bytes,
    ) -> None:
        """Test unsafe or malformed compressed responses fail closed."""
        response = Mock(status=200, headers={"Content-Encoding": encoding})
        response.read.side_effect = [compressed, b""]
        http = Mock()
        http.request.return_value = response
        mock_get_http_client.return_value = (urllib3, http, Mock())

        with pytest.raises(URLReadError, match="compressed|Content-Encoding"):
            readfromurl(
                "https://8.8.8.8/data.json",
                allow_private_networks=True,
            )

    @patch("json2xml.utils._get_http_client")
    # @lat: [[tests#Input readers#URL reader limits decoded response size]]
    def test_readfromurl_limits_decoded_response_size(
        self, mock_get_http_client: Mock
    ) -> None:
        """Test compressed URL reads stop at the configured decoded-byte limit."""
        compressed = gzip.compress(
            b'{"value":"' + (b"x" * 10_000) + b'"}',
            mtime=0,
        )
        response = Mock(
            status=200,
            headers={"Content-Encoding": "gzip"},
        )
        response.read.side_effect = [compressed, b""]
        http = Mock()
        http.request.return_value = response
        mock_get_http_client.return_value = (urllib3, http, Mock())

        with pytest.raises(URLReadError, match="maximum size"):
            readfromurl(
                "https://8.8.8.8/data.json",
                max_response_bytes=128,
                allow_private_networks=True,
            )

        http.request.assert_called_once_with(
            "GET",
            "https://8.8.8.8/data.json",
            fields=None,
            timeout=mock_get_http_client.return_value[2],
            retries=False,
            redirect=False,
            preload_content=False,
        )
        response.read.assert_called_once_with(129, decode_content=False)
        response.close.assert_called_once_with()


class TestReadFromString:
    """Test readfromstring function."""

    def test_readfromstring_valid_json(self) -> None:
        """Test reading valid JSON string."""
        json_string = '{"key": "value", "number": 42, "boolean": true}'
        result = readfromstring(json_string)
        assert result == {"key": "value", "number": 42, "boolean": True}

    def test_readfromstring_empty_object(self) -> None:
        """Test reading empty JSON object."""
        json_string = "{}"
        result = readfromstring(json_string)
        assert result == {}

    def test_readfromstring_complex_object(self) -> None:
        """Test reading complex JSON object."""
        json_string = '{"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}], "total": 2}'
        result = readfromstring(json_string)
        expected = {
            "users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}],
            "total": 2,
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

        data = readfromurl(f"{json_server}/api.json", allow_private_networks=True)
        xml_result = dicttoxml.dicttoxml(data, attr_type=False, root=False)

        assert b"<api>response</api>" in xml_result
        assert b"<status>ok</status>" in xml_result
