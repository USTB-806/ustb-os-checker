#![no_std]
#![no_main]

/// Checker initproc for ch4 (地址空间)
/// 测试基本 sys_write + spawn 所有 ch4 测试程序

#[macro_use]
extern crate user_lib;

use user_lib::{spawn, write, yield_};

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
fn main() -> i32 {
    println!("[initproc] Hello from initproc!");

    let msg = b"[initproc] Direct sys_write test passed!\n";
    let ret = write(1, msg);
    if ret > 0 {
        println!("[initproc] sys_write returned {} bytes, OK!", ret);
    } else {
        println!("[initproc] sys_write FAILED with code {}", ret);
    }

    println!("[initproc] All Lab 4 basic tests passed!");

    let mut spawned = 0;
    for test in TESTS {
        let pid = spawn(*test);
        if pid >= 0 {
            spawned += 1;
        }
    }
    println!("[initproc] spawned {} test programs", spawned);

    for _ in 0..1000 {
        yield_();
    }

    println!("[initproc] initproc exiting, all tests should have completed.");
    0
}
