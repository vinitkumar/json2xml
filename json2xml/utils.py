"""Utility methods for reading JSON data from various sources."""
from __future__ import annotations

import json
import socket
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

__lazy_modules__ = ["urllib3"]

from .types import JSONValue

DEFAULT_URL_TIMEOUT: Any | None = None
DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024
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
def _validate_url(url: str, allow_private_networks: bool) -> None:
    """Reject URL forms that can escape the intended public HTTP boundary."""
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
        return

    hostname = parsed.hostname
    try:
        addresses = {ip_address(hostname)}
    except ValueError:
        try:
            address_info = socket.getaddrinfo(
                hostname,
                port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except OSError as error:
            raise URLReadError("URL hostname could not be resolved") from error
        addresses = {
            ip_address(str(info[4][0]).split("%", 1)[0])
            for info in address_info
        }

    if not addresses or any(not address.is_global for address in addresses):
        raise URLReadError("URL must resolve only to a public network address")


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
    if (
        isinstance(max_response_bytes, bool)
        or not isinstance(max_response_bytes, int)
        or max_response_bytes <= 0
    ):
        raise URLReadError("Maximum response size must be a positive integer")
    _validate_url(url, allow_private_networks)

    urllib3, http, timeout = _get_http_client()
    response = None
    try:
        response = http.request(
            "GET",
            url,
            fields=params,
            timeout=timeout,
            retries=False,
            redirect=False,
            preload_content=False,
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

        response_data = response.read(max_response_bytes + 1, decode_content=True)
        if len(response_data) > max_response_bytes:
            raise URLReadError("URL response exceeds maximum size")
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
