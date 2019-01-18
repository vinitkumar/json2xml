#! /usr/bin/env python
import argparse
import json
import sys

import dict2xml
import requests


class Json2xml(object):
    """
    This class could read a json file
    from the filesystem or get a file from across
    the Internet or a json string and convert that into to
    xml
    """

    def __init__(self, data: str, wrapper:str = "all", indent:int=4) -> None:
        self.data = data
        self.indent = indent
        self.wrapper = wrapper

    @classmethod
    def fromjsonfile(cls, filename: str):
        """
        read json from a json file in the filesystem

        :param filename:
        :return: dict
        """
        data = []
        try:
            json_data = open(filename)
            data = json.load(json_data)
            json_data.close()
        except ValueError:
            print("the file doesn't appear to be a valid json")
        except IOError as e:
            print("looks like the file doesn't exists")
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
            data = []
        return cls(data)

    @classmethod
    def fromurl(cls, url: str, params=None):
        """
        Fetches the JSON
        data from an URL Source.

        :param url:
        :param params:
        :return: dict
        """
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return cls(response.json())
        else:
            raise Exception("Bad URl, Can't get JSON response")

    @classmethod
    def fromstring(cls, data: str):
        """
        Reads the json data as string and
        converts to dict

        :param data:
        :return: dict
        """
        if type(data) is not str:
            raise ValueError("the input doesn't seem to be valid string")
        try:
            data = json.loads(data)
        except ValueError:
            print("the string doesn't appear to be a valid json")
        except Exception as e:
            print("the string doesn't appear to be a valid json", e)
            data = []
        return cls(data)

    def json2xml(self):
        """
        This method actually takes the json that has
        been loaded into dict and converts it to XML

        :return: XML string
        """
        if self.data:
            return dict2xml.dict2xml(self.data, self.wrapper , indent=self.indent * ' ')
