#! /usr/bin/env python

BASE_URL = 'https://coderwall.com/vinitcool76.json'

import sys
import os
import urllib


sys.path.insert(0, os.path.abspath('..'))

from json2xml import json2xml

def main():
    data = json2xml.Json2xml(BASE_URL)
    print data.json2xml()

if __name__ == "__main__":
    main()
