#include <stdio.h>
#include <unistd.h>

int main(void) {
    printf("PLAN_LIBS_SMOKE_OK\n");
    printf("pid=%ld\n", (long)getpid());
    return 0;
}
