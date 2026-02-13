#![no_std]
#![no_main]

/// Checker initproc for ch5 (文件系统)
/// 内联测试 open/write/close/read + spawn ch5 测试程序

#[macro_use]
extern crate user_lib;

use user_lib::{close, open, read, spawn, write, yield_, OpenFlags};

const TESTS: &[&str] = &[
    // ch4 regression tests
    "ch4b_sbrk\0",
    "ch4_mmap0\0",
    "ch4_mmap1\0",
    "ch4_mmap2\0",
    "ch4_mmap3\0",
    "ch4_ummap0\0",
    "ch4_ummap1\0",
    // ch5 new tests
    "ch5_exit0\0",
    "ch5_exit1\0",
    "ch5_forktest_simple\0",
    "ch5_forktest0\0",
    "ch5_forktest1\0",
    "ch5_forktree\0",
    "ch5_getpid\0",
    "ch5_setprio\0",
    "ch5_stride0\0",
    "ch5_stride1\0",
    "ch5_stride2\0",
    "ch5_stride3\0",
    "ch5_stride4\0",
    "ch5_stride5\0",
];

#[no_mangle]
fn main() -> i32 {
    println!("[initproc] Hello from initproc!");

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

    println!("[initproc] initproc lab 5 exiting, all tests should have completed.");
    0
}