import datetime
import numbers
from typing import TYPE_CHECKING, Any

import pytest

from json2xml import dicttoxml

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


class TestDict2xml:
    """Test class for dicttoxml functionality."""

    def test_dict2xml_with_namespaces(self) -> None:
        """Test dicttoxml with XML namespaces."""
        data = {"ns1:node1": "data in namespace 1", "ns2:node2": "data in namespace 2"}
        namespaces = {
            "ns1": "https://www.google.de/ns1",
            "ns2": "https://www.google.de/ns2",
        }
        result = dicttoxml.dicttoxml(data, attr_type=False, xml_namespaces=namespaces)
        assert (
            b'<?xml version="1.0" encoding="UTF-8" ?>'
            b'<root xmlns:ns1="https://www.google.de/ns1" xmlns:ns2="https://www.google.de/ns2">'
            b"<ns1:node1>data in namespace 1</ns1:node1>"
            b"<ns2:node2>data in namespace 2</ns2:node2>"
            b"</root>" == result
        )

    def test_dict2xml_with_xmlns_namespaces(self) -> None:
        """Test dicttoxml with xmlns namespaces."""
        data = {"ns1:node1": "data in namespace 1", "ns2:node2": "data in namespace 2"}
        namespaces = {"xmlns": "http://www.w3.org/1999/XSL/Transform"}
        result = dicttoxml.dicttoxml(
            obj=data, attr_type=False, xml_namespaces=namespaces
        )
        assert (
            b'<?xml version="1.0" encoding="UTF-8" ?>'
            b'<root xmlns="http://www.w3.org/1999/XSL/Transform">'
            b"<ns1:node1>data in namespace 1</ns1:node1>"
            b"<ns2:node2>data in namespace 2</ns2:node2>"
            b"</root>" == result
        )

    def test_dict2xml_with_xsi_location(self) -> None:
        """Test dicttoxml with XSI schema location."""
        data = {"bike": "blue"}
        wrapper = "vehicle"
        namespaces = {
            "xsi": {
                "schemaInstance": "http://www.w3.org/2001/XMLSchema-instance",
                "schemaLocation": "https://www.w3schools.com/note.xsd",
            }
        }
        result = dicttoxml.dicttoxml(
            data, custom_root=wrapper, xml_namespaces=namespaces, attr_type=False
        )
        print(result)
        assert (
            b'<?xml version="1.0" encoding="UTF-8" ?>'
            b'<vehicle xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            b'xsi:schemaLocation="https://www.w3schools.com/note.xsd">'
            b"<bike>blue</bike>"
            b"</vehicle>" == result
        )

    def test_dict2xml_xsi_xmlns(self) -> None:
        """Test dicttoxml with both XSI and xmlns namespaces."""
        data = {"bike": "blue"}
        wrapper = "vehicle"
        xml_namespace = {
            "xsd": "https://www.w3schools.com/note.xsd",
            "xmlns": "https://www.google.de/ns1",
            "xsi": {
                "schemaInstance": "http://www.w3.org/2001/XMLSchema-instance",
                "schemaLocation": "https://www.w3schools.com",
            },
        }
        result = dicttoxml.dicttoxml(
            data, custom_root=wrapper, xml_namespaces=xml_namespace, attr_type=False
        ).decode()
        print(result)
        assert (
            '<?xml version="1.0" encoding="UTF-8" ?>'
            '<vehicle xmlns:xsd="https://www.w3schools.com/note.xsd" xmlns="https://www.google.de/ns1" '
            ""
            ""
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://www.w3schools.com">'
            "<bike>blue</bike></vehicle>" == result
        )

    def test_item_wrap_true(self) -> None:
        """Test dicttoxml with item_wrap=True."""
        data = {"bike": ["blue", "green"]}
        result = dicttoxml.dicttoxml(
            obj=data, root=False, attr_type=False, item_wrap=True
        )
        assert result == b"<bike><item>blue</item><item>green</item></bike>"

    def test_item_wrap_false(self) -> None:
        """Test dicttoxml with item_wrap=False."""
        data = {"bike": ["blue", "green"]}
        result = dicttoxml.dicttoxml(
            obj=data, root=False, attr_type=False, item_wrap=False
        )
        assert result == b"<bike>blue</bike><bike>green</bike>"

    def test_dict2xml_with_flat(self) -> None:
        """Test dicttoxml with flat list notation."""
        data = {"flat_list@flat": [1, 2, 3], "non_flat_list": [4, 5, 6]}
        result = dicttoxml.dicttoxml(data, attr_type=False)
        assert (
            b'<?xml version="1.0" encoding="UTF-8" ?>'
            b"<root><item>1</item><item>2</item><item>3</item>"
            b"<non_flat_list><item>4</item><item>5</item><item>6</item></non_flat_list>"
            b"</root>" == result
        )

    def test_dict2xml_omit_list(self) -> None:
        """Test dicttoxml with list omission."""
        obj = {"list": [{"bike": "blue"}, {"wheel": "black"}]}
        dicttoxml.dicttoxml(obj, root=False, attr_type=False, item_wrap=False)
        assert b"<list><bike>blue</bike><wheel>black</wheel></list>"

    def test_dict2xml_with_val_and_custom_attr(self) -> None:
        """Test dicttoxml with @val and custom attributes."""
        # in order to use @attr in non-dict objects, we need to lift into a dict and combine with @val as key
        data = {
            "list1": [1, 2, 3],
            "list2": {
                "@attrs": {"myattr1": "myval1", "myattr2": "myval2"},
                "@val": [4, 5, 6],
            },
        }
        result = dicttoxml.dicttoxml(data, attr_type=False)
        assert (
            b'<?xml version="1.0" encoding="UTF-8" ?>'
            b"<root><list1><item>1</item><item>2</item><item>3</item></list1>"
            b'<list2 myattr1="myval1" myattr2="myval2"><item>4</item><item>5</item><item>6</item></list2>'
            b"</root>" == result
        )

    def test_dict2xml_with_ampersand(self) -> None:
        """Test dicttoxml with ampersand character."""
        dict_without_attrs = {"Bicycles": "Wheels & Steers"}
        root = False
        attr_type = False
        result = dicttoxml.dicttoxml(
            dict_without_attrs, root=root, attr_type=attr_type
        ).decode("UTF-8")
        assert "<Bicycles>Wheels &amp; Steers</Bicycles>" == result

    def test_dict2xml_with_ampsersand_and_attrs(self) -> None:
        """Test dicttoxml with ampersand and attributes."""
        dict_with_attrs = {
            "Bicycles": {"@attrs": {"xml:lang": "nl"}, "@val": "Wheels & Steers"}
        }
        root = False
        assert (
            '<Bicycles xml:lang="nl">Wheels &amp; Steers</Bicycles>'
            == dicttoxml.dicttoxml(dict_with_attrs, root=root, attr_type=False).decode(
                "UTF-8"
            )
        )

    @pytest.fixture
    def dict_with_attrs(self) -> dict[str, Any]:
        """Fixture providing a dictionary with attributes for testing."""
        return {
            'transportation-mode': [
                {
                    '@attrs': {'xml:lang': 'nl'},
                    '@val': 'Fiets'
                },
                {
                    '@attrs': {'xml:lang': 'nl'},
                    '@val': 'Bus'
                },
                {
                    '@attrs': {'xml:lang': 'en'},
                    '@val': 'Bike'
                }
            ]
        }

    def test_dict2xml_list_items_with_attrs(self, dict_with_attrs: dict[str, Any]) -> None:
        """Test dicttoxml with list items containing attributes."""
        '''With list headers = True
        '''

        wanted_xml_result = b'<transportation-mode xml:lang="nl">Fiets</transportation-mode>' \
                            b'<transportation-mode xml:lang="nl">Bus</transportation-mode>' \
                            b'<transportation-mode xml:lang="en">Bike</transportation-mode>'
        xml_result = dicttoxml.dicttoxml(
            dict_with_attrs,
            root=False,
            attr_type=False,
            item_wrap=False,
            list_headers=True)

        assert xml_result == wanted_xml_result

    def test_make_id(self) -> None:
        """Test make_id function."""
        make_id_elem = dicttoxml.make_id("li")
        assert "li" in make_id_elem

    def test_get_unique_id(self) -> None:
        """Test get_unique_id function."""
        unique_id_elem_1 = dicttoxml.get_unique_id("li")
        unique_id_elem_2 = dicttoxml.get_unique_id("li")
        unique_id_elem_3 = dicttoxml.get_unique_id("li")
        unique_id_elem_4 = dicttoxml.get_unique_id("li")
        assert (
            len(
                list(
                    {
                        unique_id_elem_1,
                        unique_id_elem_2,
                        unique_id_elem_3,
                        unique_id_elem_4,
                    }
                )
            )
            == 4
        )

    def test_key_is_valid_xml(self) -> None:
        """Test key_is_valid_xml function."""
        valid_key = "li"
        invalid_key = "/li"
        assert dicttoxml.key_is_valid_xml(valid_key) is True
        assert dicttoxml.key_is_valid_xml(invalid_key) is False

    def test_get_xml_type(self) -> None:
        """Test get_xml_type function."""
        assert dicttoxml.get_xml_type("abc") == "str"
        assert dicttoxml.get_xml_type(1) == "int"
        assert dicttoxml.get_xml_type(True) == "bool"
        assert dicttoxml.get_xml_type({}) == "dict"

    def test_is_primitive_type(self) -> None:
        """Test is_primitive_type function."""
        assert dicttoxml.is_primitive_type(True) is True
        assert dicttoxml.is_primitive_type("abc") is True
        assert dicttoxml.is_primitive_type({}) is False

    def test_escape_xml(self) -> None:
        """Test escape_xml function."""
        elem = "&"
        escaped_string = dicttoxml.escape_xml(elem)
        assert "&" != escaped_string
        assert "&amp;" == escaped_string

    def test_wrap_cdata(self) -> None:
        """Test wrap_cdata function."""
        elem = "li"
        assert "CDATA" in dicttoxml.wrap_cdata(elem)

    def test_list_parent_elements(self) -> None:
        """Test convert_list with parent elements."""
        default_item_func = dicttoxml.default_item_func
        item = [{"frame_color": "red"}, {"frame_color": "green"}]
        con_list = dicttoxml.convert_list(
            items=item,
            attr_type=False,
            cdata=False,
            ids=None,
            item_func=default_item_func,
            item_wrap=False,
            parent="Bike",
            list_headers=True,
        )
        print(con_list)
        assert (
            "<Bike><frame_color>red</frame_color></Bike><Bike><frame_color>green</frame_color></Bike>"
            == con_list
        )

    def test_dict2xml_str_list_header(self) -> None:
        """Test dict2xml_str with list headers."""
        from json2xml.dicttoxml import dict2xml_str

        item_func = dicttoxml.default_item_func
        item = {"frame_color": "red"}
        parent = "Bike"
        xml_str = dict2xml_str(
            attr_type=False,
            attr={},
            item=item,
            item_func=item_func,
            cdata=False,
            item_name="item",
            item_wrap=False,
            parentIsList=True,
            parent=parent,
            list_headers=True,
        )

        assert "<Bike><frame_color>red</frame_color></Bike>" == xml_str

    def test_list_headers(self) -> None:
        """Test dicttoxml with list headers."""
        dict = {"Bike": [{"frame_color": "red"}, {"frame_color": "green"}]}
        result = dicttoxml.dicttoxml(
            dict, root=False, item_wrap=False, attr_type=False, list_headers=True
        )
        print(result)
        assert (
            b"<Bike><frame_color>red</frame_color></Bike><Bike><frame_color>green</frame_color></Bike>"
            == result
        )

    def test_list_headers_nested(self) -> None:
        """Test dicttoxml with nested list headers."""
        dict = {
            "transport": {"Bike": [{"frame_color": "red"}, {"frame_color": "green"}]}
        }
        result = dicttoxml.dicttoxml(
            dict, root=False, item_wrap=False, attr_type=False, list_headers=True
        )
        assert (
            b"<transport><Bike><frame_color>red</frame_color></Bike>"
            b"<Bike><frame_color>green</frame_color></Bike></transport>" == result
        )

    def test_list_headers_root(self) -> None:
        """Test dicttoxml with list headers and root element."""
        dict = {"Bike": [{"frame_color": "red"}, {"frame_color": "green"}]}
        result = dicttoxml.dicttoxml(
            dict, root=True, item_wrap=False, attr_type=False, list_headers=True
        )
        assert (
            b'<?xml version="1.0" encoding="UTF-8" ?><root>'
            b"<Bike><frame_color>red</frame_color></Bike>"
            b"<Bike><frame_color>green</frame_color></Bike></root>" == result
        )

    def test_dict2xml_no_root(self) -> None:
        """Test dicttoxml without root element."""
        payload = {"mock": "payload"}
        result = dicttoxml.dicttoxml(payload, attr_type=False, root=False)
        assert b"<mock>payload</mock>" == result

    def test_dict2xml_with_root(self) -> None:
        """Test dicttoxml with root element."""
        payload = {"mock": "payload"}
        result = dicttoxml.dicttoxml(payload, attr_type=False)
        assert (
            b'<?xml version="1.0" encoding="UTF-8" ?><root><mock>payload</mock></root>'
            == result
        )

    def test_dict2xml_with_custom_root(self) -> None:
        """Test dicttoxml with custom root element."""
        payload = {"mock": "payload"}
        result = dicttoxml.dicttoxml(payload, attr_type=False, custom_root="element")
        assert (
            b'<?xml version="1.0" encoding="UTF-8" ?><element><mock>payload</mock></element>'
            == result
        )

    def test_dict2xml_with_item_func(self) -> None:
        """Test dicttoxml with custom item function."""
        data = {"flat_list@flat": [1, 2, 3], "non_flat_list": [4, 5, 6]}
        result = dicttoxml.dicttoxml(data, attr_type=False, item_func=lambda x: "a")
        print(result)
        assert (
            b'<?xml version="1.0" encoding="UTF-8" ?>'
            b"<root><a>1</a><a>2</a><a>3</a><non_flat_list><a>4</a><a>5</a><a>6</a></non_flat_list>"
            b"</root>" == result
        )

    def test_dict2xml_with_item_func_issue_151(self) -> None:
        """Test dicttoxml with item function for issue 151."""
        data = [{"x": [1]}]
        result = dicttoxml.dicttoxml(
            data, root=False, attr_type=False, item_func=lambda y: y + "item"
        )
        print(result)
        assert b"<item><x><xitem>1</xitem></x></item>" == result

    def test_dict2xml_issue_151(self) -> None:
        """Test dicttoxml for issue 151."""
        data = [{"x": [1]}]
        result = dicttoxml.dicttoxml(data, root=False, attr_type=False)
        print(result)
        assert b"<item><x><item>1</item></x></item>" == result

    def test_dict2xml_attr_type(self) -> None:
        """Test dicttoxml with attribute types."""
        data = {"bike": "blue"}
        result = dicttoxml.dicttoxml(data, root=False, attr_type=True)
        assert b'<bike type="str">blue</bike>' == result

    def test_get_xml_type_number(self) -> None:
        """Test get_xml_type with numbers.Number."""
        assert dicttoxml.get_xml_type(3.14) == "float"

    def test_convert_datetime(self) -> None:
        """Test convert_kv with datetime objects."""
        dt = datetime.datetime(2023, 2, 15, 12, 30, 45)

        expected = '<item_name type="str">2023-02-15T12:30:45</item_name>'

        assert dicttoxml.convert_kv(
            key='item_name',
            val=dt,
            attr_type=True,
            attr={},
            cdata=False
        ) == expected

    # write test for bool test
    def test_basic_conversion(self) -> None:
        """Test basic boolean conversion."""
        xml = dicttoxml.convert_bool('key', True, False)
        assert xml == '<key>true</key>'

    def test_with_type_attribute(self) -> None:
        """Test boolean conversion with type attribute."""
        xml = dicttoxml.convert_bool('key', False, True)
        assert xml == '<key type="bool">false</key>'

    def test_with_custom_attributes(self) -> None:
        """Test boolean conversion with custom attributes."""
        xml = dicttoxml.convert_bool('key', True, False, {'id': '1'})
        assert xml == '<key id="1">true</key>'

    def test_valid_key(self) -> None:
        """Test convert_bool with valid key."""
        xml = dicttoxml.convert_bool('valid_key', False, attr_type=False)
        assert xml == '<valid_key>false</valid_key>'

    def test_convert_kv_with_cdata(self) -> None:
        """Test convert_kv with CDATA wrapping."""
        result = dicttoxml.convert_kv("key", "value", attr_type=False, cdata=True)
        assert result == "<key><![CDATA[value]]></key>"

    def test_convert_kv_with_attr_type(self) -> None:
        """Test convert_kv with attribute type."""
        value = 123
        result = dicttoxml.convert_kv("key", value, attr_type=True)
        assert result == '<key type="int">123</key>'

    def test_make_valid_xml_name_with_invalid_key(self) -> None:
        """Test make_valid_xml_name with invalid key."""
        key, attr = dicttoxml.make_valid_xml_name("invalid key", {})
        assert key == "invalid_key"
        assert attr == {}

    def test_convert_bool_with_attr_type(self) -> None:
        """Test convert_bool with attribute type."""
        result = dicttoxml.convert_bool("key", True, attr_type=True)
        assert result == '<key type="bool">true</key>'

    def test_convert_none_with_attr_type(self) -> None:
        """Test convert_none with attribute type."""
        result = dicttoxml.convert_none("key", attr_type=True)
        assert result == '<key type="null"></key>'


    def test_make_valid_xml_name_with_numeric_key(self) -> None:
        """Test make_valid_xml_name with numeric key."""
        key, attr = dicttoxml.make_valid_xml_name("123", {})
        assert key == "n123"
        assert attr == {}

    def test_escape_xml_with_special_chars(self) -> None:
        """Test escape_xml with special characters."""
        result = dicttoxml.escape_xml('This & that < those > these "quotes" \'single quotes\'')
        assert result == "This &amp; that &lt; those &gt; these &quot;quotes&quot; &apos;single quotes&apos;"

    def test_get_xml_type_with_sequence(self) -> None:
        """Test get_xml_type with sequence."""
        result = dicttoxml.get_xml_type(["item1", "item2"])
        assert result == "list"

    def test_get_xml_type_with_none(self) -> None:
        """Test get_xml_type with None value."""
        result = dicttoxml.get_xml_type(None)
        assert result == "null"

    def test_dicttoxml_with_custom_root_missing_prefix(self) -> None:
        """Test dicttoxml with custom root (previously missing test_ prefix)."""
        data = {"key": "value"}
        result = dicttoxml.dicttoxml(data, custom_root="custom", attr_type=False)
        assert b"<custom><key>value</key></custom>" in result

    def test_dicttoxml_with_xml_namespaces(self) -> None:
        """Test dicttoxml with XML namespaces."""
        data = {"key": "value"}
        namespaces = {"xmlns": "http://example.com"}
        result = dicttoxml.dicttoxml(data, xml_namespaces=namespaces)
        assert b'xmlns="http://example.com"' in result

    def test_datetime_conversion(self) -> None:
        """Test datetime conversion."""
        data = {"key": datetime.datetime(2023, 2, 15, 12, 30, 45)}
        result = dicttoxml.dicttoxml(data, attr_type=False)
        assert b"<key>2023-02-15T12:30:45</key>" in result

    def test_list_to_xml_with_primitive_items(self) -> None:
        """Test list to XML with primitive items."""
        data = {"items": [1, 2, 3]}
        result = dicttoxml.dicttoxml(data, root=False, attr_type=False, item_wrap=True)
        assert result == b"<items><item>1</item><item>2</item><item>3</item></items>"

    def test_list_to_xml_with_dict_items(self) -> None:
        """Test list to XML with dictionary items."""
        data = {"items": [{"key1": "value1"}, {"key2": "value2"}]}
        result = dicttoxml.dicttoxml(data, root=False, attr_type=False, item_wrap=True)
        assert result == b"<items><item><key1>value1</key1></item><item><key2>value2</key2></item></items>"

    def test_list_to_xml_with_mixed_items(self) -> None:
        """Test list to XML with mixed item types."""
        data = {"items": [1, "string", {"key": "value"}]}
        result = dicttoxml.dicttoxml(data, root=False, attr_type=False, item_wrap=True)
        assert result == b"<items><item>1</item><item>string</item><item><key>value</key></item></items>"

    def test_list_to_xml_with_empty_list(self) -> None:
        """Test list to XML with empty list."""
        data: dict[str, list[Any]] = {"items": []}
        result = dicttoxml.dicttoxml(data, root=False, attr_type=False, item_wrap=True)
        assert result == b"<items></items>"

    def test_list_to_xml_with_special_characters(self) -> None:
        """Test list to XML with special characters."""
        data = {"items": ["<tag>", "&", '"quote"', "'single quote'"]}
        result = dicttoxml.dicttoxml(data, root=False, attr_type=False, item_wrap=True)
        assert result == b"<items><item>&lt;tag&gt;</item><item>&amp;</item><item>&quot;quote&quot;</item><item>&apos;single quote&apos;</item></items>"

    def test_datetime_conversion_with_isoformat(self) -> None:
        """Test datetime conversion with isoformat."""
        data = {"key": datetime.datetime(2023, 2, 15, 12, 30, 45)}
        result = dicttoxml.dicttoxml(data, attr_type=False)
        assert b"<key>2023-02-15T12:30:45</key>" in result

    def test_date_conversion_with_isoformat(self) -> None:
        """Test date conversion with isoformat."""
        data = {"key": datetime.date(2023, 2, 15)}
        result = dicttoxml.dicttoxml(data, attr_type=False)
        assert b"<key>2023-02-15</key>" in result

    def test_datetime_conversion_with_attr_type(self) -> None:
        """Test datetime conversion with attribute type."""
        data = {"key": datetime.datetime(2023, 2, 15, 12, 30, 45)}
        result = dicttoxml.dicttoxml(data, attr_type=True)
        assert b'<key type="str">2023-02-15T12:30:45</key>' in result

    def test_date_conversion_with_attr_type(self) -> None:
        """Test date conversion with attribute type."""
        data = {"key": datetime.date(2023, 2, 15)}
        result = dicttoxml.dicttoxml(data, attr_type=True)
        assert b'<key type="str">2023-02-15</key>' in result

    def test_datetime_conversion_with_custom_attributes(self) -> None:
        """Test datetime conversion with custom attributes."""
        data = {"key": datetime.datetime(2023, 2, 15, 12, 30, 45)}
        result = dicttoxml.dicttoxml(data, attr_type=False, custom_root="custom")
        assert b"<custom><key>2023-02-15T12:30:45</key></custom>" in result

    def test_date_conversion_with_custom_attributes(self) -> None:
        """Test date conversion with custom attributes."""
        data = {"key": datetime.date(2023, 2, 15)}
        result = dicttoxml.dicttoxml(data, attr_type=False, custom_root="custom")
        assert b"<custom><key>2023-02-15</key></custom>" in result

    def test_get_xml_type_unsupported(self) -> None:
        """Test get_xml_type with unsupported type."""
        class CustomClass:
            pass

        # Should return the class name for unsupported types
        # Using type: ignore for intentional test of unsupported type
        result = dicttoxml.get_xml_type(CustomClass())  # type: ignore[arg-type]
        assert result == "CustomClass"

    def test_make_valid_xml_name_invalid_chars(self) -> None:
        """Test make_valid_xml_name with invalid XML characters."""
        key = "<invalid>key"
        attr: dict[str, Any] = {}
        new_key, new_attr = dicttoxml.make_valid_xml_name(key, attr)
        assert new_key == "key"
        assert new_attr == {"name": "&lt;invalid&gt;key"}

    def test_dict2xml_str_invalid_type(self) -> None:
        """Test dict2xml_str with invalid type."""
        class CustomClass:
            pass

        item = {"key": CustomClass()}
        with pytest.raises(TypeError, match="Unsupported data type:"):
            dicttoxml.dict2xml_str(
                attr_type=False,
                attr={},
                item=item,
                item_func=lambda x: "item",
                cdata=False,
                item_name="test",
                item_wrap=False,
                parentIsList=False
            )

    def test_convert_dict_invalid_type(self) -> None:
        """Test convert_dict with invalid type."""
        class CustomClass:
            pass

        obj = {"key": CustomClass()}
        with pytest.raises(TypeError, match="Unsupported data type:"):
            dicttoxml.convert_dict(
                obj=obj,
                ids=[],
                parent="root",
                attr_type=False,
                item_func=lambda x: "item",
                cdata=False,
                item_wrap=False
            )

    def test_convert_list_invalid_type(self) -> None:
        """Test convert_list with invalid type."""
        class CustomClass:
            pass

        items = [CustomClass()]
        with pytest.raises(TypeError, match="Unsupported data type:"):
            dicttoxml.convert_list(
                items=items,
                ids=None,
                parent="root",
                attr_type=False,
                item_func=lambda x: "item",
                cdata=False,
                item_wrap=False
            )

    def test_convert_list_with_none(self) -> None:
        """Test convert_list with None values."""
        items = [None]
        result = dicttoxml.convert_list(
            items=items,
            ids=None,
            parent="root",
            attr_type=True,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert result == '<item type="null"></item>'

    def test_convert_list_with_custom_ids(self) -> None:
        """Test convert_list with custom IDs."""
        items = ["test"]
        result = dicttoxml.convert_list(
            items=items,
            ids=["custom_id"],
            parent="root",
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert 'id="root_' in result
        assert '>test<' in result

    def test_convert_list_mixed_types(self) -> None:
        """Test convert_list with a mix of valid and invalid types."""
        class CustomClass:
            pass

        items = ["valid string", 100, {"a": "b"}, CustomClass()]
        with pytest.raises(TypeError, match="Unsupported data type:"):
            dicttoxml.convert_list(
                items=items,
                ids=None,
                parent="root",
                attr_type=False,
                item_func=lambda x: "item",
                cdata=False,
                item_wrap=False
            )

    # Additional tests for better coverage
    def test_make_attrstring_empty(self) -> None:
        """Test make_attrstring with empty dictionary."""
        result = dicttoxml.make_attrstring({})
        assert result == ""

    def test_make_attrstring_with_attrs(self) -> None:
        """Test make_attrstring with attributes."""
        result = dicttoxml.make_attrstring({"id": "123", "class": "test"})
        assert 'id="123"' in result
        assert 'class="test"' in result

    def test_convert_with_sequence_input(self) -> None:
        """Test convert function with sequence input."""
        result = dicttoxml.convert(
            obj=[1, 2, 3],
            ids=None,
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert "<item>1</item><item>2</item><item>3</item>" == result

    def test_dicttoxml_with_sequence_input(self) -> None:
        """Test dicttoxml with sequence input."""
        result = dicttoxml.dicttoxml([1, 2, 3], root=False, attr_type=False)
        assert b"<item>1</item><item>2</item><item>3</item>" == result

    def test_convert_kv_with_none_attr(self) -> None:
        """Test convert_kv with None attr parameter."""
        result = dicttoxml.convert_kv("key", "value", attr_type=False, attr=None)
        assert result == "<key>value</key>"

    def test_convert_bool_with_none_attr(self) -> None:
        """Test convert_bool with None attr parameter."""
        result = dicttoxml.convert_bool("key", True, attr_type=False, attr=None)
        assert result == "<key>true</key>"

    def test_convert_none_with_none_attr(self) -> None:
        """Test convert_none with None attr parameter."""
        result = dicttoxml.convert_none("key", attr_type=False, attr=None)
        assert result == "<key></key>"

    def test_escape_xml_with_numbers(self) -> None:
        """Test escape_xml with numeric input."""
        number = 123
        result = dicttoxml.escape_xml(number)
        assert result == "123"

    def test_wrap_cdata_with_numbers(self) -> None:
        """Test wrap_cdata with numeric input."""
        number = 123
        result = dicttoxml.wrap_cdata(number)
        assert result == "<![CDATA[123]]>"

    def test_get_xml_type_with_float(self) -> None:
        """Test get_xml_type with float."""
        result = dicttoxml.get_xml_type(3.14)
        assert result == "float"

    def test_convert_with_float(self) -> None:
        """Test convert function with float input."""
        result = dicttoxml.convert(
            obj=3.14,
            ids=None,
            attr_type=True,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert result == '<item type="float">3.14</item>'

    def test_dicttoxml_with_ids(self) -> None:
        """Test dicttoxml with IDs parameter."""
        data = {"key": "value"}
        result = dicttoxml.dicttoxml(data, ids=[1, 2, 3], attr_type=False)
        assert b'<key id="root_' in result
        assert b'">value</key>' in result

    def test_dicttoxml_with_cdata(self) -> None:
        """Test dicttoxml with CDATA wrapping."""
        data = {"key": "value"}
        result = dicttoxml.dicttoxml(data, cdata=True, attr_type=False, root=False)
        assert b"<key><![CDATA[value]]></key>" == result

    def test_get_unique_id_with_duplicates(self) -> None:
        """Test get_unique_id when duplicates are generated."""
        # We need to modify the original get_unique_id to simulate a pre-existing ID list
        import json2xml.dicttoxml as module

        # Save original function
        original_get_unique_id = module.get_unique_id

        # Track make_id calls
        call_count = 0
        original_make_id = module.make_id

        def mock_make_id(element: str, start: int = 100000, end: int = 999999) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "test_123456"  # First call - will collide
            else:
                return "test_789012"  # Second call - unique

        # Patch get_unique_id to use a pre-populated ids list
        def patched_get_unique_id(element: str) -> str:
            # Start with a pre-existing ID to force collision
            ids = ["test_123456"]
            this_id = module.make_id(element)
            dup = True
            while dup:
                if this_id not in ids:
                    dup = False
                    ids.append(this_id)
                else:
                    this_id = module.make_id(element)  # This exercises line 52
            return ids[-1]

        module.make_id = mock_make_id
        module.get_unique_id = patched_get_unique_id

        try:
            result = dicttoxml.get_unique_id("test")
            assert result == "test_789012"
            assert call_count == 2
        finally:
            module.make_id = original_make_id
            module.get_unique_id = original_get_unique_id

    def test_convert_with_bool_direct(self) -> None:
        """Test convert function with boolean input directly."""
        result = dicttoxml.convert(
            obj=True,
            ids=None,
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert result == "<item>true</item>"

    def test_convert_with_string_direct(self) -> None:
        """Test convert function with string input directly."""
        result = dicttoxml.convert(
            obj="test_string",
            ids=None,
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert result == "<item>test_string</item>"

    def test_convert_with_datetime_direct(self) -> None:
        """Test convert function with datetime input directly."""
        dt = datetime.datetime(2023, 2, 15, 12, 30, 45)
        result = dicttoxml.convert(
            obj=dt,
            ids=None,
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert result == "<item>2023-02-15T12:30:45</item>"

    def test_convert_with_none_direct(self) -> None:
        """Test convert function with None input directly."""
        result = dicttoxml.convert(
            obj=None,
            ids=None,
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert result == "<item></item>"

    def test_convert_unsupported_type_direct(self) -> None:
        """Test convert function with unsupported type."""
        class CustomClass:
            pass

        with pytest.raises(TypeError, match="Unsupported data type:"):
            dicttoxml.convert(
                obj=CustomClass(),  # type: ignore[arg-type]
                ids=None,
                attr_type=False,
                item_func=lambda x: "item",
                cdata=False,
                item_wrap=True
            )

    def test_dict2xml_str_with_attr_type(self) -> None:
        """Test dict2xml_str with attr_type enabled."""
        item = {"key": "value"}
        result = dicttoxml.dict2xml_str(
            attr_type=True,
            attr={},
            item=item,
            item_func=lambda x: "item",
            cdata=False,
            item_name="test",
            item_wrap=False,
            parentIsList=False
        )
        assert 'type="dict"' in result

    def test_dict2xml_str_with_primitive_dict(self) -> None:
        """Test dict2xml_str with primitive dict value."""
        item = {"@val": {"nested": "value"}}
        result = dicttoxml.dict2xml_str(
            attr_type=False,
            attr={},
            item=item,
            item_func=lambda x: "item",
            cdata=False,
            item_name="test",
            item_wrap=False,
            parentIsList=False
        )
        assert "nested" in result

    def test_list2xml_str_with_attr_type(self) -> None:
        """Test list2xml_str with attr_type enabled."""
        item = ["value1", "value2"]
        result = dicttoxml.list2xml_str(
            attr_type=True,
            attr={},
            item=item,
            item_func=lambda x: "item",
            cdata=False,
            item_name="test",
            item_wrap=True
        )
        assert 'type="list"' in result

    def test_convert_dict_with_bool_value(self) -> None:
        """Test convert_dict with boolean value."""
        obj = {"flag": True}
        result = dicttoxml.convert_dict(
            obj=obj,
            ids=[],
            parent="root",
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=False
        )
        assert "<flag>true</flag>" == result

    def test_convert_dict_with_falsy_value(self) -> None:
        """Test convert_dict with falsy but not None value."""
        obj = {"empty": ""}
        result = dicttoxml.convert_dict(
            obj=obj,
            ids=[],
            parent="root",
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=False
        )
        assert "<empty></empty>" == result

    def test_convert_list_with_flat_item_name(self) -> None:
        """Test convert_list with item_name ending in @flat."""
        items = ["test"]
        result = dicttoxml.convert_list(
            items=items,
            ids=None,
            parent="root",
            attr_type=False,
            item_func=lambda x: x + "@flat",
            cdata=False,
            item_wrap=True
        )
        assert "<root>test</root>" == result

    def test_convert_list_with_bool_item(self) -> None:
        """Test convert_list with boolean item."""
        items = [True]
        result = dicttoxml.convert_list(
            items=items,
            ids=None,
            parent="root",
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert "<item>true</item>" == result

    def test_convert_list_with_datetime_item(self) -> None:
        """Test convert_list with datetime item."""
        dt = datetime.datetime(2023, 2, 15, 12, 30, 45)
        items = [dt]
        result = dicttoxml.convert_list(
            items=items,
            ids=None,
            parent="root",
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert "<item>2023-02-15T12:30:45</item>" == result

    def test_convert_list_with_sequence_item(self) -> None:
        """Test convert_list with sequence item."""
        items = [["nested", "list"]]
        result = dicttoxml.convert_list(
            items=items,
            ids=None,
            parent="root",
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=True
        )
        assert "<item><item>nested</item><item>list</item></item>" == result

    def test_dict2xml_str_with_primitive_dict_rawitem(self) -> None:
        """Test dict2xml_str with primitive dict as rawitem to trigger line 274."""
        # Create a case where rawitem is a dict and is_primitive_type returns True
        # This is tricky because normally dicts are not primitive types
        # We need to mock is_primitive_type to return True for a dict
        import json2xml.dicttoxml as module
        original_is_primitive = module.is_primitive_type

        def mock_is_primitive(val: Any) -> bool:
            if isinstance(val, dict) and val == {"test": "data"}:
                return True
            return original_is_primitive(val)

        module.is_primitive_type = mock_is_primitive
        try:
            item = {"@val": {"test": "data"}}
            result = dicttoxml.dict2xml_str(
                attr_type=False,
                attr={},
                item=item,
                item_func=lambda x: "item",
                cdata=False,
                item_name="test",
                item_wrap=False,
                parentIsList=False
            )
            assert "test" in result
        finally:
            module.is_primitive_type = original_is_primitive

    def test_convert_dict_with_falsy_value_line_400(self) -> None:
        """Test convert_dict with falsy value to trigger line 400."""
        # Line 400 is triggered when val is falsy but doesn't match previous type checks
        # We need a falsy value that is not: bool, number, string, has isoformat, dict, or Sequence

        # The simplest way is to use None itself, which will be falsy
        obj = {"none_key": None}

        result = dicttoxml.convert_dict(
            obj=obj,
            ids=[],
            parent="root",
            attr_type=False,
            item_func=lambda x: "item",
            cdata=False,
            item_wrap=False
        )

        # None should trigger the "elif not val:" branch and result in an empty element
        assert "<none_key></none_key>" == result

    def test_attrs_xml_escaping(self) -> None:
        """Test that @attrs values are properly XML-escaped."""
        # Test the specific case from the user's bug report
        info_dict = {
            'Info': {
                "@attrs": {
                    "Name": "systemSpec",
                    "HelpText": "spec version <here>"
                }
            }
        }
        result = dicttoxml.dicttoxml(info_dict, attr_type=False, item_wrap=False, root=False).decode('utf-8')
        expected = '<Info Name="systemSpec" HelpText="spec version &lt;here&gt;"></Info>'
        assert expected == result

    def test_attrs_comprehensive_xml_escaping(self) -> None:
        """Test comprehensive XML escaping in attributes."""
        data = {
            'Element': {
                "@attrs": {
                    "ampersand": "Tom & Jerry",
                    "less_than": "value < 10",
                    "greater_than": "value > 5",
                    "quotes": 'He said "Hello"',
                    "single_quotes": "It's working",
                    "mixed": "Tom & Jerry < 10 > 5 \"quoted\" 'apostrophe'"
                },
                "@val": "content"
            }
        }
        result = dicttoxml.dicttoxml(data, attr_type=False, item_wrap=False, root=False).decode('utf-8')

        # Check that all special characters are properly escaped in attributes
        assert 'ampersand="Tom &amp; Jerry"' in result
        assert 'less_than="value &lt; 10"' in result
        assert 'greater_than="value &gt; 5"' in result
        assert 'quotes="He said &quot;Hello&quot;"' in result
        assert 'single_quotes="It&apos;s working"' in result
        assert 'mixed="Tom &amp; Jerry &lt; 10 &gt; 5 &quot;quoted&quot; &apos;apostrophe&apos;"' in result

        # Verify the element content is also properly escaped
        assert ">content<" in result

    def test_attrs_empty_and_none_values(self) -> None:
        """Test attribute handling with empty and None values."""
        data = {
            'Element': {
                "@attrs": {
                    "empty": "",
                    "zero": 0,
                    "false": False
                }
            }
        }
        result = dicttoxml.dicttoxml(data, attr_type=False, item_wrap=False, root=False).decode('utf-8')

        assert 'empty=""' in result
        assert 'zero="0"' in result
        assert 'false="False"' in result

    def test_make_attrstring_function_directly(self) -> None:
        """Test the make_attrstring function directly."""
        from json2xml.dicttoxml import make_attrstring

        # Test basic escaping
        attrs = {
            "test": "value <here>",
            "ampersand": "Tom & Jerry",
            "quotes": 'Say "hello"'
        }
        result = make_attrstring(attrs)

        assert 'test="value &lt;here&gt;"' in result
        assert 'ampersand="Tom &amp; Jerry"' in result
        assert 'quotes="Say &quot;hello&quot;"' in result

        # Test empty attributes
        empty_attrs: dict[str, Any] = {}
        result = make_attrstring(empty_attrs)
        assert result == ""
