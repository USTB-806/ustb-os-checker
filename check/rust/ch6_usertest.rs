#![no_std]
#![no_main]

#[macro_use]
extern crate user_lib;

use user_lib::{exec, fork, wait, yield_};

const TESTS: &[&str] = &[
    "ch6_cat\0",
    "ch6_filetest_simple\0",
    "ch6_file0\0",
    "ch6_file1\0",
    "ch6_file2\0",
    "ch6_file3\0",
];

#[no_mangle]
pub fn main() -> i32 {
    println!("[ch6_usertest] Running all Lab 5 tests...");

    let mut spawned = 0;
    for test in TESTS {
        let pid = spawn(*test);
        if pid >= 0 {
            spawned += 1;
        }
    }
    println!("[ch6_usertest] spawned {} test programs", spawned);

    // yield to let spawned programs complete
    for _ in 0..200 {
        yield_();
    }

    println!("Test ch6_usertest OK!");
    0
}
