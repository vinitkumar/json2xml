##About

[![Build Status](https://travis-ci.org/vinitkumar/json2xml.svg?branch=master)](https://travis-ci.org/vinitkumar/json2xml)

A Simple python utility to convert JSON to XML(Supports 3.5.x and 3.6.x).
It can be used to convert a json file to xml or from an URL that returns json data.

### How to install

```
pip3 install json2xml
```

### Usage

#### Command Line

python -m src.cli --file="examples/example.json"
python -m src.cli --url="https://coderwall.com/vinitcool76.json"

#### Inline in Code

- From a file

```python
from src.json2xml import Json2xml
data = Json2xml.fromjsonfile('examples/example.json').data
data_object = Json2xml(data)
data_object.json2xml() #xml output
```

- From an URL

```python
from src.json2xml import Json2xml
data = Json2xml.fromurl('https://coderwall.com/vinitcool76.json').data
data_object = Json2xml(data)
data_object.json2xml() #xml output
```


### Bugs, features

Create an ![issue](https://github.com/vinitkumar/json2xml/issues/new) in the repository and if you have a new feature that you want to add, please send a pull request.
