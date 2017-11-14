#! /usr/bin/env python
import argparse
import json
import sys

import dict2xml
import requests


class Json2xml(object):
    # -------------------------------
    ##
    # @Synopsis  This class could read a json file
    # from the filesystem or get a file from across
    # the Internet, and convert that json object to
    # xml
    #
    # @Param data : Data to be fed into the system.
    #
    # @Returns  Null
    # ---------------------------------
    def __init__(self, data: str) -> None:
        self.data = data

    # -------------------------------
    ##
    # @Synopsis  Read JSON from a file in
    # the system
    # ---------------------------------
    @classmethod
    def fromjsonfile(cls, filename: str):
        try:
            json_data = open(filename)
            data = json.load(json_data)
            json_data.close()
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
            data = []
        return cls(data)

    # -------------------------------
    ##
    # @Synopsis  Fetches the JSON
    # data from an URL Source.
    #
    # ---------------------------------
    @classmethod
    def fromurl(cls, url: str, params=None):
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return cls(response.json())
        else:
            raise Exception("Bad URl, Can't get JSON response")

    @classmethod
    def fromstring(cls, data: str):
        if type(data) is not str:
            raise("Sorry but it doesn't seem to be valid string")
        try:
            data = json.loads(data)
        except Exception as e:
            print("Sorry, failed to load json, seems the JSON is not right")
            data = []
        return cls(data)


    # -------------------------------
    ##
    # @Synopsis  This method actually
    # converts the json data that is converted
    # into dict into XML
    #
    # @Returns XML
    # ---------------------------------
    def json2xml(self):
        if self.data:
            xmldata = dict2xml.dict2xml(self.data, wrap="all", indent="  ")
            return xmldata
