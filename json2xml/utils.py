"""Utility methods for reading JSON data from various sources."""

from __future__ import annotations

import json
import socket
import zlib
from ipaddress import ip_address
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

__lazy_modules__ = ["urllib3"]

from .types import JSONValue

DEFAULT_URL_TIMEOUT: Any | None = None
DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024
COMPRESSED_READ_CHUNK_BYTES = 64 * 1024
_HTTP: Any | None = None


def _get_http_client() -> tuple[Any, Any, Any]:
    """Import and initialize urllib3 only for URL reads."""
    import urllib3

    global DEFAULT_URL_TIMEOUT, _HTTP
    if DEFAULT_URL_TIMEOUT is None:
        DEFAULT_URL_TIMEOUT = urllib3.Timeout(connect=5.0, read=30.0)
    if _HTTP is None:
        _HTTP = urllib3.PoolManager()
    return urllib3, _HTTP, DEFAULT_URL_TIMEOUT


class JSONReadError(Exception):
    """Raised when there is an error reading JSON data."""

    pass


class InvalidDataError(Exception):
    """Raised when the data is invalid."""

    pass


class URLReadError(Exception):
    """Raised when there is an error reading from a URL."""

    pass


class StringReadError(Exception):
    """Raised when there is an error reading from a string."""

    pass


# @lat: [[behavior#Input readers]]
def readfromjson(filename: str) -> JSONValue:
    """Read JSON data from a file."""
    try:
        with open(filename, encoding="utf-8") as jsondata:
            return json.load(jsondata)
    except (ValueError, OSError) as error:
        raise JSONReadError("Invalid JSON File") from error


# @lat: [[behavior#URL security boundaries]]
def _validate_url(url: str) -> SplitResult:
    """Validate the URL form without performing network access."""
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except (TypeError, ValueError) as error:
        raise URLReadError("URL is not valid") from error

    if parsed.scheme not in {"http", "https"}:
        raise URLReadError("URL must use HTTP or HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise URLReadError("URL must not contain credentials")
    if parsed.hostname is None:
        raise URLReadError("URL must include a hostname")
    return parsed


def _resolve_validated_address(
    parsed: SplitResult, allow_private_networks: bool
) -> str | None:
    """Resolve and validate the public address used for the connection."""
    if allow_private_networks:
        return None

    assert parsed.hostname is not None
    hostname = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addresses = [ip_address(hostname)]
    except ValueError:
        try:
            address_info = socket.getaddrinfo(
                hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        except (OSError, UnicodeError) as error:
            raise URLReadError("URL hostname could not be resolved") from error
        addresses = [
            ip_address(str(info[4][0]).split("%", 1)[0]) for info in address_info
        ]

    if not addresses or any(not address.is_global for address in addresses):
        raise URLReadError("URL must resolve only to a public network address")
    return str(addresses[0])


def _request_via_validated_address(
    http: Any,
    parsed: SplitResult,
    validated_address: str,
    params: dict[str, str] | None,
    timeout: Any,
) -> Any:
    """Issue a GET directly to an address already validated as public."""
    assert parsed.hostname is not None
    try:
        hostname = parsed.hostname.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise URLReadError("URL hostname could not be resolved") from error

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    authority = f"[{hostname}]" if ":" in hostname else hostname
    if parsed.port is not None:
        authority = f"{authority}:{parsed.port}"
    pool_kwargs = None
    if parsed.scheme == "https":
        pool_kwargs = {
            "assert_hostname": hostname,
            "server_hostname": hostname,
        }
    pool = http.connection_from_host(
        validated_address,
        port=port,
        scheme=parsed.scheme,
        pool_kwargs=pool_kwargs,
    )
    request_target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    return pool.request(
        "GET",
        request_target,
        fields=params,
        headers={"Host": authority},
        timeout=timeout,
        retries=False,
        redirect=False,
        preload_content=False,
    )


def _has_zlib_header(data: bytes) -> bool:
    """Return whether bytes begin with an RFC 1950 zlib header."""
    if len(data) < 2:
        return False
    compression_method, flags = data[0], data[1]
    return (
        compression_method & 0x0F == 8 and (compression_method << 8 | flags) % 31 == 0
    )


def _compression_decoder(encoding: str, first_chunk: bytes) -> Any:
    """Create a bounded-output decoder for supported content encodings."""
    if encoding in {"gzip", "x-gzip"}:
        return zlib.decompressobj(16 + zlib.MAX_WBITS)
    if encoding == "deflate":
        window_bits = (
            zlib.MAX_WBITS if _has_zlib_header(first_chunk) else -zlib.MAX_WBITS
        )
        return zlib.decompressobj(window_bits)
    raise URLReadError(f"Unsupported Content-Encoding: {encoding}")


def _decompress_with_limit(
    response: Any,
    decoder: Any,
    first_chunk: bytes,
    max_response_bytes: int,
    content_length: int | None,
) -> bytes:
    """Decode a compressed body with encoded and decoded byte limits."""
    response_data = bytearray()
    compressed_bytes = len(first_chunk)
    compressed_chunk = first_chunk
    try:
        while compressed_chunk:
            if compressed_bytes > max_response_bytes:
                raise URLReadError("URL response exceeds maximum size")
            if content_length is not None and compressed_bytes > content_length:
                raise URLReadError("URL response exceeds declared Content-Length")

            pending = compressed_chunk
            while pending:
                remaining_bytes = max_response_bytes + 1 - len(response_data)
                decoded_chunk = decoder.decompress(pending, remaining_bytes)
                response_data.extend(decoded_chunk)
                if len(response_data) > max_response_bytes:
                    raise URLReadError("URL response exceeds maximum size")
                pending = decoder.unconsumed_tail

            if content_length is not None and compressed_bytes == content_length:
                break
            compressed_bytes_max = (
                content_length if content_length is not None else max_response_bytes + 1
            )
            read_size = min(
                COMPRESSED_READ_CHUNK_BYTES,
                compressed_bytes_max - compressed_bytes,
            )
            compressed_chunk = response.read(read_size, decode_content=False)
            compressed_bytes += len(compressed_chunk)
    except zlib.error as error:
        raise URLReadError("URL returned invalid compressed data") from error

    if content_length is not None and compressed_bytes != content_length:
        raise URLReadError("URL response did not match Content-Length")
    if not decoder.eof or decoder.unused_data:
        raise URLReadError("URL returned invalid compressed data")
    return bytes(response_data)


def _read_response_data(
    response: Any,
    max_response_bytes: int,
    content_length: int | None,
) -> bytes:
    """Read a response without allowing encoded or decoded output above the limit."""
    encoding = response.headers.get("Content-Encoding", "").strip().lower()
    if encoding in {"", "identity"}:
        response_data = response.read(
            max_response_bytes + 1,
            decode_content=False,
        )
        if len(response_data) > max_response_bytes:
            raise URLReadError("URL response exceeds maximum size")
        return response_data

    compressed_bytes_max = (
        content_length if content_length is not None else max_response_bytes + 1
    )
    first_chunk = response.read(
        min(COMPRESSED_READ_CHUNK_BYTES, compressed_bytes_max),
        decode_content=False,
    )
    decoder = _compression_decoder(encoding, first_chunk)
    return _decompress_with_limit(
        response,
        decoder,
        first_chunk,
        max_response_bytes,
        content_length,
    )


def _validated_content_length(response: Any, max_response_bytes: int) -> int | None:
    """Parse and bound a declared encoded response length."""
    content_length = response.headers.get("Content-Length")
    if content_length is None:
        return None
    try:
        parsed_length = int(content_length)
    except ValueError as error:
        raise URLReadError("URL returned an invalid Content-Length") from error
    if parsed_length < 0:
        raise URLReadError("URL returned an invalid Content-Length")
    if parsed_length > max_response_bytes:
        raise URLReadError("URL response exceeds maximum size")
    return parsed_length


def readfromurl(
    url: str,
    params: dict[str, str] | None = None,
    *,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    allow_private_networks: bool = False,
) -> JSONValue:
    """Load bounded JSON data from a public URL.

    Private-network access is available only through the explicit trusted-caller
    opt-in. Redirects and embedded credentials are always rejected.
    """
    if not isinstance(allow_private_networks, bool):
        raise URLReadError("allow_private_networks must be a boolean")
    if (
        isinstance(max_response_bytes, bool)
        or not isinstance(max_response_bytes, int)
        or max_response_bytes <= 0
    ):
        raise URLReadError("Maximum response size must be a positive integer")
    parsed = _validate_url(url)
    validated_address = _resolve_validated_address(
        parsed,
        allow_private_networks,
    )

    urllib3, http, timeout = _get_http_client()
    response = None
    try:
        if validated_address is None:
            response = http.request(
                "GET",
                parsed.geturl(),
                fields=params,
                timeout=timeout,
                retries=False,
                redirect=False,
                preload_content=False,
            )
        else:
            response = _request_via_validated_address(
                http,
                parsed,
                validated_address,
                params,
                timeout,
            )
        if response.status != 200:
            raise URLReadError("URL is not returning correct response")

        content_length = _validated_content_length(
            response,
            max_response_bytes,
        )
        response_data = _read_response_data(
            response,
            max_response_bytes,
            content_length,
        )
    except urllib3.exceptions.HTTPError as error:
        raise URLReadError("URL could not be read") from error
    finally:
        if response is not None:
            response.close()

    try:
        return json.loads(response_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise URLReadError("URL did not return valid JSON") from error


def readfromstring(jsondata: object) -> JSONValue:
    """Load JSON data from a string."""
    if not isinstance(jsondata, str):
        raise StringReadError("Input is not a proper JSON string")
    try:
        return json.loads(jsondata)
    except ValueError as error:
        raise StringReadError("Input is not a proper JSON string") from error
