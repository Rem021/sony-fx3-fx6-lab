#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
typedef unsigned long U;
static int test_errno,callback_count,complete_count,dynamic_count;static const void*expected_pointer;static unsigned expected_target;static int dynamic_result;
int*__errno_location(void){return &test_errno;}
long syscall(long n,...){assert(n==178||n==172);test_errno=919;return 275;}
int dprintf(int fd,const char*f,...){(void)fd;(void)f;test_errno=999;return 0;}
static U gpe102_now(void){test_errno=818;return 104000;}
static unsigned char profile_storage[0x80000];
void*mmap(void*p,U n,int prot,int flags,int fd,long off){(void)p;(void)prot;(void)flags;(void)fd;assert(n==0x80000&&off==0x41d640000UL);return profile_storage;}
int munmap(void*p,U n){(void)p;(void)n;return 0;}
#include "fx3-gpe-profile104-v1.h"
#define FX3_GPE104_HOST_TEST 1
#include "fx3-complete104-observe-v2-profile104.h"
static void cb(const void*p){assert(p==expected_pointer&&test_errno==41);callback_count++;test_errno=42;}
static int complete(unsigned q,const void*p,size_t n){assert(q==expected_target&&p==expected_pointer&&n==4&&test_errno==43);complete_count++;test_errno=1018;return 0;}
static int dynamic(unsigned flags,unsigned module,void*arg){assert(test_errno==51);dynamic_count++;if(flags==0x2a){assert(module==0x82);if(!dynamic_result)*(unsigned*)arg=0x808261c0;}else{assert(flags==0x4a&&module==0&&(U)arg==0x808261c0);}test_errno=52;return dynamic_result;}
static int peek(U p,void*out,U n){assert(n==4);memcpy(out,(void*)p,n);test_errno=888;return 1;}
int main(void){pr104_init(9);struct pr104_context profile;pr104_begin(&profile,437,4,0x808261c0);unsigned status=0;expected_pointer=&status;expected_target=0x808261c0;test_errno=41;gpe104_callback(cb,&status,437,4,0,expected_target,123);assert(callback_count==1&&test_errno==42&&status==0);test_errno=43;assert(gpe104_complete(complete,expected_target,&status,4,437,4,0)==0);assert(complete_count==1&&test_errno==1018&&status==0);
 unsigned q=0;test_errno=51;assert(gpe104_dynamic(dynamic,peek,0x2a,0x82,&q,0xa7b4)==0&&q==0x808261c0&&test_errno==52);test_errno=51;assert(gpe104_dynamic(dynamic,peek,0x4a,0,(void*)0x808261c0UL,0xa41c)==0&&test_errno==52);dynamic_result=-1018;test_errno=51;q=0;assert(gpe104_dynamic(dynamic,peek,0x2a,0x82,&q,0xa7b4)==-1018&&q==0&&test_errno==52);assert(dynamic_count==3);
 test_errno=71;gpe104_command_return(437,4,expected_target,5);assert(test_errno==71);pr104_finish(&profile,5,0,24);assert(pr104_ring[5]==1&&!pr104_current);puts("AP104_PROFILE_PASSIVE_CALLBACK_SEND_DYNAMIC_EXACT_ONCE_ARGUMENTS_RESULTS_ERRNO_ASAN_UBSAN_PASS");}
