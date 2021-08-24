"""Utils methods to convert XML data to dict from various sources"""
import json
import requests


class JSONReadError(Exception):
    pass


class URLReadError(Exception):
    pass


class StringReadError(Exception):
    pass



def readfromjson(filename: str) -> dict:
    """
    Reads a json string and emits json string
    """
    try:
        json_data = open(filename)
        data = json.load(json_data)
        json_data.close()
        return data
    except ValueError as exp:
        print(exp)
        raise JSONReadError
    except IOError as exp:
        print(exp)
        raise JSONReadError("Invalid JSON File")


def readfromurl(url: str, params: dict = None) -> dict:
    """
    Loads json from an URL over the internets
    """
    # TODO: See if we can remove requests too from the deps too. Then, we will become
    # zero deps.
    # REFERENCE: this article https://dev.to/bowmanjd/http-calls-in-python-without-requests-or-other-external-dependencies-5aj1
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    raise URLReadError("URL is not returning correct response")


def readfromstring(jsondata: str) -> dict:
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
