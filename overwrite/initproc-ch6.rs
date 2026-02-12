#![no_std]
#![no_main]

/// Checker initproc for ch6 (进程管理 — waitpid)
/// 使用 fork + exec + wait 来测试学生的 sys_waitpid 实现

#[macro_use]
extern crate user_lib;

use user_lib::{exec, fork, wait, yield_};

const TESTS: &[&str] = &[
    // ch4 regression tests
    "ch4b_sbrk\0",
    "ch4_mmap0\0",
    "ch4_mmap1\0",
    "ch4_mmap3\0",
    "ch4_ummap0\0",
    "ch4_ummap1\0",
    // ch6 new tests
    "ch6_forktest_simple\0",
    "ch6_forktest0\0",
    "ch6_exit0\0",
    "ch6_getpid\0",
    "ch6_usertest\0",
];

#[no_mangle]
fn main() -> i32 {
    println!("[initproc] === Lab 6 Process Management Test ===");

    for test in TESTS {
        let pid = fork();
        if pid == 0 {
            // child: exec test program
            exec(*test, &[0 as *const u8]);
            // exec failed
            println!("[initproc] exec {} failed!", &test[..test.len()-1]);
            return -1;
        } else {
            println!("[initproc] forked child pid={} for {}", pid, &test[..test.len()-1]);
        }
    }

    // Wait for all children — this is the core test of the student's waitpid!
    let mut exit_code: i32 = 0;
    let mut reaped = 0;
    loop {
        let pid = wait(&mut exit_code);
        if pid < 0 {
            break;
        }
        println!(
            "[initproc] Released a zombie process, pid={}, exit_code={}",
            pid, exit_code,
        );
        reaped += 1;
    }
    println!("[initproc] reaped {} child processes", reaped);
    println!("[initproc] All Lab 6 waitpid tests completed!");
    0
}
