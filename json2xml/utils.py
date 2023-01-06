from __future__ import annotations

"""Utils methods to convert XML data to dict from various sources"""
import json
import urllib3


class JSONReadError(Exception):
    pass


class InvalidDataError(Exception):
    pass


class URLReadError(Exception):
    pass


class StringReadError(Exception):
    pass


def readfromjson(filename: str) -> dict[str, str]:
    """
    Reads a json string and emits json string
    """
    try:
        with open(filename, encoding="utf-8") as json_data:
            data = json.load(json_data)
            json_data.close()
            return data
    except ValueError as exp:
        print(exp)
        raise JSONReadError
    except OSError as exp:
        print(exp)
        raise JSONReadError("Invalid JSON File")


def readfromurl(url: str, params: dict[str, str] | None = None) -> dict[str, str]:
    """
    Loads json from an URL over the internets
    """
    # we need a PoolManager for connection pooling with urllib3. Also, params
    # needs to be encoded too
    http = urllib3.PoolManager()
    response = http.request("GET", url, fields=params)
    if response.status == 200:
        data = json.loads(response.data.decode('utf-8'))
        return data
    raise URLReadError("URL is not returning correct response")


def readfromstring(jsondata: str) -> dict[str, str]:
    """
    Loads json from string
    """
    if not isinstance(jsondata, str):
        raise StringReadError("Sorry! the string doesn't seems to a proper JSON")
    try:
        data = json.loads(jsondata)
    except ValueError as exp:
        print(exp)
        raise StringReadError("Sorry! the string doesn't seems to a proper JSON")
    except Exception as exp:
        print(exp)
        raise StringReadError("Sorry! the string doesn't seems to a proper JSON")
    return data
