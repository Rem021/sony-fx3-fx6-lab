#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>
#include <assert.h>
typedef unsigned long U;typedef unsigned W;struct ts{long s,n;};static U app_base;static unsigned char request[32],model[16];static W msglen=32;static unsigned mode,calls,sizes,reads,opens,closes;static char output[262144];static unsigned used;static _Alignas(64) unsigned char software[65536];
static int*test_errno(void){return &errno;}
#define __errno_location test_errno
static int test_log(int f,const char*fmt,...){(void)f;va_list a;va_start(a,fmt);int n=vsnprintf(output+used,sizeof output-used,fmt,a);va_end(a);assert(n>=0&&(unsigned)n<sizeof output-used);used+=n;errno=88;return n;}
#define dprintf test_log
static long test_syscall(long n,...){errno=89;assert(n==172||n==178);return n==172?228:427;}
#define syscall test_syscall
static int test_open(const char*p,int flags,...){(void)flags;opens++;errno=90;if(!strcmp(p,"/proc/self/mem"))return 10;if(!strcmp(p,"/proc/cmdline"))return 11;if(!strcmp(p,"/dev/mem"))return 12;if(!strcmp(p,"/tmp/fx3-date98-active.identity"))return 13;assert(0);return -1;}
#define open test_open
static int test_close(int fd){assert(fd>=10&&fd<=13);closes++;errno=91;return 0;}
#define close test_close
static long test_read(int fd,void*out,U n){assert(fd==11);const char*p="memrsv=0x00010000@0x41df00000:uc";assert(n>strlen(p));memcpy(out,p,strlen(p));return strlen(p);}
#define read test_read
static long test_pread(int fd,void*out,U n,long addr){assert(fd==10);reads++;errno=5;U p=addr;if(p==(U)request&&n<=32){if(mode==0)return -1;memcpy(out,request,n);return n;}if(app_base&&p==app_base+0x8365c90&&n==2){memcpy(out,model,n);return n;}if(app_base&&p==app_base+0x8227358&&n==4){memcpy(out,model+4,n);return n;}if(app_base&&p==app_base+0x822735c&&n==4){memcpy(out,model+8,n);return n;}return -1;}
#define pread test_pread
static void*test_mmap(void*p,U n,int prot,int flags,int fd,long off){assert(!p&&n==0x6000&&prot==3&&flags==1&&fd==12&&off==0x41df01000UL);return software+4096;}
#define mmap test_mmap
static int test_clock(int id,struct ts*t){assert(id==1);t->s=7;t->n=9;errno=93;return 0;}
#define clock_gettime test_clock
#include "fx3-date-observe98-v1.h"
static W sizefn(void*p){assert(p==request);sizes++;errno=94;return msglen;}
static int native(W dst,void*p){calls++;assert(errno==19);assert(dst==0x80900141||dst==7);if(p){assert(p==request);for(unsigned i=0;i<32;i++)assert(request[i]==i);request[2]=0xfe;}errno=5;return -1021;}
static void reset(void){for(unsigned i=0;i<32;i++)request[i]=i;used=calls=sizes=reads=opens=closes=0;output[0]=0;errno=19;}
static W d98_test_word(unsigned char*p){W x;memcpy(&x,p,4);return x;}static U getu(unsigned char*p){U x;memcpy(&x,p,8);return x;}
int main(void){memset(software,0x5a,sizeof software);memset(software+4096,0,0x6000);reset();app_base=0;assert(date98_sync(native,sizefn,0x80900141,request,0x1234)==-1021);assert(errno==5&&calls==1&&sizes==1&&opens==closes);assert(strstr(output,"captured=1 read_method=2 pread_errno=5")&&strstr(output,"000102030405")&&strstr(output,"0001fe030405"));unsigned char*p=software+4096,*r=p+64;assert(getu(p)==DATE98_MAGIC&&getu(p+32)==1&&getu(r)==4&&d98_test_word(r+48)==2&&(int)d98_test_word(r+52)==-1021&&d98_test_word(r+60)==1&&d98_test_word(r+64)==1&&d98_test_word(r+68)==2&&d98_test_word(r+72)==2&&d98_test_word(r+76)==1);assert(!memcmp(r+192,"\x00\x01\x02\x03",4)&&!memcmp(r+256,"\x00\x01\xfe\x03",4));for(unsigned i=0;i<4096;i++)assert(software[i]==0x5a);for(unsigned i=4096+0x6000;i<sizeof software;i++)assert(software[i]==0x5a);
 reset();mode=1;app_base=0x10000000;model[0]=1;model[1]=0;W a=2,b=0;memcpy(model+4,&a,4);memcpy(model+8,&b,4);assert(date98_sync(native,sizefn,0x80900141,request,0x1234)==-1021);assert(errno==5&&calls==1&&opens==closes);assert(strstr(output,"read_method=1")&&strstr(output,"force_current=1 force_next=0")&&strstr(output,"date_mask=3 date_current=2 date_next=0"));
 reset();assert(date98_sync(native,sizefn,7,request,0)==-1021);assert(errno==5&&calls==1&&sizes==0&&reads==0&&opens==0&&used==0);
 reset();assert(date98_sync(native,sizefn,0x80900141,0,0)==-1021);assert(errno==5&&calls==1&&sizes==0&&reads==0&&opens==0&&used==0);
 reset();msglen=4097;assert(date98_sync(native,sizefn,0x80900141,request,0)==-1021);assert(errno==5&&calls==1&&strstr(output,"captured=0"));msglen=32;
 reset();date98_events=64;assert(date98_sync(native,sizefn,0x80900141,request,0)==-1021);assert(errno==5&&calls==1&&strstr(output,"captured=0"));
 reset();U regs[31]={0};regs[0]=0xfffffc06;U copy[31];memcpy(copy,regs,sizeof regs);date98_point(97,0x2b72684,regs);assert(errno==19&&!memcmp(copy,regs,sizeof regs));for(unsigned i=0;i<32;i++)assert(request[i]==i);assert(model[0]==1&&model[1]==0);puts("DATE98_USER_PASS early_unbound_pmem_EIO_native_owned32_copy/full_original_before_after/errno_args_result_unchanged/fresh_model_read/input4K_and_neighbors_unchanged/bounds_cap/null_nondate/registers_preserved");}
