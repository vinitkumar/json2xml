#![no_main]

use libfuzzer_sys::fuzz_target;
use json2xml_rs::is_valid_xml_name;

fuzz_target!(|data: &str| {
    let result = is_valid_xml_name(data);
    
    // Verify invariants:
    // 1. Empty string is always invalid
    if data.is_empty() {
        assert!(!result);
    }
    
    // 2. String starting with digit is invalid
    if let Some(first) = data.chars().next() {
        if first.is_ascii_digit() {
            assert!(!result);
        }
    }
    
    // 3. String starting with "xml" (case-insensitive) is invalid
    if data.to_lowercase().starts_with("xml") {
        assert!(!result);
    }
    
    // 4. String containing spaces is invalid
    if data.contains(' ') {
        assert!(!result);
    }
    
    // 5. Function should never panic - reaching here means it didn't
});
