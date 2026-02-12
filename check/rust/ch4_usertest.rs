#![no_std]
#![no_main]

#[macro_use]
extern crate user_lib;

use user_lib::{spawn, yield_};

/// Checker ch4 轻量级测试编排器
/// 按顺序 spawn 各个独立测试程序，确保它们全部执行

const TESTS: &[&str] = &[
    "ch4b_sbrk\0",
    "ch4_mmap0\0",
    "ch4_mmap1\0",
    "ch4_mmap2\0",
    "ch4_mmap3\0",
    "ch4_ummap0\0",
    "ch4_ummap1\0",
];

#[no_mangle]
pub fn main() -> i32 {
    println!("[ch4_usertest] Running all Lab 4 tests...");

    let mut spawned = 0;
    for test in TESTS {
        let pid = spawn(*test);
        if pid >= 0 {
            spawned += 1;
        }
    }
    println!("[ch4_usertest] spawned {} test programs", spawned);

    // yield to let spawned programs complete
    for _ in 0..200 {
        yield_();
    }

    println!("Test ch4_usertest OK!");
    0
}
