from src.json2xml import Json2xml
data = Json2xml.fromjsonfile('examples/example.json').data
data_object = Json2xml(data, wrapper="custom", indent=4)
print(data_object.json2xml()) #xml output
