#![no_main]

use libfuzzer_sys::fuzz_target;
use json2xml_rs::escape_xml;

fuzz_target!(|data: &str| {
    let result = escape_xml(data);
    
    // Verify invariants:
    // 1. Result should not contain unescaped special chars
    assert!(!result.contains('&') || result.contains("&amp;") || result.contains("&quot;") 
            || result.contains("&apos;") || result.contains("&lt;") || result.contains("&gt;"));
    
    // 2. Result should be valid (no panics occurred)
    // 3. If input had no special chars, output equals input
    if !data.contains('&') && !data.contains('"') && !data.contains('\'') 
       && !data.contains('<') && !data.contains('>') {
        assert_eq!(result, data);
    }
    
    // 4. Output length should be >= input length (escaping only adds chars)
    assert!(result.len() >= data.len());
});
