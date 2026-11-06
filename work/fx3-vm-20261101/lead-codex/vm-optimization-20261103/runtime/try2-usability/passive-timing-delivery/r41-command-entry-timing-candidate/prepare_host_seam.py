"""Reuse the actual v26 full-source host seam, replace only IO/clock mocks and narrow main."""
from pathlib import Path
import re
O=Path(__file__).resolve().parent;G=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-claude/impl/gpe-perf')
s=(G/'check_adapter.c').read_text();s=s[:s.index('static double now(void)')]
s=s.replace('#if CANDIDATE\n#include "fx3-gpe-observe-v26-perf.c"\n#else\n#include "fx3-gpe-observe-v25-reference.c"\n#endif', '#define FX3_GPE104_HOST_TEST 1\n#include ADAPTER_SOURCE')
s=s.replace('static void callback(const void*);', '''static void callback(const void*);
static char effects[8192];static unsigned effect_n;static void effect(char c){assert(effect_n+1<sizeof effects);effects[effect_n++]=c;effects[effect_n]=0;}
static char log_lines[64][2048];static unsigned log_n;static unsigned clocks;static unsigned long ns_value=1000000100UL;static int test_case,first_read_errno=-1;
static int seam_clock(int clock_id,struct timespec*t){assert(clock_id==CLOCK_MONOTONIC);effect('C');clocks++;errno=233;
 if(TEST_CANDIDATE&&clocks==1){if(test_case==3)return -1;t->tv_sec=test_case==4?0:1;t->tv_nsec=0;return 0;}
 unsigned long n=ns_value;ns_value+=test_case==2?1000000000UL:100UL;t->tv_sec=(long)(n/1000000000UL);t->tv_nsec=(long)(n%1000000000UL);return 0;}
static int seam_sleep(const struct timespec*a,struct timespec*b){(void)a;(void)b;effect('N');return 0;}
#define clock_gettime seam_clock
#define nanosleep seam_sleep''')
a='static int mock_printf(int fd,const char*fmt,...){(void)fd;(void)fmt;log_calls++;return 1;}'
b='''static int mock_printf(int fd,const char*fmt,...){(void)fd;log_calls++;effect('L');assert(log_n<64);va_list a;va_start(a,fmt);int n=vsnprintf(log_lines[log_n],2048,fmt,a);va_end(a);assert(n>=0&&n<2048);log_n++;errno=234;return n;}''';assert a in s;s=s.replace(a,b)
s=s.replace('static int mock_open(const char*path,int flags,...){(void)flags;', "static int mock_open(const char*path,int flags,...){effect('O');(void)flags;")
s=s.replace('static long mock_read(int fd,void*out,unsigned long n){', "static long mock_read(int fd,void*out,unsigned long n){effect('R');")
s=s.replace('static long mock_pread(int fd,void*out,unsigned long n,long p){(void)fd;', "static long mock_pread(int fd,void*out,unsigned long n,long p){effect('P');if(first_read_errno<0)first_read_errno=errno;(void)fd;")
s=s.replace('static int mock_close(int fd){(void)fd;', "static int mock_close(int fd){effect('X');(void)fd;")
s=s.replace('static void *mock_mmap(void*p,unsigned long n,int prot,int flags,int fd,long offset){', "static void *mock_mmap(void*p,unsigned long n,int prot,int flags,int fd,long offset){effect('M');")
s=s.replace('static int mock_munmap(void*p,unsigned long n){', "static int mock_munmap(void*p,unsigned long n){effect('U');")
s=s.replace('static long mock_syscall(long number,...){(void)number;return 0;}', "static long mock_syscall(long number,...){effect('S');return number==178?7301:0;}")
s=s.replace('callback_calls++;trace_order', "callback_calls++;effect('c');errno=25;trace_order")
s=s.replace('status_calls++;trace_order', "status_calls++;effect('s');errno=30;trace_order")
a='FILE*f=fopen("build/textures.bin","rb");assert(f);size_t n=fread(source,1,sizeof source,f);assert(n);fclose(f);for(size_t i=n;i<sizeof source;i++)source[i]=source[i%n];';assert a in s;s=s.replace(a,'memset(source,0x3a,sizeof source);')
s+='''
int main(int argc,char**argv){assert(argc==2);test_case=atoi(argv[1]);assert(test_case>=0&&test_case<=4);setup();
 unsigned char raw[144];fill_param(raw);raw[38]=0;p64(raw+40,(U)callback);p64(raw+48,0xabc);
 if(test_case==2)command_lock=1;
 effect_n=log_n=clocks=0;first_read_errno=-1;log_calls=status_calls=callback_calls=0;trace_pos=0;memset(trace_order,0,sizeof trace_order);errno=17;
 int result=command(0,test_case==1?1:0,0,71,0x123,raw);int after=errno;
 unsigned pixels=0;for(unsigned y=0;y<2;y++)for(unsigned x=0;x<16;x++){unsigned char*p=screen+0x100+((unsigned long)y*640+x)*2;uint16_t value;memcpy(&value,p,2);if(value==0x246f)pixels++;}
 if(test_case==1||test_case==2){assert(result==5&&callback_calls==0&&status_calls==0&&pixels==0);}else{assert(result==0&&callback_calls==1&&status_calls==1&&trace_pos==2&&trace_order[0]=='c'&&trace_order[1]=='s');assert(pixels==32);}
 assert(first_read_errno==17);
 printf("SUMMARY {\\"case\\":%d,\\"candidate\\":%d,\\"result\\":%d,\\"errno\\":%d,\\"first_read_errno\\":%d,\\"clock_calls\\":%u,\\"log_calls\\":%lu,\\"callback_calls\\":%lu,\\"SendDrawComp_calls\\":%lu,\\"pixels\\":%u,\\"effects\\":\\"%s\\",\\"callback_order\\":\\"%s\\"}\\n",test_case,TEST_CANDIDATE,result,after,first_read_errno,clocks,log_calls,callback_calls,status_calls,pixels,effects,trace_order);
 for(unsigned i=0;i<log_n;i++)printf("LOG %s",log_lines[i]);return 0;}
'''
(O/'tests/host_seam.c').write_text(s)
