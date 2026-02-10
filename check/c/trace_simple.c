#include "../lib/lib.h"

int main() {
    print_str("Simple Trace Example\n");
    
    // Check how many times we've called write so far
    // Output example: "WRITE count: 2"
    print_str("Checking write syscall count...\n");
    isize count = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_WRITE, 0);
    print_str("WRITE count: ");
    print_num(count);
    print_str("\n");
    
    // Make some writes
    // Output example: "WRITE count: 22"
    print_str("Making 5 write calls:\n");
    for (int i = 1; i <= 5; i++) {
        print_str("  Write #");
        print_num(i);
        print_str("\n");
    }
    
    // Check count again
    count = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_WRITE, 0);
    print_str("WRITE count now: ");
    print_num(count);
    print_str("\n");
    
    // Get task info
    print_str("Getting task information...\n");
    TaskInfo info;
    if (trace(TRACE_GET_TASK_INFO, 0, (size_t)&info) == 0) {
        print_str("Total syscalls: ");
        print_num(info.syscall_times);
        print_str("\n");
        print_str("Task status: ");
        print_num(info.status);
        print_str("\n");
    }
    
    print_str("Success trace_simple!\n");
    return 0;
}
