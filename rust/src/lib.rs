//! Fast native JSON to XML conversion for Python
//!
//! This module provides a high-performance Rust implementation of dicttoxml
//! that can be used as a drop-in replacement for the pure Python version.

#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};
/// Escape special XML characters in a string (allocating convenience wrapper).
#[inline]
pub fn escape_xml(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + s.len() / 10);
    push_escaped_attr(&mut out, s);
    out
}

/// Append text content with XML escaping matching the Python implementation.
/// Scans bytes for speed, copies clean slices in bulk.
#[inline]
pub fn push_escaped_text(out: &mut String, s: &str) {
    let mut last = 0;
    for (i, b) in s.bytes().enumerate() {
        let repl = match b {
            b'&' => "&amp;",
            b'"' => "&quot;",
            b'\'' => "&apos;",
            b'<' => "&lt;",
            b'>' => "&gt;",
            _ => continue,
        };
        out.push_str(&s[last..i]);
        out.push_str(repl);
        last = i + 1;
    }
    out.push_str(&s[last..]);
}

/// Append attribute value with full XML escaping (also escapes quotes).
#[inline]
pub fn push_escaped_attr(out: &mut String, s: &str) {
    let mut last = 0;
    for (i, b) in s.bytes().enumerate() {
        let repl = match b {
            b'&' => "&amp;",
            b'"' => "&quot;",
            b'\'' => "&apos;",
            b'<' => "&lt;",
            b'>' => "&gt;",
            _ => continue,
        };
        out.push_str(&s[last..i]);
        out.push_str(repl);
        last = i + 1;
    }
    out.push_str(&s[last..]);
}

/// Wrap content in CDATA section (allocating convenience wrapper).
#[inline]
pub fn wrap_cdata(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 12);
    push_cdata(&mut out, s);
    out
}

/// Append a CDATA section directly to the buffer.
#[inline]
pub fn push_cdata(out: &mut String, s: &str) {
    out.push_str("<![CDATA[");
    let mut start = 0;
    while let Some(i) = s[start..].find("]]>") {
        let abs = start + i;
        out.push_str(&s[start..abs]);
        out.push_str("]]]]><![CDATA[>");
        start = abs + 3;
    }
    out.push_str(&s[start..]);
    out.push_str("]]>");
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
    if key.len() >= 3 && key.as_bytes()[..3].eq_ignore_ascii_case(b"xml") {
        return false;
    }

    true
}

/// Make a valid XML name from a key, returning the tag name and the raw
/// (unescaped) original key when a fallback is needed. Escaping of the
/// attribute value is handled later by `make_attr_string`, so we must NOT
/// escape here to avoid double-escaping.
pub fn make_valid_xml_name(key: &str) -> (String, Option<(String, String)>) {
    // Already valid
    if is_valid_xml_name(key) {
        return (key.to_string(), None);
    }

    // Numeric key - prepend 'n'
    if key.bytes().all(|b| b.is_ascii_digit()) && !key.is_empty() {
        return (format!("n{}", key), None);
    }

    // Try replacing spaces with underscores
    let with_underscores = key.replace(' ', "_");
    if is_valid_xml_name(&with_underscores) {
        return (with_underscores, None);
    }

    // Fall back to using "key" with name attribute (raw value, escaped later)
    ("key".to_string(), Some(("name".to_string(), key.to_string())))
}

/// Build an attribute string from key-value pairs (allocating convenience wrapper).
pub fn make_attr_string(attrs: &[(String, String)]) -> String {
    let mut out = String::new();
    push_attrs(&mut out, attrs);
    out
}

/// Append XML attributes directly to a buffer.
#[inline]
fn push_attrs(out: &mut String, attrs: &[(String, String)]) {
    for (k, v) in attrs {
        out.push(' ');
        out.push_str(k);
        out.push_str("=\"");
        push_escaped_attr(out, v);
        out.push('"');
    }
}

/// Write opening tag with optional name and type attributes directly to buffer.
#[cfg(feature = "python")]
#[inline]
fn write_open_tag(out: &mut String, tag: &str, name_attr: Option<&str>, type_attr: Option<&str>) {
    out.push('<');
    out.push_str(tag);
    if let Some(name) = name_attr {
        out.push_str(" name=\"");
        push_escaped_attr(out, name);
        out.push('"');
    }
    if let Some(ty) = type_attr {
        out.push_str(" type=\"");
        out.push_str(ty);
        out.push('"');
    }
    out.push('>');
}

/// Write a closing tag directly to buffer.
#[cfg(feature = "python")]
#[inline]
fn write_close_tag(out: &mut String, tag: &str) {
    out.push_str("</");
    out.push_str(tag);
    out.push('>');
}

/// Configuration for XML conversion
#[cfg(feature = "python")]
#[derive(Copy, Clone)]
struct ConvertConfig {
    attr_type: bool,
    cdata: bool,
    item_wrap: bool,
    list_headers: bool,
}

#[cfg(feature = "python")]
use pyo3::PyResult;

/// Return `Some(type_name)` when `attr_type` is enabled.
#[cfg(feature = "python")]
#[inline]
fn type_attr<'a>(cfg: &ConvertConfig, ty: &'a str) -> Option<&'a str> {
    if cfg.attr_type { Some(ty) } else { None }
}

/// Single unified type-dispatch writer. Every Python value goes through here
/// exactly once, writing directly into the shared output buffer.
#[cfg(feature = "python")]
fn write_value(
    py: Python<'_>,
    out: &mut String,
    obj: &Bound<'_, PyAny>,
    tag: &str,
    name_attr: Option<&str>,
    cfg: &ConvertConfig,
    wrap_container: bool,
) -> PyResult<()> {
    // None
    if obj.is_none() {
        write_open_tag(out, tag, name_attr, type_attr(cfg, "null"));
        write_close_tag(out, tag);
        return Ok(());
    }

    // Bool (must check before int since bool is subclass of int in Python)
    if obj.is_instance_of::<PyBool>() {
        let v: bool = obj.extract()?;
        write_open_tag(out, tag, name_attr, type_attr(cfg, "bool"));
        out.push_str(if v { "true" } else { "false" });
        write_close_tag(out, tag);
        return Ok(());
    }

    // Int - try i64 first, fall back to string for large integers
    if obj.is_instance_of::<PyInt>() {
        write_open_tag(out, tag, name_attr, type_attr(cfg, "int"));
        match obj.extract::<i64>() {
            Ok(v) => { out.push_str(&v.to_string()); }
            Err(_) => { out.push_str(obj.str()?.to_str()?); }
        }
        write_close_tag(out, tag);
        return Ok(());
    }

    // Float - use Python's str() for parity (Rust renders 1.0 as "1")
    if obj.is_instance_of::<PyFloat>() {
        write_open_tag(out, tag, name_attr, type_attr(cfg, "float"));
        out.push_str(obj.str()?.to_str()?);
        write_close_tag(out, tag);
        return Ok(());
    }

    // String
    if let Ok(py_str) = obj.cast::<PyString>() {
        let s = py_str.to_str()?;
        write_open_tag(out, tag, name_attr, type_attr(cfg, "str"));
        if cfg.cdata {
            push_cdata(out, s);
        } else {
            push_escaped_text(out, s);
        }
        write_close_tag(out, tag);
        return Ok(());
    }

    // Dict
    if let Ok(dict) = obj.cast::<PyDict>() {
        if wrap_container {
            write_open_tag(out, tag, name_attr, type_attr(cfg, "dict"));
        }
        write_dict_contents(py, out, dict, cfg)?;
        if wrap_container {
            write_close_tag(out, tag);
        }
        return Ok(());
    }

    // List
    if let Ok(list) = obj.cast::<PyList>() {
        if wrap_container {
            write_open_tag(out, tag, name_attr, type_attr(cfg, "list"));
        }
        write_list_contents(py, out, list, tag, cfg)?;
        if wrap_container {
            write_close_tag(out, tag);
        }
        return Ok(());
    }

    // Other iterables (tuples, generators, etc.)
    if let Ok(iter) = obj.try_iter() {
        let items: Vec<Bound<'_, PyAny>> = iter.collect::<PyResult<_>>()?;
        let list = PyList::new(py, &items)?;
        if wrap_container {
            write_open_tag(out, tag, name_attr, type_attr(cfg, "list"));
        }
        write_list_contents(py, out, &list, tag, cfg)?;
        if wrap_container {
            write_close_tag(out, tag);
        }
        return Ok(());
    }

    // Fallback: convert to string via Python's str()
    let py_str = obj.str()?;
    let s = py_str.to_str()?;
    write_open_tag(out, tag, name_attr, type_attr(cfg, "str"));
    if cfg.cdata {
        push_cdata(out, s);
    } else {
        push_escaped_text(out, s);
    }
    write_close_tag(out, tag);
    Ok(())
}

/// Write all key-value pairs of a dict into the buffer.
#[cfg(feature = "python")]
fn write_dict_contents(
    py: Python<'_>,
    out: &mut String,
    dict: &Bound<'_, PyDict>,
    cfg: &ConvertConfig,
) -> PyResult<()> {
    for (key, val) in dict.iter() {
        let key_str: String = key.str()?.extract()?;
        let (xml_key, name_attr_pair) = make_valid_xml_name(&key_str);
        let name_attr = name_attr_pair.as_ref().map(|(_, v)| v.as_str());

        // Lists in dicts get special wrapping treatment
        if let Ok(list) = val.cast::<PyList>() {
            if cfg.item_wrap {
                write_open_tag(out, &xml_key, name_attr, type_attr(cfg, "list"));
                write_list_contents(py, out, list, &xml_key, cfg)?;
                write_close_tag(out, &xml_key);
            } else {
                write_list_contents(py, out, list, &xml_key, cfg)?;
            }
        } else {
            write_value(py, out, &val, &xml_key, name_attr, cfg, true)?;
        }
    }
    Ok(())
}

/// Write all items of a list into the buffer.
#[cfg(feature = "python")]
fn write_list_contents(
    py: Python<'_>,
    out: &mut String,
    list: &Bound<'_, PyList>,
    parent: &str,
    cfg: &ConvertConfig,
) -> PyResult<()> {
    let tag_name = if cfg.list_headers {
        parent
    } else if cfg.item_wrap {
        "item"
    } else {
        parent
    };

    for item in list.iter() {
        // Dicts inside lists have special wrapping logic
        if let Ok(dict) = item.cast::<PyDict>() {
            if cfg.item_wrap || cfg.list_headers {
                write_open_tag(out, tag_name, None, type_attr(cfg, "dict"));
                write_dict_contents(py, out, dict, cfg)?;
                write_close_tag(out, tag_name);
            } else {
                write_dict_contents(py, out, dict, cfg)?;
            }
        } else {
            write_value(py, out, &item, tag_name, None, cfg, true)?;
        }
    }
    Ok(())
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
    if !is_valid_xml_name(custom_root) {
        return Err(PyValueError::new_err(format!(
            "Invalid XML root element name: '{}'",
            custom_root
        )));
    }

    let config = ConvertConfig {
        attr_type,
        cdata,
        item_wrap,
        list_headers,
    };

    let mut out = String::new();

    if root {
        out.push_str("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>");
        out.push('<');
        out.push_str(custom_root);
        out.push('>');
    }

    if let Ok(dict) = obj.cast::<PyDict>() {
        write_dict_contents(py, &mut out, dict, &config)?;
    } else if let Ok(list) = obj.cast::<PyList>() {
        write_list_contents(py, &mut out, list, custom_root, &config)?;
    } else {
        write_value(py, &mut out, obj, custom_root, None, &config, true)?;
    }

    if root {
        out.push_str("</");
        out.push_str(custom_root);
        out.push('>');
    }

    Ok(out.into_bytes())
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
        fn returns_raw_key_for_invalid_names() {
            // make_valid_xml_name must return the raw key, not escaped.
            // Escaping happens later in make_attr_string to avoid double-escaping.
            let (name, attr) = make_valid_xml_name("tag&name");
            assert_eq!(name, "key");
            assert_eq!(attr, Some(("name".to_string(), "tag&name".to_string())));
        }

        #[test]
        fn double_escape_does_not_happen() {
            // End-to-end: make_valid_xml_name + make_attr_string should produce
            // a single level of escaping, not &amp;amp;
            let (name, attr) = make_valid_xml_name("tag&name");
            assert_eq!(name, "key");
            let attrs = attr.map(|(k, v)| vec![(k, v)]).unwrap_or_default();
            let attr_string = make_attr_string(&attrs);
            assert_eq!(attr_string, " name=\"tag&amp;name\"");
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

    mod push_escaped_text_tests {
        use super::*;

        #[test]
        fn escapes_special_chars_in_text() {
            let mut out = String::new();
            push_escaped_text(&mut out, "a < b & c > d");
            assert_eq!(out, "a &lt; b &amp; c &gt; d");
        }

        #[test]
        fn escapes_quotes_in_text() {
            let mut out = String::new();
            push_escaped_text(&mut out, "say \"hello\" & 'bye'");
            assert_eq!(out, "say &quot;hello&quot; &amp; &apos;bye&apos;");
        }

        #[test]
        fn handles_empty_string() {
            let mut out = String::new();
            push_escaped_text(&mut out, "");
            assert_eq!(out, "");
        }

        #[test]
        fn handles_no_special_chars() {
            let mut out = String::new();
            push_escaped_text(&mut out, "plain text 123");
            assert_eq!(out, "plain text 123");
        }

        #[test]
        fn handles_unicode() {
            let mut out = String::new();
            push_escaped_text(&mut out, "café & thé");
            assert_eq!(out, "café &amp; thé");
        }
    }

    mod push_escaped_attr_tests {
        use super::*;

        #[test]
        fn escapes_quotes_and_special_chars() {
            let mut out = String::new();
            push_escaped_attr(&mut out, "a\"b'c&d<e>f");
            assert_eq!(out, "a&quot;b&apos;c&amp;d&lt;e&gt;f");
        }
    }

    mod push_cdata_tests {
        use super::*;

        #[test]
        fn wraps_simple_string() {
            let mut out = String::new();
            push_cdata(&mut out, "hello");
            assert_eq!(out, "<![CDATA[hello]]>");
        }

        #[test]
        fn escapes_cdata_end_sequence() {
            let mut out = String::new();
            push_cdata(&mut out, "foo]]>bar");
            assert_eq!(out, "<![CDATA[foo]]]]><![CDATA[>bar]]>");
        }

        #[test]
        fn handles_multiple_cdata_end_sequences() {
            let mut out = String::new();
            push_cdata(&mut out, "a]]>b]]>c");
            assert_eq!(out, "<![CDATA[a]]]]><![CDATA[>b]]]]><![CDATA[>c]]>");
        }
    }
}
