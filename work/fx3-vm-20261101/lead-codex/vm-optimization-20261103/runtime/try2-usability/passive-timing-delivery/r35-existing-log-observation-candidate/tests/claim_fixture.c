/* Exact original bind_ram body. Actual host O_EXCL file; only Linux flag
 * translation, cmdline, physical mmap and syscall facilities are mocked. */
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <string.h>
#include <assert.h>
#include <stdarg.h>
typedef unsigned long U;typedef unsigned W;
static volatile U *ram;static char *claim_path;static unsigned char memory[65536];static unsigned maps;
static int m_open(const char*p,int f,...){if(strstr(p,".claim"))return open(claim_path,O_RDWR|O_CREAT|O_EXCL,0600);if(!strcmp(p,"/proc/cmdline"))return 10001;return 10002;}
static long m_read(int fd,void*b,U n){const char*s="memrsv=0x00010000@0x41dc00000:uc";memcpy(b,s,strlen(s));return strlen(s);}
static int m_close(int fd){return fd>=10000?0:close(fd);}
static void *m_mmap(void*a,U n,int p,int f,int fd,long at){assert(n==65536&&at==0x41dc00000UL);maps++;return memory;}
static long m_syscall(long n,...){assert(n==172);return syscall(SYS_getpid);}
#define open m_open
#define read m_read
#define close m_close
#define mmap m_mmap
#define syscall m_syscall
#include "original-bind-ram.inc"
int main(int argc,char**argv){assert(argc==3);claim_path=argv[1];int expected=atoi(argv[2]);int rc=bind_ram();assert(rc==expected);if(!rc){assert(maps==1);int second=bind_ram();assert(second==-1&&maps==1);}else assert(!maps);printf("CLAIM rc=%d maps=%u actual_host_O_EXCL=1 mock_physical_map=1\n",rc,maps);return 0;}
