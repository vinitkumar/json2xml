#! /usr/bin/env python

BASE_URL = 'http://maps.googleapis.com/maps/api/geocode/json'

import sys
import os
import urllib


sys.path.insert(0, os.path.abspath('..'))

from json2xml import json2xml


def geocode(address, sensor, **geo_args):
    geo_args.update({
        'address': address,
        'sensor': sensor
    })


def main():
    geocode(address="pune", sensor="false")
    geo_args = {'sensor': 'false', 'address': 'pune'}
    url = BASE_URL + '?' + urllib.urlencode(geo_args)
    data = json2xml.Json2xml(url)
    print data.json2xml()


if __name__ == "__main__":
    main()




