#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#define LIGHT104_HOST 1
#define __errno_location __error
#define dlsym test_dlsym
#define dprintf test_dprintf
#define syscall test_syscall
#define clock_gettime test_clock_gettime
#define dladdr test_dladdr
#include "fx3-completion104-light-v1.c"
static unsigned call_count,alloc_count,snd_count;static void*expected;static void**expected_out;static int result_code,errno_code;static U relative=0xa12c;
static int real_complete(unsigned q,const void*p,U n){assert(q==0x808261c1&&p==expected&&n==4);assert(errno==91);call_count++;errno=errno_code;return result_code;}
static int real_alloc(unsigned q,void**p,unsigned n,unsigned wait){assert(q==0x808261c1&&p==expected_out&&n==4&&wait==1);assert(errno==91);alloc_count++;if(!result_code)*p=expected;errno=errno_code;return result_code;}
static int real_snd(unsigned q,void*p){assert(q==0x808261c1&&p==expected);assert(errno==91);snd_count++;errno=errno_code;return result_code;}
void*test_dlsym(void*h,const char*s){assert(h==(void*)-1);errno=601;if(!strcmp(s,"_ZN5mpgpe7message12SendDrawCompEjPKvm"))return real_complete;if(!strcmp(s,"osal_valloc_msg_wait"))return real_alloc;if(!strcmp(s,"osal_snd_msg"))return real_snd;assert(0);return 0;}
int test_dprintf(int fd,const char*fmt,...){assert(fd==2&&fmt);errno=602;return 0;}
long test_syscall(long n,...){assert(n==178);errno=603;return 287;}
int test_clock_gettime(int c,struct light_ts*t){assert(c==1);t->s=1;t->n=2;errno=604;return 0;}
int test_dladdr(const void*p,struct light_di*d){d->file="/usr/lib/libgpe.so";d->base=(void*)((U)p-relative);errno=605;return 1;}
int main(void){unsigned status=0;void*message=&status;expected=message;expected_out=&message;
 for(int i=0;i<2;i++){result_code=i?-1018:0;errno_code=i?1018:17;errno=91;assert(light_SendDrawComp(0x808261c1,&status,4)==result_code&&errno==errno_code);errno=91;assert(osal_valloc_msg_wait(0x808261c1,&message,4,1)==result_code&&errno==errno_code);errno=91;assert(osal_snd_msg(0x808261c1,message)==result_code&&errno==errno_code);}
 assert(call_count==2&&alloc_count==2&&snd_count==2);U rel;int in;relative=0xa12c;assert(!strcmp(path((void*)0x123456,&rel,&in),"original_SyncCallback_SendDrawComp_PLT")&&in&&rel==relative);relative=0x9c50;assert(!strcmp(path((void*)0x123456,&rel,&in),"original_Main_failure_SendDrawComp_PLT"));puts("AP104_LIGHT_EXACT_ONCE_ARGS_RESULTS_ERRNO_CALLER_PATH_ASAN_UBSAN_PASS");return 0;}
