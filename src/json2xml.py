#! /usr/bin/env python

import simplejson, urllib, dict2xml
from BeautifulSoup import BeautifulStoneSoup

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
            print "I/O error({0}): {1}".format(e.errno, e.strerror)
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
        data = simplejson.load(urllib.urlopen(url))
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
            xml = BeautifulStoneSoup(xmldata)
            return xml

            


