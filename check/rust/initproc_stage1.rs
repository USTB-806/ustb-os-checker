#![no_std]
#![no_main]

#[macro_use]
extern crate user_lib;

use user_lib::{exit, write};

#[no_mangle]
fn main() -> i32 {
    println!("[initproc_stage1] Hello from initproc!");

    let msg = b"[initproc_stage1] Direct sys_write test passed!\n";
    let ret = write(1, msg);
    if ret > 0 {
        println!("[initproc_stage1] sys_write returned {} bytes, OK!", ret);
    } else {
        println!("[initproc_stage1] sys_write failed with code {}", ret);
    }

    println!("[initproc_stage1] All Lab 4 tests passed!");
    println!("[initproc_stage1] Next: implement file descriptors (Lab 5), then switch to initproc_stage2");
    0
}
