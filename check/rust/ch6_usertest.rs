#![no_std]
#![no_main]

#[macro_use]
extern crate user_lib;

use user_lib::{exec, fork, wait, yield_};

/// Checker ch6 轻量级测试编排器
/// 使用 fork+exec 启动各个独立测试程序，waitpid 回收子进程

const TESTS: &[&str] = &[
    "ch6_forktest_simple\0",
    "ch6_forktest0\0",
    "ch6_exit0\0",
    "ch6_getpid\0",
];

#[no_mangle]
pub fn main() -> i32 {
    println!("[ch6_usertest] Running all Lab 6 tests...");

    for test in TESTS {
        let pid = fork();
        if pid == 0 {
            // child: exec test
            exec(*test, &[0 as *const u8]);
            println!("[ch6_usertest] exec {} failed!", &test[..test.len()-1]);
            return -1;
        }
    }

    // Wait for all children
    let mut exit_code: i32 = 0;
    let mut reaped = 0;
    loop {
        let pid = wait(&mut exit_code);
        if pid < 0 {
            break;
        }
        reaped += 1;
    }
    println!("[ch6_usertest] reaped {} test programs", reaped);

    println!("Test ch6_usertest OK!");
    0
}
