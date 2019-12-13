"""Utils methods to convert XML data to dict from various sources"""
import sys
import json
import requests


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
        sys.exit(exp)
    except IOError as exp:
        print(exp)
        sys.exit(exp)


def readfromurl(url: str, params: dict = None) -> dict:
    """
    Loads json from an URL over the internets
    """
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    sys.exit(response.text)


def readfromstring(jsondata: str) -> dict:
    """
    Loads json from string
    """
    if not isinstance(jsondata, str):
        sys.exit("the input doesn't seem to be valid string")
    try:
        data = json.loads(jsondata)
    except ValueError as exp:
        print(exp)
        sys.exit(exp)
    except Exception as exp:
        print(exp)
        sys.exit(exp)
    return data
