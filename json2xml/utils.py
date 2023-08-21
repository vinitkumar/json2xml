"""Utility methods for converting XML data to dictionary from various sources."""
from typing import Optional

import json
import urllib3


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


def readfromjson(filename: str) -> dict[str, str]:
    """Reads a JSON file and returns a dictionary."""
    try:
        with open(filename, encoding="utf-8") as jsondata:
            return json.load(jsondata)
    except ValueError:
        raise JSONReadError("Invalid JSON File")
    except OSError:
        raise JSONReadError("Invalid JSON File")


def readfromurl(url: str, params: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Loads JSON data from a URL and returns a dictionary."""
    http = urllib3.PoolManager()
    response = http.request("GET", url, fields=params)
    if response.status == 200:
        return json.loads(response.data.decode('utf-8'))
    raise URLReadError("URL is not returning correct response")


def readfromstring(jsondata: str) -> dict[str, str]:
    """Loads JSON data from a string and returns a dictionary."""
    if not isinstance(jsondata, str):
        raise StringReadError("Input is not a proper JSON string")
    try:
        return json.loads(jsondata)
    except ValueError:
        raise StringReadError("Input is not a proper JSON string")
