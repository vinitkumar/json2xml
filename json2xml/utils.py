"""Utility methods for reading JSON data from various sources."""
from __future__ import annotations

import json

import urllib3

from .types import JSONValue

DEFAULT_URL_TIMEOUT = urllib3.Timeout(connect=5.0, read=30.0)
_HTTP = urllib3.PoolManager()


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


def readfromurl(url: str, params: dict[str, str] | None = None) -> JSONValue:
    """Load JSON data from a URL."""
    try:
        response = _HTTP.request(
            "GET",
            url,
            fields=params,
            timeout=DEFAULT_URL_TIMEOUT,
            retries=False,
        )
    except urllib3.exceptions.HTTPError as error:
        raise URLReadError("URL could not be read") from error

    if response.status != 200:
        raise URLReadError("URL is not returning correct response")

    try:
        return json.loads(response.data.decode("utf-8"))
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
