import sys
import lxml.etree as etree
from .json2xml import Json2xml

def main(argv=None):
   if len(argv) > 1:
      data = Json2xml.fromjsonfile(argv[1]).data
      data_object = Json2xml(data)
      try:
          xml = etree.XML(data_object)
          print(etree.tostring(xml, pretty_print = True))
      except Exception as e:
         print(data_object.json2xml())

if __name__ == "__main__":
    main(sys.argv)
