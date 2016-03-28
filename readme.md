##About

[![Build Status](https://travis-ci.org/vinitkumar/json2xml.svg?branch=master)](https://travis-ci.org/vinitkumar/json2xml)

A Simple python utility to convert JSON to xml. It support conversation
from a json file or from an URL. (Supports both Python2.7.x and 3.5.x)

### How to install

```
# python2
pip install json2xml
# python3
pip3 install json2xml
```

###How to use

#### From JSON File

```python
from json2xml.json2xml import Json2xml
data = Json2xml.fromjsonfile('examples/example.json').data
data_object = Json2xml(data)
data_object.json2xml()
```

#### From WEB Url

```python
from json2xml.json2xml import Json2xml
data = Json2xml.fromurl('https://coderwall.com/vinitcool76.json').data
data_object = Json2xml(data)
data_object.json2xml()
```

These are two simple ways you can use this utility.

### Bugs, features

Create an issue in the repository and if you have a new feature that you want to add, please send a pull request.
