##About

This is a simple python module to conver json data to xml data.


### How to install

```
pip install json2xml
```

###How to use

Check out the examples given in examples directory.

Run:
```bash

$ python example.py
```

Gives:

```xml
<results>
<address_components>
<long_name>Pune</long_name>
<short_name>Pune</short_name>
<types>locality</types>
<types>political</types>
</address_components>
<address_components>
<long_name>Pune</long_name>
<short_name>Pune</short_name>
<types>administrative_area_level_2</types>
<types>political</types>
</address_components>
<address_components>
<long_name>Maharashtra</long_name>
<short_name>MH</short_name>
<types>administrative_area_level_1</types>
<types>political</types>
</address_components>
<address_components>
<long_name>India</long_name>
<short_name>IN</short_name>
<types>country</types>
<types>political</types>
</address_components>
<formatted_address>Pune, Maharashtra, India</formatted_address>
<geometry>
<bounds>
<northeast>
<lat>18.6346965</lat>
<lng>73.9894867</lng>
</northeast>
<southwest>
<lat>18.4136739</lat>
<lng>73.7398911</lng>
</southwest>
</bounds>
<location>
<lat>18.5204303</lat>
<lng>73.8567437</lng>
</location>
<location_type>APPROXIMATE</location_type>
<viewport>
<northeast>
<lat>18.6346965</lat>
<lng>73.9894867</lng>
</northeast>
<southwest>
<lat>18.4136739</lat>
<lng>73.7398911</lng>
</southwest>
</viewport>
</geometry>
<types>locality</types>
<types>political</types>
</results>
<status>OK</status>
```

###Bugs, features

Create an issue in the repository
