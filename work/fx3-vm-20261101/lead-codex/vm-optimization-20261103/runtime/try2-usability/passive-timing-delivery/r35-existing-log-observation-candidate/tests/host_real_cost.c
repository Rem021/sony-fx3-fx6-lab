#include <unistd.h>
#include <sys/syscall.h>
#include <time.h>
unsigned long host_cost_ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (unsigned long)t.tv_sec*1000000000UL+t.tv_nsec;}
long host_cost_getpid(void){return syscall(SYS_getpid);}
