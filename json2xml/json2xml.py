#! /usr/bin/env python

import simplejson, urllib, dict2xml
from BeautifulSoup import BeautifulStoneSoup

class Json2xml(object):

    def __init__(self, url):
        self.url = url

    def json2xml(self):
        data = simplejson.load(urllib.urlopen(self.url))
        if data:
            xmldata = dict2xml.dict2xml(data)
            xml = BeautifulStoneSoup(xmldata)
            return xml


