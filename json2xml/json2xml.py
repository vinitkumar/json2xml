#! /usr/bin/env python
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
    def __init__(self, data):
        self.data = data

    # -------------------------------
    ##
    # @Synopsis  Read JSON from a file in
    # the system
    # ---------------------------------
    @classmethod
    def fromjsonfile(cls, filename):
        try:
            json_data = open(filename)
            data = simplejson.load(json_data)
        except IOError as e:
            print ("I/O error({0}): {1}".format(e.errno, e.strerror))
            data = []
        return cls(data)

    # -------------------------------
    ##
    # @Synopsis  Fetches the JSON
    # data from an URL Source.
    #
    # ---------------------------------
    @classmethod
    def fromurl(cls, url):
        data = requests.get(url).json()
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
            xmldata = dict2xml.dict2xml(self.data)
            xml = BeautifulSoup(xmldata, "html.parser")
            return xml

def main(argv=None):
   if len(argv) > 1:
      data = Json2xml.fromjsonfile(argv[1]).data
      data_object = Json2xml(data)
      try:
          import lxml.etree as etree
          xml = etree.XML(data_object)
          print(etree.tostring(xml, pretty_print = True))
      except Exception as e:
         print(data_object.json2xml())

if __name__ == "__main__":
    main(sys.argv)

