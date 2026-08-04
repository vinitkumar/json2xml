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
def _validate_url(
    url: str, allow_private_networks: bool
) -> tuple[SplitResult, str | None]:
    """Validate a URL and return the public address the request must use."""
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError) as error:
        raise URLReadError("URL is not valid") from error

    if parsed.scheme not in {"http", "https"}:
        raise URLReadError("URL must use HTTP or HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise URLReadError("URL must not contain credentials")
    if parsed.hostname is None:
        raise URLReadError("URL must include a hostname")
    if allow_private_networks:
        return parsed, None

    hostname = parsed.hostname
    try:
        addresses = [ip_address(hostname)]
    except ValueError:
        try:
            address_info = socket.getaddrinfo(
                hostname,
                port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except (OSError, UnicodeError) as error:
            raise URLReadError("URL hostname could not be resolved") from error
        addresses = [
            ip_address(str(info[4][0]).split("%", 1)[0])
            for info in address_info
        ]

    if not addresses or any(not address.is_global for address in addresses):
        raise URLReadError("URL must resolve only to a public network address")
    return parsed, str(addresses[0])


def _request_url(
    http: Any,
    parsed: SplitResult,
    validated_address: str | None,
    params: dict[str, str] | None,
    timeout: Any,
) -> Any:
    """Issue a GET directly to the validated address when one is required."""
    request_options = {
        "fields": params,
        "timeout": timeout,
        "retries": False,
        "redirect": False,
        "preload_content": False,
    }
    if validated_address is None:
        return http.request("GET", parsed.geturl(), **request_options)

    assert parsed.hostname is not None
    hostname = parsed.hostname.encode("idna").decode("ascii")

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
        headers={"Host": authority},
        **request_options,
    )


def _compression_decoder(encoding: str, first_chunk: bytes) -> Any:
    """Create a bounded-output decoder for supported content encodings."""
    if encoding in {"gzip", "x-gzip"}:
        return zlib.decompressobj(16 + zlib.MAX_WBITS)
    if encoding == "deflate":
        has_zlib_header = (
            len(first_chunk) >= 2
            and first_chunk[0] & 0x0F == 8
            and (first_chunk[0] << 8 | first_chunk[1]) % 31 == 0
        )
        return zlib.decompressobj(
            zlib.MAX_WBITS if has_zlib_header else -zlib.MAX_WBITS
        )
    raise URLReadError(f"Unsupported Content-Encoding: {encoding}")


def _read_response_data(response: Any, max_response_bytes: int) -> bytes:
    """Read a response without allowing decoded output above the limit."""
    encoding = response.headers.get("Content-Encoding", "").strip().lower()
    if encoding in {"", "identity"}:
        response_data = response.read(
            max_response_bytes + 1,
            decode_content=False,
        )
        if len(response_data) > max_response_bytes:
            raise URLReadError("URL response exceeds maximum size")
        return response_data

    first_chunk = response.read(
        COMPRESSED_READ_CHUNK_BYTES,
        decode_content=False,
    )
    decoder = _compression_decoder(encoding, first_chunk)
    response_data = bytearray()
    compressed_chunk = first_chunk
    try:
        while compressed_chunk:
            pending = compressed_chunk
            while pending:
                remaining_bytes = max_response_bytes + 1 - len(response_data)
                decoded_chunk = decoder.decompress(pending, remaining_bytes)
                response_data.extend(decoded_chunk)
                if len(response_data) > max_response_bytes:
                    raise URLReadError("URL response exceeds maximum size")
                pending = decoder.unconsumed_tail
            compressed_chunk = response.read(
                COMPRESSED_READ_CHUNK_BYTES,
                decode_content=False,
            )
    except zlib.error as error:
        raise URLReadError("URL returned invalid compressed data") from error

    if not decoder.eof or decoder.unused_data:
        raise URLReadError("URL returned invalid compressed data")
    return bytes(response_data)


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
    parsed, validated_address = _validate_url(url, allow_private_networks)

    urllib3, http, timeout = _get_http_client()
    response = None
    try:
        response = _request_url(
            http,
            parsed,
            validated_address,
            params,
            timeout,
        )
        if response.status != 200:
            raise URLReadError("URL is not returning correct response")

        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > max_response_bytes:
                    raise URLReadError("URL response exceeds maximum size")
            except ValueError as error:
                raise URLReadError("URL returned an invalid Content-Length") from error

        response_data = _read_response_data(response, max_response_bytes)
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
