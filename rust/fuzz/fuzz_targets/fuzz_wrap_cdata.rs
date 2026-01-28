#![no_main]

use libfuzzer_sys::fuzz_target;
use json2xml_rs::wrap_cdata;

fuzz_target!(|data: &str| {
    let result = wrap_cdata(data);
    
    // Verify invariants:
    // 1. Result must start with CDATA opening
    assert!(result.starts_with("<![CDATA["));
    
    // 2. Result must end with CDATA closing
    assert!(result.ends_with("]]>"));
    
    // 3. The ]]> sequence in input must be properly escaped
    //    (split into ]]]]><![CDATA[>)
    
    // 4. Result should be longer than or equal to input + CDATA wrapper (12 chars)
    assert!(result.len() >= data.len() + 12);
});
