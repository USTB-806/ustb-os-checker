#include "lib.h"

int main() {
    write(1, "Testing open/read/close...\n", 27);
    int fd = open("test_file", 0);
    if (fd > 0) {
        char buf[32];
        isize n = read(fd, buf, 32);
        if (n > 0) {
            write(1, "Read content: ", 14);
            write(1, buf, n);
        } else {
             write(1, "Read failed\n", 12);
        }
        close(fd);
    } else {
        write(1, "Open failed\n", 12);
    }
    return 0;
}
