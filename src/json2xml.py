#! /usr/bin/env python
import sys
import requests
import simplejson
import urllib
import dict2xml
from bs4 import BeautifulSoup


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
            data = simplejson.load(json_data)
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
    def fromurl(cls, url: str):
        response = requests.get(url)
        if response.status_code == 200:
            return cls(response.json())
        else:
            raise Exception("Bad URl, Can't get JSON response")
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
            xmldata = dict2xml.dict2xml(self.data)
            xml = BeautifulSoup(xmldata, "html.parser")
            return xml

def main(argv=None):
    parser = argparse.ArgumentParser(description='Utility to convert json to valid xml.')
    parser.add_argument('--url', dest='url', action='store')
    parser.add_argument('--file', dest='file', action='store')
    args = parser.parse_args()

    if args.url:
        url = args.url
        data = Json2xml.fromurl(url)
        print(Json2xml.json2xml(data))

    if args.file:
        file = args.file
        data = Json2xml.fromjsonfile(file)
        print(Json2xml.json2xml(data))

if __name__ == "__main__":
    main(sys.argv)

