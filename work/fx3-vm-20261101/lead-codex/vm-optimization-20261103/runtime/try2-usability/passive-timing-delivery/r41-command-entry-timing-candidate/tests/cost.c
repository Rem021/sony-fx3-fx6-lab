/* Finite host-only cost: actual old/new return helper with real host clock,
 * bounded vsnprintf sink instead of serial output. No hardware/QEMU estimate. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <time.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <assert.h>
#include <stdlib.h>
typedef unsigned long U;
static int *host_errno(void){return &errno;}
#define __errno_location host_errno
static volatile unsigned long bytes_written;
static int sink_printf(int fd,const char*fmt,...){(void)fd;char b[512];va_list a;va_start(a,fmt);int n=vsnprintf(b,sizeof b,fmt,a);va_end(a);assert(n>0&&n<(int)sizeof b);bytes_written+=(unsigned long)n;return n;}
static long host_tid(long n,...){assert(n==178);return 7301;}
#define dprintf sink_printf
#define syscall host_tid
#define FX3_GPE102_HOST_TEST 1
#define FX3_GPE104_HOST_TEST 1
#include "fx3-gpe-command-wait102-v1.h"
#include RETURN_HEADER
static U wall(void){struct timespec t;assert(!clock_gettime(CLOCK_MONOTONIC,&t));return(U)t.tv_sec*1000000000UL+(U)t.tv_nsec;}
int main(int argc,char**argv){assert(argc==2);unsigned count=(unsigned)atoi(argv[1]);assert(count>0&&count<=100000);for(unsigned trial=0;trial<3;trial++){
 bytes_written=0;U begin=wall();for(unsigned i=0;i<count;i++){
#if TEST_CANDIDATE
 int saved=*__errno_location();U entry=gpe102_now();*__errno_location()=saved;gpe104_command_return(i,0,0x123,0,entry);
#else
 gpe104_command_return(i,0,0x123,0);
#endif
 }U end=wall();printf("%d,%u,%u,%lu,%lu\n",TEST_CANDIDATE,trial,count,end-begin,bytes_written);
 }return 0;}
