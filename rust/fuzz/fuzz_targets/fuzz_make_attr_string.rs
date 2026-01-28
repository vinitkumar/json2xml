#![no_main]

use libfuzzer_sys::fuzz_target;
use arbitrary::Arbitrary;
use json2xml_rs::make_attr_string;

#[derive(Arbitrary, Debug)]
struct AttrInput {
    attrs: Vec<(String, String)>,
}

fuzz_target!(|input: AttrInput| {
    let result = make_attr_string(&input.attrs);
    
    // Verify invariants:
    // 1. Empty attrs should produce empty string
    if input.attrs.is_empty() {
        assert!(result.is_empty());
        return;
    }
    
    // 2. Result should start with space (for XML formatting)
    assert!(result.starts_with(' '), "Attribute string should start with space");
    
    // 3. Each attribute should produce a ` key="value"`-like fragment.
    //    We check for the more specific pattern ` {key}="` to avoid
    //    passing on overlapping keys (e.g. "a" vs "aa") or malformed formatting.
    for (key, _value) in &input.attrs {
        let expected_fragment = format!(" {}=\"", key);
        assert!(
            result.contains(&expected_fragment),
            "Attribute fragment '{}' should appear in result '{}'",
            expected_fragment,
            result
        );
    }
    
    // 4. Values should be escaped (no raw & < > " ' in values)
    //    The make_attr_string calls escape_xml on values
    
    // 5. Function should never panic - reaching here means it didn't
});
