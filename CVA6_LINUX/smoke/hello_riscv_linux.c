#include <stdio.h>
#include <unistd.h>

int main(void) {
    printf("hello from riscv linux on cva6/spike\n");
    printf("pid=%ld\n", (long)getpid());
    return 0;
}
