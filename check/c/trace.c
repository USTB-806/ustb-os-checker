#include "../lib/lib.h"

int main() {
    print_str("Trace System Call Test\n");
    
    // Test 1: Get initial syscall count
    print_str("Test 1: Get initial syscall count\n");
    isize write_count = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_WRITE, 0);
    print_str("  SYSCALL_WRITE (64) count: ");
    print_num(write_count);
    print_str("\n");
    
    // Test 2: Call write several times and check count
    print_str("Test 2: Call write 3 times and check count\n");
    write(1, "  Line 1\n", 9);
    write(1, "  Line 2\n", 9);
    write(1, "  Line 3\n", 9);
    
    write_count = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_WRITE, 0);
    print_str("  SYSCALL_WRITE count completed after writes: ");
    print_num(write_count);
    print_str("\n");
    
    // Test 4: Get task information
    print_str("Test 4: Get task information\n");
    TaskInfo task_info;
    int result = trace(TRACE_GET_TASK_INFO, 0, (size_t)&task_info);
    
    if (result == 0) {
        print_str("  Task Status: ");
        print_num(task_info.status);
        
        // Print status name
        if (task_info.status == TASK_STATUS_UNINIT) {
            print_str(" (UNINIT)");
        } else if (task_info.status == TASK_STATUS_READY) {
            print_str(" (READY)");
        } else if (task_info.status == TASK_STATUS_RUNNING) {
            print_str(" (RUNNING)");
        } else if (task_info.status == TASK_STATUS_EXITED) {
            print_str(" (EXITED)");
        }
        print_str(" OK!\n");
        
        print_str("  Total Syscalls: ");
        print_num(task_info.syscall_times);
        print_str(" OK!\n");
    } else {
        print_str("  Failed to get task info, result: ");
        print_num(result);
        print_str("\n");
    }
    
    yield();

    // Test 5: Check multiple syscall counts
    print_str("Test 5: Check counts for different syscalls\n");
    
    isize exit_count = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_EXIT, 0);
    print_str("  SYSCALL_EXIT (93) count: ");
    print_num(exit_count);
    print_str("\n");
    
    isize yield_count = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_YIELD, 0);
    print_str("  SYSCALL_YIELD (124) count completed: ");
    print_num(yield_count);
    print_str("\n");
    
    isize trace_count = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_TRACE, 0);
    print_str("  SYSCALL_TRACE (410) count completed: ");
    print_num(trace_count);
    print_str("\n");
    
    print_str("Test 6: Test with invalid syscall ID\n");
    result = trace(TRACE_GET_SYSCALL_COUNT, 999, 0);
    print_str("  Querying syscall 999, result: ");
    print_num(result);
    print_str(" (should be -1 or 0)\n");
    
    // Test 7: Call yield and check its count
    print_str("Test 7: Call yield() and check count\n");
    isize yield_before = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_YIELD, 0);
    print_str("  SYSCALL_YIELD count before: ");
    print_num(yield_before);
    print_str("\n");
    
    yield();
    
    isize yield_after = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_YIELD, 0);
    print_str("  SYSCALL_YIELD count completed after: ");
    print_num(yield_after);
    print_str("\n");
    
    // Test 8: Get time and check count
    print_str("Test 8: Call get_time() and check count\n");
    isize gettime_before = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_GET_TIME, 0);
    print_str("  SYSCALL_GET_TIME count before: ");
    print_num(gettime_before);
    print_str("\n");
    
    TimeVal tv;
    get_time(&tv);
    print_str("  Current time: ");
    print_num(tv.sec);
    print_str(".");
    print_num(tv.usec);
    print_str(" seconds\n");
    
    isize gettime_after = trace(TRACE_GET_SYSCALL_COUNT, SYSCALL_GET_TIME, 0);
    print_str("  SYSCALL_GET_TIME count after: ");
    print_num(gettime_after);
    print_str("\n");
    
    // Test 9: Get total syscall count
    print_str("Test 9: Get total syscall count\n");
    isize total = trace(TRACE_GET_TOTAL_SYSCALLS, 0, 0);
    print_str("  Success! Total syscalls: ");
    print_num(total);
    print_str("\n");
    
    // Final task info
    print_str("Final Task Information\n");
    result = trace(TRACE_GET_TASK_INFO, 0, (size_t)&task_info);
    if (result == 0) {
        print_str("Success! Total syscalls made: ");
        print_num(task_info.syscall_times);
        print_str("\n");
    }
    
    print_str("All trace syscall tests finished!\n");
    
    return 0;
}
