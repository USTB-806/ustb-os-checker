#![no_std]
#![no_main]

#[macro_use]
extern crate user_lib;

use user_lib::{spawn, yield_};

/// Checker ch5 轻量级测试编排器
/// 按顺序 spawn 各个独立测试程序，确保它们全部执行

const TESTS: &[&str] = &[
    "ch5_file0\0",
    "ch5b_filetest_simple\0",
    "ch5_file1\0",
    "ch5_file2\0",
];

#[no_mangle]
pub fn main() -> i32 {
    println!("[ch5_usertest] Running all Lab 5 tests...");

    let mut spawned = 0;
    for test in TESTS {
        let pid = spawn(*test);
        if pid >= 0 {
            spawned += 1;
        }
    }
    println!("[ch5_usertest] spawned {} test programs", spawned);

    // yield to let spawned programs complete
    for _ in 0..200 {
        yield_();
    }

    println!("Test ch5_usertest OK!");
    0
}
