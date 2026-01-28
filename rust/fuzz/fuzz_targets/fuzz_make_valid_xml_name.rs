#![no_main]

use libfuzzer_sys::fuzz_target;
use json2xml_rs::make_valid_xml_name;

fuzz_target!(|data: &str| {
    let (name, attr) = make_valid_xml_name(data);
    
    // Verify invariants:
    // 1. The returned name must be a valid XML name OR be "key" with an attribute
    if name != "key" {
        // If we didn't fall back to "key", the name should be valid
        // (though it might have been transformed)
        assert!(!name.is_empty(), "Name should not be empty");
    }
    
    // 2. If attr is Some, name should be "key"
    if attr.is_some() {
        assert_eq!(name, "key", "Fallback name should be 'key'");
        let (attr_name, _attr_value) = attr.unwrap();
        assert_eq!(attr_name, "name", "Attribute key should be 'name'");
    }
    
    // 3. Purely numeric input should get 'n' prefix
    if !data.is_empty() && data.chars().all(|c| c.is_ascii_digit()) {
        assert!(name.starts_with('n'), "Numeric keys should get 'n' prefix");
    }
    
    // 4. Function should never panic - reaching here means it didn't
});
