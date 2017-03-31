import sys
import argparse
from src.json2xml import Json2xml


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
