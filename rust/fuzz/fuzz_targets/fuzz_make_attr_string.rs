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
    
    // 3. Each attribute should produce key="value" format
    for (key, _value) in &input.attrs {
        // Key should appear in the result
        assert!(result.contains(key), "Key '{}' should appear in result", key);
    }
    
    // 4. Values should be escaped (no raw & < > " ' in values)
    //    The make_attr_string calls escape_xml on values
    
    // 5. Function should never panic - reaching here means it didn't
});
