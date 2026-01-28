//! Fast native JSON to XML conversion for Python
//!
//! This module provides a high-performance Rust implementation of dicttoxml
//! that can be used as a drop-in replacement for the pure Python version.

#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};
use std::fmt::Write;

/// Escape special XML characters in a string.
/// This is one of the hottest paths - optimized for single-pass processing.
#[inline]
pub fn escape_xml(s: &str) -> String {
    let mut result = String::with_capacity(s.len() + s.len() / 10);
    for c in s.chars() {
        match c {
            '&' => result.push_str("&amp;"),
            '"' => result.push_str("&quot;"),
            '\'' => result.push_str("&apos;"),
            '<' => result.push_str("&lt;"),
            '>' => result.push_str("&gt;"),
            _ => result.push(c),
        }
    }
    result
}

/// Wrap content in CDATA section
#[inline]
pub fn wrap_cdata(s: &str) -> String {
    let escaped = s.replace("]]>", "]]]]><![CDATA[>");
    format!("<![CDATA[{}]]>", escaped)
}

/// Check if a key is a valid XML element name (simplified check)
/// Full validation would require XML parsing, but this catches common issues
pub fn is_valid_xml_name(key: &str) -> bool {
    if key.is_empty() {
        return false;
    }

    let mut chars = key.chars();

    // First character must be letter or underscore
    match chars.next() {
        Some(c) if c.is_alphabetic() || c == '_' => {}
        _ => return false,
    }

    // Remaining characters can be letters, digits, hyphens, underscores, or periods
    for c in chars {
        if !(c.is_alphanumeric() || c == '-' || c == '_' || c == '.' || c == ':') {
            return false;
        }
    }

    // Names starting with "xml" (case-insensitive) are reserved
    !key.to_lowercase().starts_with("xml")
}

/// Make a valid XML name from a key, returning the key and any attributes
pub fn make_valid_xml_name(key: &str) -> (String, Option<(String, String)>) {
    let escaped = escape_xml(key);

    // Already valid
    if is_valid_xml_name(&escaped) {
        return (escaped, None);
    }

    // Numeric key - prepend 'n'
    if escaped.chars().all(|c| c.is_ascii_digit()) {
        return (format!("n{}", escaped), None);
    }

    // Try replacing spaces with underscores
    let with_underscores = escaped.replace(' ', "_");
    if is_valid_xml_name(&with_underscores) {
        return (with_underscores, None);
    }

    // Fall back to using "key" with name attribute
    ("key".to_string(), Some(("name".to_string(), escaped)))
}

/// Build an attribute string from key-value pairs
pub fn make_attr_string(attrs: &[(String, String)]) -> String {
    if attrs.is_empty() {
        return String::new();
    }
    let mut result = String::new();
    for (k, v) in attrs {
        write!(result, " {}=\"{}\"", k, escape_xml(v)).unwrap();
    }
    result
}

/// Configuration for XML conversion
#[cfg(feature = "python")]
struct ConvertConfig {
    attr_type: bool,
    cdata: bool,
    item_wrap: bool,
    list_headers: bool,
}

#[cfg(feature = "python")]
use pyo3::PyResult;

/// Convert a Python value to XML string
#[cfg(feature = "python")]
fn convert_value(
    py: Python<'_>,
    obj: &Bound<'_, PyAny>,
    parent: &str,
    config: &ConvertConfig,
    item_name: &str,
) -> PyResult<String> {
    // Handle None
    if obj.is_none() {
        return convert_none(item_name, config);
    }

    // Handle bool (must check before int since bool is subclass of int in Python)
    if obj.is_instance_of::<PyBool>() {
        let val: bool = obj.extract()?;
        return convert_bool(item_name, val, config);
    }

    // Handle int - try i64 first, fall back to string for large integers
    if obj.is_instance_of::<PyInt>() {
        let val_str = match obj.extract::<i64>() {
            Ok(val) => val.to_string(),
            Err(_) => obj.str()?.extract::<String>()?, // Fall back for big ints
        };
        return convert_number(item_name, &val_str, "int", config);
    }

    // Handle float
    if obj.is_instance_of::<PyFloat>() {
        let val: f64 = obj.extract()?;
        return convert_number(item_name, &val.to_string(), "float", config);
    }

    // Handle string
    if obj.is_instance_of::<PyString>() {
        let val: String = obj.extract()?;
        return convert_string(item_name, &val, config);
    }

    // Handle dict
    if obj.is_instance_of::<PyDict>() {
        let dict: &Bound<'_, PyDict> = obj.cast()?;
        return convert_dict(py, dict, parent, config);
    }

    // Handle list
    if obj.is_instance_of::<PyList>() {
        let list: &Bound<'_, PyList> = obj.cast()?;
        return convert_list(py, list, parent, config);
    }

    // Handle other sequences (tuples, etc.) - check if iterable via try_iter
    if let Ok(iter) = obj.try_iter() {
        let items: Vec<Bound<'_, PyAny>> = iter.filter_map(|r| r.ok()).collect();
        let list = PyList::new(py, &items)?;
        return convert_list(py, &list, parent, config);
    }

    // Fallback: convert to string
    let val: String = obj.str()?.extract()?;
    convert_string(item_name, &val, config)
}

/// Convert a string value to XML
#[cfg(feature = "python")]
fn convert_string(key: &str, val: &str, config: &ConvertConfig) -> PyResult<String> {
    let (xml_key, name_attr) = make_valid_xml_name(key);
    let mut attrs = Vec::new();

    if let Some((k, v)) = name_attr {
        attrs.push((k, v));
    }
    if config.attr_type {
        attrs.push(("type".to_string(), "str".to_string()));
    }

    let attr_string = make_attr_string(&attrs);
    let content = if config.cdata {
        wrap_cdata(val)
    } else {
        escape_xml(val)
    };

    Ok(format!(
        "<{}{}>{}</{}>",
        xml_key, attr_string, content, xml_key
    ))
}

/// Convert a number value to XML
#[cfg(feature = "python")]
fn convert_number(
    key: &str,
    val: &str,
    type_name: &str,
    config: &ConvertConfig,
) -> PyResult<String> {
    let (xml_key, name_attr) = make_valid_xml_name(key);
    let mut attrs = Vec::new();

    if let Some((k, v)) = name_attr {
        attrs.push((k, v));
    }
    if config.attr_type {
        attrs.push(("type".to_string(), type_name.to_string()));
    }

    let attr_string = make_attr_string(&attrs);
    Ok(format!("<{}{}>{}</{}>", xml_key, attr_string, val, xml_key))
}

/// Convert a boolean value to XML
#[cfg(feature = "python")]
fn convert_bool(key: &str, val: bool, config: &ConvertConfig) -> PyResult<String> {
    let (xml_key, name_attr) = make_valid_xml_name(key);
    let mut attrs = Vec::new();

    if let Some((k, v)) = name_attr {
        attrs.push((k, v));
    }
    if config.attr_type {
        attrs.push(("type".to_string(), "bool".to_string()));
    }

    let attr_string = make_attr_string(&attrs);
    let bool_str = if val { "true" } else { "false" };
    Ok(format!(
        "<{}{}>{}</{}>",
        xml_key, attr_string, bool_str, xml_key
    ))
}

/// Convert a None value to XML
#[cfg(feature = "python")]
fn convert_none(key: &str, config: &ConvertConfig) -> PyResult<String> {
    let (xml_key, name_attr) = make_valid_xml_name(key);
    let mut attrs = Vec::new();

    if let Some((k, v)) = name_attr {
        attrs.push((k, v));
    }
    if config.attr_type {
        attrs.push(("type".to_string(), "null".to_string()));
    }

    let attr_string = make_attr_string(&attrs);
    Ok(format!("<{}{}></{}>", xml_key, attr_string, xml_key))
}

/// Convert a dictionary to XML
#[cfg(feature = "python")]
fn convert_dict(
    py: Python<'_>,
    dict: &Bound<'_, PyDict>,
    _parent: &str,
    config: &ConvertConfig,
) -> PyResult<String> {
    let mut output = String::new();

    for (key, val) in dict.iter() {
        let key_str: String = key.str()?.extract()?;
        let (xml_key, name_attr) = make_valid_xml_name(&key_str);

        // Handle bool (must check before int)
        if val.is_instance_of::<PyBool>() {
            let bool_val: bool = val.extract()?;
            let mut attrs = Vec::new();
            if let Some((k, v)) = name_attr {
                attrs.push((k, v));
            }
            if config.attr_type {
                attrs.push(("type".to_string(), "bool".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            let bool_str = if bool_val { "true" } else { "false" };
            write!(
                output,
                "<{}{}>{}</{}>",
                xml_key, attr_string, bool_str, xml_key
            )
            .unwrap();
        }
        // Handle int - try i64 first, fall back to string for large integers
        else if val.is_instance_of::<PyInt>() {
            let int_str = match val.extract::<i64>() {
                Ok(v) => v.to_string(),
                Err(_) => val.str()?.extract::<String>()?,
            };
            let mut attrs = Vec::new();
            if let Some((k, v)) = name_attr {
                attrs.push((k, v));
            }
            if config.attr_type {
                attrs.push(("type".to_string(), "int".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            write!(
                output,
                "<{}{}>{}</{}>",
                xml_key, attr_string, int_str, xml_key
            )
            .unwrap();
        }
        // Handle float
        else if val.is_instance_of::<PyFloat>() {
            let float_val: f64 = val.extract()?;
            let mut attrs = Vec::new();
            if let Some((k, v)) = name_attr {
                attrs.push((k, v));
            }
            if config.attr_type {
                attrs.push(("type".to_string(), "float".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            write!(
                output,
                "<{}{}>{}</{}>",
                xml_key, attr_string, float_val, xml_key
            )
            .unwrap();
        }
        // Handle string
        else if val.is_instance_of::<PyString>() {
            let str_val: String = val.extract()?;
            let mut attrs = Vec::new();
            if let Some((k, v)) = name_attr {
                attrs.push((k, v));
            }
            if config.attr_type {
                attrs.push(("type".to_string(), "str".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            let content = if config.cdata {
                wrap_cdata(&str_val)
            } else {
                escape_xml(&str_val)
            };
            write!(
                output,
                "<{}{}>{}</{}>",
                xml_key, attr_string, content, xml_key
            )
            .unwrap();
        }
        // Handle None
        else if val.is_none() {
            let mut attrs = Vec::new();
            if let Some((k, v)) = name_attr {
                attrs.push((k, v));
            }
            if config.attr_type {
                attrs.push(("type".to_string(), "null".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            write!(output, "<{}{}></{}>", xml_key, attr_string, xml_key).unwrap();
        }
        // Handle nested dict
        else if val.is_instance_of::<PyDict>() {
            let nested_dict: &Bound<'_, PyDict> = val.cast()?;
            let mut attrs = Vec::new();
            if let Some((k, v)) = name_attr {
                attrs.push((k, v));
            }
            if config.attr_type {
                attrs.push(("type".to_string(), "dict".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            let inner = convert_dict(py, nested_dict, &xml_key, config)?;
            write!(
                output,
                "<{}{}>{}</{}>",
                xml_key, attr_string, inner, xml_key
            )
            .unwrap();
        }
        // Handle list
        else if val.is_instance_of::<PyList>() {
            let list: &Bound<'_, PyList> = val.cast()?;
            let list_output = convert_list(py, list, &xml_key, config)?;

            if config.item_wrap {
                let mut attrs = Vec::new();
                if let Some((k, v)) = name_attr {
                    attrs.push((k, v));
                }
                if config.attr_type {
                    attrs.push(("type".to_string(), "list".to_string()));
                }
                let attr_string = make_attr_string(&attrs);
                write!(
                    output,
                    "<{}{}>{}</{}>",
                    xml_key, attr_string, list_output, xml_key
                )
                .unwrap();
            } else {
                output.push_str(&list_output);
            }
        }
        // Fallback: convert to string
        else {
            let str_val: String = val.str()?.extract()?;
            let mut attrs = Vec::new();
            if let Some((k, v)) = name_attr {
                attrs.push((k, v));
            }
            if config.attr_type {
                attrs.push(("type".to_string(), "str".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            let content = if config.cdata {
                wrap_cdata(&str_val)
            } else {
                escape_xml(&str_val)
            };
            write!(
                output,
                "<{}{}>{}</{}>",
                xml_key, attr_string, content, xml_key
            )
            .unwrap();
        }
    }

    Ok(output)
}

/// Convert a list to XML
#[cfg(feature = "python")]
fn convert_list(
    py: Python<'_>,
    list: &Bound<'_, PyList>,
    parent: &str,
    config: &ConvertConfig,
) -> PyResult<String> {
    let mut output = String::new();
    let item_name = "item";

    for item in list.iter() {
        let tag_name = if config.item_wrap || config.list_headers {
            if config.list_headers {
                parent
            } else {
                item_name
            }
        } else {
            parent
        };

        // Handle bool (must check before int)
        if item.is_instance_of::<PyBool>() {
            let bool_val: bool = item.extract()?;
            let mut attrs = Vec::new();
            if config.attr_type {
                attrs.push(("type".to_string(), "bool".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            let bool_str = if bool_val { "true" } else { "false" };
            write!(
                output,
                "<{}{}>{}</{}>",
                tag_name, attr_string, bool_str, tag_name
            )
            .unwrap();
        }
        // Handle int - try i64 first, fall back to string for large integers
        else if item.is_instance_of::<PyInt>() {
            let int_str = match item.extract::<i64>() {
                Ok(v) => v.to_string(),
                Err(_) => item.str()?.extract::<String>()?,
            };
            let mut attrs = Vec::new();
            if config.attr_type {
                attrs.push(("type".to_string(), "int".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            write!(
                output,
                "<{}{}>{}</{}>",
                tag_name, attr_string, int_str, tag_name
            )
            .unwrap();
        }
        // Handle float
        else if item.is_instance_of::<PyFloat>() {
            let float_val: f64 = item.extract()?;
            let mut attrs = Vec::new();
            if config.attr_type {
                attrs.push(("type".to_string(), "float".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            write!(
                output,
                "<{}{}>{}</{}>",
                tag_name, attr_string, float_val, tag_name
            )
            .unwrap();
        }
        // Handle string
        else if item.is_instance_of::<PyString>() {
            let str_val: String = item.extract()?;
            let mut attrs = Vec::new();
            if config.attr_type {
                attrs.push(("type".to_string(), "str".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            let content = if config.cdata {
                wrap_cdata(&str_val)
            } else {
                escape_xml(&str_val)
            };
            write!(
                output,
                "<{}{}>{}</{}>",
                tag_name, attr_string, content, tag_name
            )
            .unwrap();
        }
        // Handle None
        else if item.is_none() {
            let mut attrs = Vec::new();
            if config.attr_type {
                attrs.push(("type".to_string(), "null".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            write!(output, "<{}{}></{}>", tag_name, attr_string, tag_name).unwrap();
        }
        // Handle nested dict
        else if item.is_instance_of::<PyDict>() {
            let nested_dict: &Bound<'_, PyDict> = item.cast()?;
            let inner = convert_dict(py, nested_dict, tag_name, config)?;

            if config.item_wrap || config.list_headers {
                let mut attrs = Vec::new();
                if config.attr_type {
                    attrs.push(("type".to_string(), "dict".to_string()));
                }
                let attr_string = make_attr_string(&attrs);
                write!(
                    output,
                    "<{}{}>{}</{}>",
                    tag_name, attr_string, inner, tag_name
                )
                .unwrap();
            } else {
                output.push_str(&inner);
            }
        }
        // Handle nested list
        else if item.is_instance_of::<PyList>() {
            let nested_list: &Bound<'_, PyList> = item.cast()?;
            let inner = convert_list(py, nested_list, tag_name, config)?;

            let mut attrs = Vec::new();
            if config.attr_type {
                attrs.push(("type".to_string(), "list".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            write!(
                output,
                "<{}{}>{}</{}>",
                tag_name, attr_string, inner, tag_name
            )
            .unwrap();
        }
        // Fallback
        else {
            let str_val: String = item.str()?.extract()?;
            let mut attrs = Vec::new();
            if config.attr_type {
                attrs.push(("type".to_string(), "str".to_string()));
            }
            let attr_string = make_attr_string(&attrs);
            let content = if config.cdata {
                wrap_cdata(&str_val)
            } else {
                escape_xml(&str_val)
            };
            write!(
                output,
                "<{}{}>{}</{}>",
                tag_name, attr_string, content, tag_name
            )
            .unwrap();
        }
    }

    Ok(output)
}

/// Convert a Python dict/list to XML bytes.
///
/// This is a high-performance Rust implementation of dicttoxml.
///
/// Args:
///     obj: The Python object to convert (dict or list)
///     root: Whether to include XML declaration and root element (default: True)
///     custom_root: The name of the root element (default: "root")
///     attr_type: Whether to include type attributes (default: True)
///     item_wrap: Whether to wrap list items in <item> tags (default: True)
///     cdata: Whether to wrap string values in CDATA sections (default: False)
///     list_headers: Whether to repeat parent tag for each list item (default: False)
///
/// Returns:
///     bytes: The XML representation of the input object
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (obj, root=true, custom_root="root", attr_type=true, item_wrap=true, cdata=false, list_headers=false))]
#[allow(clippy::too_many_arguments)]
fn dicttoxml(
    py: Python<'_>,
    obj: &Bound<'_, PyAny>,
    root: bool,
    custom_root: &str,
    attr_type: bool,
    item_wrap: bool,
    cdata: bool,
    list_headers: bool,
) -> PyResult<Vec<u8>> {
    let config = ConvertConfig {
        attr_type,
        cdata,
        item_wrap,
        list_headers,
    };

    let content = if obj.is_instance_of::<PyDict>() {
        let dict: &Bound<'_, PyDict> = obj.cast()?;
        convert_dict(py, dict, custom_root, &config)?
    } else if obj.is_instance_of::<PyList>() {
        let list: &Bound<'_, PyList> = obj.cast()?;
        convert_list(py, list, custom_root, &config)?
    } else {
        convert_value(py, obj, custom_root, &config, custom_root)?
    };

    let output = if root {
        format!(
            "<?xml version=\"1.0\" encoding=\"UTF-8\" ?><{}>{}</{}>",
            custom_root, content, custom_root
        )
    } else {
        content
    };

    Ok(output.into_bytes())
}

/// Fast XML string escaping.
///
/// Escapes &, ", ', <, > characters for XML.
#[cfg(feature = "python")]
#[pyfunction]
fn escape_xml_py(s: &str) -> String {
    escape_xml(s)
}

/// Wrap a string in CDATA section.
#[cfg(feature = "python")]
#[pyfunction]
fn wrap_cdata_py(s: &str) -> String {
    wrap_cdata(s)
}

/// A Python module implemented in Rust.
#[cfg(feature = "python")]
#[pymodule]
fn json2xml_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(dicttoxml, m)?)?;
    m.add_function(wrap_pyfunction!(escape_xml_py, m)?)?;
    m.add_function(wrap_pyfunction!(wrap_cdata_py, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    mod escape_xml_tests {
        use super::*;

        #[test]
        fn escapes_ampersand() {
            assert_eq!(escape_xml("foo & bar"), "foo &amp; bar");
        }

        #[test]
        fn escapes_double_quote() {
            assert_eq!(escape_xml("say \"hello\""), "say &quot;hello&quot;");
        }

        #[test]
        fn escapes_single_quote() {
            assert_eq!(escape_xml("it's fine"), "it&apos;s fine");
        }

        #[test]
        fn escapes_less_than() {
            assert_eq!(escape_xml("a < b"), "a &lt; b");
        }

        #[test]
        fn escapes_greater_than() {
            assert_eq!(escape_xml("a > b"), "a &gt; b");
        }

        #[test]
        fn escapes_all_special_chars() {
            assert_eq!(
                escape_xml("<tag attr=\"val\" & 'x'>"),
                "&lt;tag attr=&quot;val&quot; &amp; &apos;x&apos;&gt;"
            );
        }

        #[test]
        fn handles_empty_string() {
            assert_eq!(escape_xml(""), "");
        }

        #[test]
        fn handles_no_special_chars() {
            assert_eq!(escape_xml("hello world 123"), "hello world 123");
        }

        #[test]
        fn handles_unicode() {
            assert_eq!(escape_xml("café & thé"), "café &amp; thé");
        }
    }

    mod wrap_cdata_tests {
        use super::*;

        #[test]
        fn wraps_simple_string() {
            assert_eq!(wrap_cdata("hello"), "<![CDATA[hello]]>");
        }

        #[test]
        fn wraps_empty_string() {
            assert_eq!(wrap_cdata(""), "<![CDATA[]]>");
        }

        #[test]
        fn escapes_cdata_end_sequence() {
            assert_eq!(wrap_cdata("foo]]>bar"), "<![CDATA[foo]]]]><![CDATA[>bar]]>");
        }

        #[test]
        fn handles_multiple_cdata_end_sequences() {
            assert_eq!(
                wrap_cdata("a]]>b]]>c"),
                "<![CDATA[a]]]]><![CDATA[>b]]]]><![CDATA[>c]]>"
            );
        }

        #[test]
        fn handles_special_xml_chars() {
            assert_eq!(
                wrap_cdata("<tag & \"attr\">"),
                "<![CDATA[<tag & \"attr\">]]>"
            );
        }
    }

    mod is_valid_xml_name_tests {
        use super::*;

        #[test]
        fn accepts_simple_name() {
            assert!(is_valid_xml_name("element"));
        }

        #[test]
        fn accepts_name_with_underscore_prefix() {
            assert!(is_valid_xml_name("_element"));
        }

        #[test]
        fn accepts_name_with_numbers() {
            assert!(is_valid_xml_name("item123"));
        }

        #[test]
        fn accepts_name_with_hyphens() {
            assert!(is_valid_xml_name("my-element"));
        }

        #[test]
        fn accepts_name_with_dots() {
            assert!(is_valid_xml_name("my.element"));
        }

        #[test]
        fn accepts_name_with_colons() {
            assert!(is_valid_xml_name("ns:element"));
        }

        #[test]
        fn rejects_empty_string() {
            assert!(!is_valid_xml_name(""));
        }

        #[test]
        fn rejects_name_starting_with_number() {
            assert!(!is_valid_xml_name("123element"));
        }

        #[test]
        fn rejects_name_starting_with_hyphen() {
            assert!(!is_valid_xml_name("-element"));
        }

        #[test]
        fn rejects_name_with_spaces() {
            assert!(!is_valid_xml_name("my element"));
        }

        #[test]
        fn rejects_xml_prefix_lowercase() {
            assert!(!is_valid_xml_name("xmlelement"));
        }

        #[test]
        fn rejects_xml_prefix_uppercase() {
            assert!(!is_valid_xml_name("XMLelement"));
        }

        #[test]
        fn rejects_xml_prefix_mixed_case() {
            assert!(!is_valid_xml_name("XmLelement"));
        }
    }

    mod make_valid_xml_name_tests {
        use super::*;

        #[test]
        fn returns_valid_name_unchanged() {
            let (name, attr) = make_valid_xml_name("element");
            assert_eq!(name, "element");
            assert!(attr.is_none());
        }

        #[test]
        fn prepends_n_to_numeric_key() {
            let (name, attr) = make_valid_xml_name("123");
            assert_eq!(name, "n123");
            assert!(attr.is_none());
        }

        #[test]
        fn replaces_spaces_with_underscores() {
            let (name, attr) = make_valid_xml_name("my element");
            assert_eq!(name, "my_element");
            assert!(attr.is_none());
        }

        #[test]
        fn falls_back_to_key_with_name_attr() {
            let (name, attr) = make_valid_xml_name("-invalid");
            assert_eq!(name, "key");
            assert_eq!(attr, Some(("name".to_string(), "-invalid".to_string())));
        }

        #[test]
        fn escapes_special_chars_in_name() {
            let (name, attr) = make_valid_xml_name("tag&name");
            assert_eq!(name, "key");
            assert_eq!(attr, Some(("name".to_string(), "tag&amp;name".to_string())));
        }
    }

    mod make_attr_string_tests {
        use super::*;

        #[test]
        fn returns_empty_for_empty_attrs() {
            assert_eq!(make_attr_string(&[]), "");
        }

        #[test]
        fn formats_single_attr() {
            let attrs = vec![("type".to_string(), "str".to_string())];
            assert_eq!(make_attr_string(&attrs), " type=\"str\"");
        }

        #[test]
        fn formats_multiple_attrs() {
            let attrs = vec![
                ("name".to_string(), "foo".to_string()),
                ("type".to_string(), "int".to_string()),
            ];
            assert_eq!(make_attr_string(&attrs), " name=\"foo\" type=\"int\"");
        }

        #[test]
        fn escapes_attr_values() {
            let attrs = vec![("name".to_string(), "foo & bar".to_string())];
            assert_eq!(make_attr_string(&attrs), " name=\"foo &amp; bar\"");
        }
    }
}
