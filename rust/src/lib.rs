//! Optional native JSON-to-XML backend for Python.
//!
//! The Python selector uses this crate only for dict/list requests whose options it can
//! preserve. Unsupported features remain on the compatibility-focused Python serializer.

#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::{PyBool, PyBytes, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};
#[cfg(feature = "python")]
use std::io::{BufWriter, Write};

use std::borrow::Cow;

#[cfg(feature = "python")]
const OUTPUT_BUFFER_SIZE: usize = 16 * 1024;

// Restarted searches have lower setup cost for sparse escapes. After four matches, the
// monotonic iterators keep dense inputs linear instead of repeatedly scanning the same bytes.
const SPARSE_ESCAPE_SCAN_LIMIT: u8 = 4;

#[inline]
fn invalid_xml_char(s: &str) -> Option<char> {
    s.chars().find(|character| {
        let codepoint = u32::from(*character);
        !matches!(codepoint, 0x9 | 0xA | 0xD | 0x20..=0xD7FF | 0xE000..=0xFFFD | 0x10000..=0x10FFFF)
    })
}

// @lat: [[behavior#XML output safety]]
#[cfg(feature = "python")]
#[inline]
fn validate_xml_chars(s: &str) -> PyResult<()> {
    if let Some(character) = invalid_xml_char(s) {
        return Err(PyValueError::new_err(format!(
            "Character U+{:04X} is not allowed in XML 1.0",
            u32::from(character)
        )));
    }
    Ok(())
}

/// Return the byte offset of the next character requiring XML escaping.
///
/// Every searched byte is ASCII, so a match is always a valid boundary in the original UTF-8
/// string.
#[inline(always)]
fn next_xml_escape(bytes: &[u8]) -> Option<usize> {
    let markup = memchr::memchr3(b'&', b'<', b'>', bytes);
    let quote = memchr::memchr2(b'"', b'\'', bytes);
    match (markup, quote) {
        (Some(left), Some(right)) => Some(left.min(right)),
        (Some(index), None) | (None, Some(index)) => Some(index),
        (None, None) => None,
    }
}

/// Return escape offsets using two monotonic platform-optimized scanners.
#[inline]
fn monotonic_xml_escape_indices(bytes: &[u8]) -> impl Iterator<Item = usize> + '_ {
    let mut markup = memchr::memchr3_iter(b'&', b'<', b'>', bytes).peekable();
    let mut quotes = memchr::memchr2_iter(b'"', b'\'', bytes).peekable();

    std::iter::from_fn(move || match (markup.peek(), quotes.peek()) {
        (Some(&left), Some(&right)) if left <= right => markup.next(),
        (Some(_), Some(_)) => quotes.next(),
        (Some(_), None) => markup.next(),
        (None, Some(_)) => quotes.next(),
        (None, None) => None,
    })
}

#[inline(always)]
fn escape_replacement(byte: u8) -> &'static str {
    match byte {
        b'&' => "&amp;",
        b'"' => "&quot;",
        b'\'' => "&apos;",
        b'<' => "&lt;",
        b'>' => "&gt;",
        _ => unreachable!("xml_escape_indices returned a non-escape byte"),
    }
}

/// Escape the five XML-special characters into a newly allocated string.
///
/// This low-level helper does not validate the XML 1.0 Char production; the Python export
/// validates before calling it.
#[inline]
pub fn escape_xml(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + s.len() / 10);
    push_escaped_attr(&mut out, s);
    out
}

/// Append text content with the five-character escaping used by the Python implementation.
///
/// This low-level helper assumes `s` already satisfies the XML 1.0 Char production. It scans
/// bytes for speed and copies clean UTF-8 slices in bulk.
#[inline]
pub fn push_escaped_text(out: &mut String, s: &str) {
    let bytes = s.as_bytes();
    let mut last = 0;
    for _ in 0..SPARSE_ESCAPE_SCAN_LIMIT {
        let Some(relative) = next_xml_escape(&bytes[last..]) else {
            out.push_str(&s[last..]);
            return;
        };
        let i = last + relative;
        out.push_str(&s[last..i]);
        out.push_str(escape_replacement(bytes[i]));
        last = i + 1;
    }

    let dense_start = last;
    for relative in monotonic_xml_escape_indices(&bytes[dense_start..]) {
        let i = dense_start + relative;
        out.push_str(&s[last..i]);
        out.push_str(escape_replacement(bytes[i]));
        last = i + 1;
    }
    out.push_str(&s[last..]);
}

/// Append attribute value with full XML escaping (also escapes quotes).
#[inline]
pub fn push_escaped_attr(out: &mut String, s: &str) {
    push_escaped_text(out, s);
}

#[cfg(feature = "python")]
#[inline]
fn write_str<W: Write + ?Sized>(out: &mut W, s: &str) -> PyResult<()> {
    out.write_all(s.as_bytes())?;
    Ok(())
}

#[cfg(feature = "python")]
#[inline]
fn write_byte<W: Write + ?Sized>(out: &mut W, b: u8) -> PyResult<()> {
    out.write_all(&[b])?;
    Ok(())
}

#[cfg(feature = "python")]
#[inline]
fn write_escaped_text<W: Write + ?Sized>(out: &mut W, s: &str) -> PyResult<()> {
    validate_xml_chars(s)?;
    let bytes = s.as_bytes();
    let mut last = 0;
    for _ in 0..SPARSE_ESCAPE_SCAN_LIMIT {
        let Some(relative) = next_xml_escape(&bytes[last..]) else {
            return write_str(out, &s[last..]);
        };
        let i = last + relative;
        write_str(out, &s[last..i])?;
        write_str(out, escape_replacement(bytes[i]))?;
        last = i + 1;
    }

    let dense_start = last;
    for relative in monotonic_xml_escape_indices(&bytes[dense_start..]) {
        let i = dense_start + relative;
        write_str(out, &s[last..i])?;
        write_str(out, escape_replacement(bytes[i]))?;
        last = i + 1;
    }
    write_str(out, &s[last..])
}

#[cfg(feature = "python")]
#[inline]
fn write_escaped_attr<W: Write + ?Sized>(out: &mut W, s: &str) -> PyResult<()> {
    write_escaped_text(out, s)
}

#[cfg(feature = "python")]
#[inline]
fn write_cdata<W: Write + ?Sized>(out: &mut W, s: &str) -> PyResult<()> {
    validate_xml_chars(s)?;
    write_str(out, "<![CDATA[")?;
    let mut start = 0;
    while let Some(i) = s[start..].find("]]>") {
        let abs = start + i;
        write_str(out, &s[start..abs])?;
        write_str(out, "]]]]><![CDATA[>")?;
        start = abs + 3;
    }
    write_str(out, &s[start..])?;
    write_str(out, "]]>")
}

/// Wrap content in a newly allocated CDATA section.
///
/// Embedded `]]>` terminators are split across adjacent CDATA sections. This low-level helper
/// does not validate the XML 1.0 Char production; the Python export validates before calling it.
#[inline]
pub fn wrap_cdata(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 12);
    push_cdata(&mut out, s);
    out
}

/// Append a CDATA section directly to the buffer.
///
/// The caller must validate XML characters before using the emitted section in a document.
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

/// Return true for names the Python serializer accepts without consulting a parser.
///
/// This mirrors `_is_fast_valid_xml_name` in `json2xml/dicttoxml.py` exactly: ASCII only,
/// no colon, an initial ASCII letter or underscore, then ASCII alphanumerics, `-`, `_`, or
/// `.`. Python resolves anything outside this set through a real XML parser, whose verdict
/// this crate cannot reproduce, so the backend selector keeps those payloads on the Python
/// serializer rather than guessing here.
pub fn is_valid_xml_name(key: &str) -> bool {
    let bytes = key.as_bytes();
    let Some((first, rest)) = bytes.split_first() else {
        return false;
    };
    if !(first.is_ascii_alphabetic() || *first == b'_') {
        return false;
    }
    rest.iter()
        .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.'))
}

/// Make a valid XML name from a key, returning the tag name and the raw
/// (unescaped) original key when a fallback is needed. Escaping of the
/// attribute value is handled later by `make_attr_string`, so we must NOT
/// escape here to avoid double-escaping.
pub fn make_valid_xml_name<'a>(
    key: &'a str,
) -> (Cow<'a, str>, Option<(&'static str, Cow<'a, str>)>) {
    // Already valid
    if is_valid_xml_name(key) {
        return (Cow::Borrowed(key), None);
    }

    // Numeric key - prepend 'n'
    if key.bytes().all(|b| b.is_ascii_digit()) && !key.is_empty() {
        return (Cow::Owned(format!("n{}", key)), None);
    }

    // Try replacing spaces with underscores
    let with_underscores = key.replace(' ', "_");
    if is_valid_xml_name(&with_underscores) {
        return (Cow::Owned(with_underscores), None);
    }

    // Fall back to using "key" with name attribute (raw value, escaped later)
    (Cow::Borrowed("key"), Some(("name", Cow::Borrowed(key))))
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
fn write_open_tag<W: Write + ?Sized>(
    out: &mut W,
    tag: &str,
    name_attr: Option<&str>,
    type_attr: Option<&str>,
) -> PyResult<()> {
    write_byte(out, b'<')?;
    write_str(out, tag)?;
    if let Some(name) = name_attr {
        write_str(out, " name=\"")?;
        write_escaped_attr(out, name)?;
        write_byte(out, b'"')?;
    }
    if let Some(ty) = type_attr {
        write_str(out, " type=\"")?;
        write_str(out, ty)?;
        write_byte(out, b'"')?;
    }
    write_byte(out, b'>')
}

/// Write scalar character data, wrapping it in CDATA when requested.
///
/// Python's `convert_kv` applies CDATA to every scalar it handles, so strings and numbers
/// share this path. Booleans and nulls have their own writers and never use CDATA.
#[cfg(feature = "python")]
#[inline]
fn write_scalar_body<W: Write + ?Sized>(out: &mut W, s: &str, cdata: bool) -> PyResult<()> {
    if cdata {
        write_cdata(out, s)
    } else {
        write_escaped_text(out, s)
    }
}

/// Write an `i64` without allocating a `String`.
#[cfg(feature = "python")]
#[inline]
fn write_integer<W: Write + ?Sized>(out: &mut W, value: i64, cdata: bool) -> PyResult<()> {
    // i64::MIN is 20 bytes with its sign, the widest decimal rendering.
    let mut buf = [0u8; 20];
    let mut end = buf.len();
    let negative = value < 0;
    // Accumulate through the negative side so i64::MIN does not overflow.
    let mut remaining = if negative { value } else { -value };
    loop {
        end -= 1;
        buf[end] = b'0' + (-(remaining % 10)) as u8;
        remaining /= 10;
        if remaining == 0 {
            break;
        }
    }
    if negative {
        end -= 1;
        buf[end] = b'-';
    }
    // Digits and the sign are ASCII, so the slice is valid UTF-8 by construction.
    let rendered = core::str::from_utf8(&buf[end..]).expect("decimal digits are ASCII");
    write_scalar_body(out, rendered, cdata)
}

/// Write a closing tag directly to buffer.
#[cfg(feature = "python")]
#[inline]
fn write_close_tag<W: Write + ?Sized>(out: &mut W, tag: &str) -> PyResult<()> {
    write_str(out, "</")?;
    write_str(out, tag)?;
    write_byte(out, b'>')
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
fn write_value<W: Write + ?Sized>(
    py: Python<'_>,
    out: &mut W,
    obj: &Bound<'_, PyAny>,
    tag: &str,
    name_attr: Option<&str>,
    cfg: &ConvertConfig,
    wrap_container: bool,
) -> PyResult<()> {
    // None
    if obj.is_none() {
        write_open_tag(out, tag, name_attr, type_attr(cfg, "null"))?;
        write_close_tag(out, tag)?;
        return Ok(());
    }

    // Bool (must check before int since bool is subclass of int in Python)
    if obj.is_instance_of::<PyBool>() {
        let v: bool = obj.extract()?;
        write_open_tag(out, tag, name_attr, type_attr(cfg, "bool"))?;
        write_str(out, if v { "true" } else { "false" })?;
        write_close_tag(out, tag)?;
        return Ok(());
    }

    // Int - try i64 first, fall back to Python's str() for large integers.
    // Python's convert_kv wraps every non-bool, non-null scalar in CDATA when enabled,
    // so numbers take the same path as strings here.
    if obj.is_instance_of::<PyInt>() {
        write_open_tag(out, tag, name_attr, type_attr(cfg, "int"))?;
        match obj.extract::<i64>() {
            Ok(v) => write_integer(out, v, cfg.cdata)?,
            Err(_) => write_scalar_body(out, obj.str()?.to_str()?, cfg.cdata)?,
        }
        write_close_tag(out, tag)?;
        return Ok(());
    }

    // Float - use Python's str() for parity (Rust renders 1.0 as "1")
    if obj.is_instance_of::<PyFloat>() {
        write_open_tag(out, tag, name_attr, type_attr(cfg, "float"))?;
        write_scalar_body(out, obj.str()?.to_str()?, cfg.cdata)?;
        write_close_tag(out, tag)?;
        return Ok(());
    }

    // String
    if let Ok(py_str) = obj.cast::<PyString>() {
        let s = py_str.to_str()?;
        write_open_tag(out, tag, name_attr, type_attr(cfg, "str"))?;
        write_scalar_body(out, s, cfg.cdata)?;
        write_close_tag(out, tag)?;
        return Ok(());
    }

    // Dict
    if let Ok(dict) = obj.cast::<PyDict>() {
        if wrap_container {
            write_open_tag(out, tag, name_attr, type_attr(cfg, "dict"))?;
        }
        write_dict_contents(py, out, dict, cfg)?;
        if wrap_container {
            write_close_tag(out, tag)?;
        }
        return Ok(());
    }

    // List
    if let Ok(list) = obj.cast::<PyList>() {
        if wrap_container {
            write_open_tag(out, tag, name_attr, type_attr(cfg, "list"))?;
        }
        write_convert_list(py, out, list, tag, cfg)?;
        if wrap_container {
            write_close_tag(out, tag)?;
        }
        return Ok(());
    }

    // Other iterables (tuples, generators, etc.)
    if let Ok(iter) = obj.try_iter() {
        let items: Vec<Bound<'_, PyAny>> = iter.collect::<PyResult<_>>()?;
        let list = PyList::new(py, &items)?;
        if wrap_container {
            write_open_tag(out, tag, name_attr, type_attr(cfg, "list"))?;
        }
        write_convert_list(py, out, &list, tag, cfg)?;
        if wrap_container {
            write_close_tag(out, tag)?;
        }
        return Ok(());
    }

    // Fallback: convert to string via Python's str()
    let py_str = obj.str()?;
    let s = py_str.to_str()?;
    write_open_tag(out, tag, name_attr, type_attr(cfg, "str"))?;
    write_scalar_body(out, s, cfg.cdata)?;
    write_close_tag(out, tag)?;
    Ok(())
}

/// Write every key/value pair of a dict, mirroring `_append_convert_dict`.
#[cfg(feature = "python")]
fn write_dict_contents<W: Write + ?Sized>(
    py: Python<'_>,
    out: &mut W,
    dict: &Bound<'_, PyDict>,
    cfg: &ConvertConfig,
) -> PyResult<()> {
    for (key, val) in dict.iter() {
        let key_py_str = key.str()?;
        let (xml_key, name_attr_owned) = make_valid_xml_name(key_py_str.to_str()?);
        let name_attr = name_attr_owned.as_ref().map(|(_, v)| v.as_ref());

        if let Ok(list) = val.cast::<PyList>() {
            write_list2xml_str(py, out, name_attr, list, &xml_key, cfg)?;
        } else if let Ok(child) = val.cast::<PyDict>() {
            write_dict2xml_str(py, out, name_attr, child, &xml_key, false, "", cfg)?;
        } else {
            write_value(py, out, &val, &xml_key, name_attr, cfg, true)?;
        }
    }
    Ok(())
}

/// Emit a dict element, mirroring `_append_dict2xml_str`.
///
/// `parent_is_list` and `list_headers` decide whether the dict keeps its own wrapper, borrows
/// the parent tag, or is flattened into the surrounding element.
#[cfg(feature = "python")]
#[allow(clippy::too_many_arguments)]
fn write_dict2xml_str<W: Write + ?Sized>(
    py: Python<'_>,
    out: &mut W,
    name_attr: Option<&str>,
    item: &Bound<'_, PyDict>,
    item_name: &str,
    parent_is_list: bool,
    parent: &str,
    cfg: &ConvertConfig,
) -> PyResult<()> {
    let type_value = type_attr(cfg, "dict");
    let has_attrs = name_attr.is_some() || type_value.is_some();

    if parent_is_list && cfg.list_headers {
        // Python only carries the attributes onto the borrowed parent tag when items are
        // not individually wrapped.
        if has_attrs && !cfg.item_wrap {
            write_open_tag(out, parent, name_attr, type_value)?;
        } else {
            write_open_tag(out, parent, None, None)?;
        }
        write_dict_contents(py, out, item, cfg)?;
        write_close_tag(out, parent)?;
    } else if parent_is_list && !cfg.item_wrap {
        write_dict_contents(py, out, item, cfg)?;
    } else {
        write_open_tag(out, item_name, name_attr, type_value)?;
        write_dict_contents(py, out, item, cfg)?;
        write_close_tag(out, item_name)?;
    }
    Ok(())
}

/// Emit a list element, mirroring `_append_list2xml_str`.
///
/// The wrapper is dropped when the members are written directly into the surrounding element:
/// under `list_headers`, or when an unwrapped list leads with a primitive.
#[cfg(feature = "python")]
fn write_list2xml_str<W: Write + ?Sized>(
    py: Python<'_>,
    out: &mut W,
    name_attr: Option<&str>,
    item: &Bound<'_, PyList>,
    item_name: &str,
    cfg: &ConvertConfig,
) -> PyResult<()> {
    // Python's historical list shape depends only on the first member.
    let first_is_primitive = match item.get_item(0) {
        Ok(first) => is_python_scalar(&first),
        Err(_) => false,
    };

    if cfg.list_headers || (first_is_primitive && !cfg.item_wrap) {
        return write_convert_list(py, out, item, item_name, cfg);
    }

    write_open_tag(out, item_name, name_attr, type_attr(cfg, "list"))?;
    write_convert_list(py, out, item, item_name, cfg)?;
    write_close_tag(out, item_name)
}

/// Write every member of a list, mirroring `_append_convert_list`.
#[cfg(feature = "python")]
fn write_convert_list<W: Write + ?Sized>(
    py: Python<'_>,
    out: &mut W,
    list: &Bound<'_, PyList>,
    parent: &str,
    cfg: &ConvertConfig,
) -> PyResult<()> {
    // The default item_func names every member "item"; custom functions stay on Python.
    let item_name = "item";
    // Only plain scalars borrow the parent tag when items are not wrapped. Booleans and
    // nulls keep the item tag, matching the Python writer.
    let (scalar_key, scalar_name_attr) = if cfg.item_wrap {
        (Cow::Borrowed(item_name), None)
    } else {
        make_valid_xml_name(parent)
    };
    let scalar_name = scalar_name_attr.as_ref().map(|(_, v)| v.as_ref());

    for item in list.iter() {
        if let Ok(dict) = item.cast::<PyDict>() {
            write_dict2xml_str(py, out, None, dict, item_name, true, parent, cfg)?;
        } else if let Ok(inner) = item.cast::<PyList>() {
            write_list2xml_str(py, out, None, inner, item_name, cfg)?;
        } else if item.is_none() || item.is_instance_of::<PyBool>() {
            write_value(py, out, &item, item_name, None, cfg, true)?;
        } else {
            write_value(py, out, &item, &scalar_key, scalar_name, cfg, true)?;
        }
    }
    Ok(())
}

/// Return true when a Python object is treated as a primitive scalar by the
/// pure-Python serializer for list-wrapper decisions.
#[cfg(feature = "python")]
#[inline]
fn is_python_scalar(obj: &Bound<'_, PyAny>) -> bool {
    obj.is_none()
        || obj.is_instance_of::<PyBool>()
        || obj.is_instance_of::<PyInt>()
        || obj.is_instance_of::<PyFloat>()
        || obj.is_instance_of::<PyString>()
}

/// Convert a Python value to UTF-8 encoded XML bytes.
///
/// The direct extension accepts scalars and iterables, while the automatic backend selector
/// dispatches only supported dict/list requests here.
///
/// Args:
///     obj: The Python object to convert.
///     root: Whether to include the XML declaration and root element (default: True).
///     custom_root: The name of the root element (default: "root").
///     attr_type: Whether to include type attributes (default: True).
///     item_wrap: Whether to wrap list items in `<item>` tags (default: True).
///     cdata: Whether to wrap string values in CDATA sections (default: False).
///     list_headers: Suppress the outer list container and repeat the parent tag for nested
///         dictionary items; primitive tags continue to follow `item_wrap` (default: False).
///
/// Returns:
///     bytes: The XML representation of the input object.
///
/// Raises:
///     ValueError: If `custom_root` is not a supported XML name or data contains characters
///         excluded by XML 1.0.
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
) -> PyResult<Py<PyBytes>> {
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

    // Stream into Python-owned bytes storage to avoid a complete Rust String and cross-language
    // copy. The bounded buffer coalesces the serializer's many small writes.
    PyBytes::new_with_writer(py, 0, |out| {
        let mut out = BufWriter::with_capacity(OUTPUT_BUFFER_SIZE, out);

        if root {
            write_str(&mut out, "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>")?;
            write_byte(&mut out, b'<')?;
            write_str(&mut out, custom_root)?;
            write_byte(&mut out, b'>')?;
        }

        // Python renders a rootless document with an empty parent name, so list members and
        // top-level scalars must be named from that same empty parent rather than from the
        // unused custom root.
        let parent = if root { custom_root } else { "" };

        if let Ok(dict) = obj.cast::<PyDict>() {
            write_dict_contents(py, &mut out, dict, &config)?;
        } else if let Ok(list) = obj.cast::<PyList>() {
            write_convert_list(py, &mut out, list, parent, &config)?;
        } else {
            // A bare scalar is named by the item function, exactly as _append_convert does.
            write_value(py, &mut out, obj, "item", None, &config, true)?;
        }

        if root {
            write_str(&mut out, "</")?;
            write_str(&mut out, custom_root)?;
            write_byte(&mut out, b'>')?;
        }

        out.flush()?;
        Ok(())
    })
    .map(Bound::unbind)
}

/// Return true when a key names the same element in both implementations.
///
/// Mirrors `_rust_renders_key_identically` in `json2xml/backend_selector.py`.
#[cfg(feature = "python")]
fn key_renders_identically(key: &Bound<'_, PyAny>) -> bool {
    let Ok(py_str) = key.cast_exact::<PyString>() else {
        return false;
    };
    let Ok(text) = py_str.to_str() else {
        return false;
    };
    if text.is_empty() || text.starts_with('@') || text.ends_with("@flat") {
        return false;
    }
    if !text.is_ascii() || text.contains(':') {
        return false;
    }
    // A trailing space is the one case Python's parser probe accepts but the fast path
    // rejects, because the probe document tolerates space before the tag close.
    !text.as_bytes()[text.len() - 1].is_ascii_whitespace()
}

/// Return true when a payload stays inside the subset this backend renders identically.
///
/// This is the native form of `rust_renders_identically`; the selector calls it before
/// dispatching so the walk does not cost a Python-level traversal of the whole payload.
/// Types are matched exactly, because Python classifies subclasses through isinstance
/// fallbacks that this writer does not reproduce.
#[cfg(feature = "python")]
#[pyfunction]
fn payload_is_supported(obj: &Bound<'_, PyAny>) -> PyResult<bool> {
    let mut stack: Vec<Bound<'_, PyAny>> = vec![obj.clone()];

    while let Some(value) = stack.pop() {
        if value.is_none()
            || value.is_exact_instance_of::<PyString>()
            || value.is_exact_instance_of::<PyBool>()
            || value.is_exact_instance_of::<PyInt>()
            || value.is_exact_instance_of::<PyFloat>()
        {
            continue;
        }
        if let Ok(dict) = value.cast_exact::<PyDict>() {
            for (key, child) in dict.iter() {
                if !key_renders_identically(&key) {
                    return Ok(false);
                }
                stack.push(child);
            }
            continue;
        }
        if let Ok(list) = value.cast_exact::<PyList>() {
            for item in list.iter() {
                stack.push(item);
            }
            continue;
        }
        if let Ok(tuple) = value.cast_exact::<PyTuple>() {
            for item in tuple.iter() {
                stack.push(item);
            }
            continue;
        }
        return Ok(false);
    }
    Ok(true)
}

/// Fast XML string escaping.
///
/// Escapes &, ", ', <, > characters for XML.
#[cfg(feature = "python")]
#[pyfunction]
fn escape_xml_py(s: &str) -> PyResult<String> {
    validate_xml_chars(s)?;
    Ok(escape_xml(s))
}

/// Wrap a string in CDATA section.
#[cfg(feature = "python")]
#[pyfunction]
fn wrap_cdata_py(s: &str) -> PyResult<String> {
    validate_xml_chars(s)?;
    Ok(wrap_cdata(s))
}

/// A Python module implemented in Rust.
#[cfg(feature = "python")]
#[pymodule]
fn json2xml_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(dicttoxml, m)?)?;
    m.add_function(wrap_pyfunction!(payload_is_supported, m)?)?;
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
        fn rejects_name_with_colons() {
            // Python resolves colon names through its parser, so the selector keeps them
            // on the Python serializer rather than have this crate guess.
            assert!(!is_valid_xml_name("ns:element"));
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
        fn accepts_xml_prefixed_names() {
            // The XML specification reserves these names, but the Python serializer emits
            // them unchanged. Rejecting them here silently renamed user keys.
            assert!(is_valid_xml_name("xmlelement"));
            assert!(is_valid_xml_name("XMLelement"));
            assert!(is_valid_xml_name("XmLelement"));
            assert!(is_valid_xml_name("xml"));
        }

        #[test]
        fn rejects_non_ascii_names() {
            // Python decides these with a parser; this crate must not claim them.
            assert!(!is_valid_xml_name("café"));
            assert!(!is_valid_xml_name("名前"));
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
            assert_eq!(
                attr.as_ref().map(|(k, v)| (*k, v.as_ref())),
                Some(("name", "-invalid"))
            );
        }

        #[test]
        // @lat: [[tests#XML helper behavior#Rust invalid-name attrs escape once]]
        fn returns_raw_key_for_invalid_names() {
            // make_valid_xml_name must return the raw key, not escaped.
            // Escaping happens later in make_attr_string to avoid double-escaping.
            let (name, attr) = make_valid_xml_name("tag&name");
            assert_eq!(name, "key");
            assert_eq!(
                attr.as_ref().map(|(k, v)| (*k, v.as_ref())),
                Some(("name", "tag&name"))
            );
        }

        #[test]
        fn double_escape_does_not_happen() {
            // End-to-end: make_valid_xml_name + make_attr_string should produce
            // a single level of escaping, not &amp;amp;
            let (name, attr) = make_valid_xml_name("tag&name");
            assert_eq!(name, "key");
            let attrs = attr
                .map(|(k, v)| vec![(k.to_string(), v.into_owned())])
                .unwrap_or_default();
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
        // @lat: [[tests#XML helper behavior#Rust XML escape scanner]]
        fn locates_each_escape_byte_without_splitting_utf8() {
            assert_eq!(next_xml_escape("plain café".as_bytes()), None);
            assert_eq!(next_xml_escape("café & tea".as_bytes()), Some(6));
            assert_eq!(
                monotonic_xml_escape_indices(b"<&>\"'").collect::<Vec<_>>(),
                [0, 1, 2, 3, 4]
            );
            assert_eq!(next_xml_escape(b"safe>"), Some(4));
        }

        #[test]
        // @lat: [[tests#XML helper behavior#Dense Rust XML escape scanning remains linear]]
        fn handles_dense_single_class_escape_input() {
            let dense = "&".repeat(32 * 1024);
            let indices = monotonic_xml_escape_indices(dense.as_bytes()).collect::<Vec<_>>();

            assert_eq!(indices.len(), dense.len());
            assert_eq!(indices.first(), Some(&0));
            assert_eq!(indices.last(), Some(&(dense.len() - 1)));
            assert_eq!(escape_xml(&dense), "&amp;".repeat(dense.len()));
        }

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
