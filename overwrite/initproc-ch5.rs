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
    "ch4_mmap3\0",
    "ch4_ummap0\0",
    "ch4_ummap1\0",
    // ch5 new tests
    "ch5_file0\0",
    "ch5b_filetest_simple\0",
    "ch5_usertest\0",
];

#[no_mangle]
fn main() -> i32 {
    println!("[initproc] === Lab 5 File System Test ===");

    // Test 1: create + write
    let fd = open("test_checker\0", OpenFlags::CREATE | OpenFlags::WRONLY);
    assert!(fd > 0, "open for write failed");
    let msg = b"Hello from Lab 5!";
    let ret = write(fd as usize, msg);
    assert_eq!(ret as usize, msg.len());
    close(fd as usize);
    println!("[initproc] Test file create+write passed!");

    // Test 2: reopen + read + verify
    let fd = open("test_checker\0", OpenFlags::RDONLY);
    assert!(fd > 0, "open for read failed");
    let mut buf = [0u8; 64];
    let n = read(fd as usize, &mut buf);
    assert_eq!(n as usize, msg.len());
    let content = core::str::from_utf8(&buf[..n as usize]).unwrap();
    assert_eq!(content, "Hello from Lab 5!");
    close(fd as usize);
    println!("[initproc] Test file read+verify passed!");

    // Test 3: stdout write
    let stdout_msg = b"[initproc] stdout write OK!\n";
    write(1, stdout_msg);

    println!("[initproc] All Lab 5 tests passed!");

    // Spawn ch5 test programs
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

    println!("[initproc] initproc exiting.");
    0
}
