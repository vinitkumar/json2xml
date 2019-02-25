import json
import requests
import sys


def readfromjson(filename: str) -> dict:
    """
    Reads a json string and emits json string
    """
    try:
        json_data = open(filename)
        data = json.load(json_data)
        json_data.close()
        print(type(data))
        return data
    except ValueError as e:
        print(e)
        sys.exit(e)
    except IOError as e:
        print(e)
        sys.exit(e)


def readfromurl(url: str, params: dict = None) -> dict:
    """
    Loads json from an URL over the internets
    """
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        sys.exit(response.text)


def readfromstring(jsondata: str) -> dict:
    """
    Loads json from string
    """
    if type(jsondata) is not str:
        sys.exit("the input doesn't seem to be valid string")
    try:
        data = json.loads(jsondata)
    except ValueError as e:
        print(e)
        sys.exit(e)
    except Exception as e:
        print(e)
        sys.exit(e)
    return data
