#![no_std]
#![no_main]

/// Checker initproc for ch6 (进程管理 — waitpid)
/// 使用 fork + exec + wait 来测试学生的 sys_waitpid 实现

#[macro_use]
extern crate user_lib;

use user_lib::{exec, fork, wait, yield_, spawn};

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
    // ch6 new test
    "ch6_cat\0",
    "ch6_filetest_simple\0",
    "ch6_file0\0",
    "ch6_file1\0",
    "ch6_file2\0",
    "ch6_file3\0",
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

    println!("[initproc] initproc lab 6 exiting, all tests should have completed.");
    0
}
