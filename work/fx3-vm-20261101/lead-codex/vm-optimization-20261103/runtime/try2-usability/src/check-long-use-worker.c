#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#define open fake_open
#define read fake_read
#define close fake_close
#define pread fake_pread
#define mmap fake_mmap
#define dlsym fake_dlsym
#define dlinfo fake_dlinfo
#define dlopen provider_dlopen
#define syscall fake_syscall
#define clock_gettime fake_clock
#define usleep fake_sleep
#define pthread_create fake_thread_create
#define pthread_detach fake_thread_detach
#define osal_free_msg provider_free
#define __errno_location fake_errno
#include "fx3-rm-empty-provider-v8-long-use.c"
static unsigned char page[65536];static unsigned idle,sent,freed,holds;static U nano=1000000000UL;static int fake_error;
struct packet95 {W source,n;unsigned char body[20];};
static W table_keys[7]={3,0x30,0x15,0x1af,0x1ac,0x1ab,0x1f8};
int*fake_errno(void){return &fake_error;}
int fake_open(const char*p,int flags,...){(void)flags;if(!strcmp(p,"/proc/cmdline"))return 1;if(!strcmp(p,"/dev/mem"))return 2;if(!strcmp(p,"/proc/self/mem"))return 3;if(!strcmp(p,"/tmp/fx3-keyworker96.identity"))return -1;assert(0);return -1;}
long fake_read(int fd,void*out,size_t n){assert(fd==1);const char*s="memrsv=0x00010000@0x41df00000:uc";assert(n>strlen(s));memcpy(out,s,strlen(s));return strlen(s);}
int fake_close(int fd){assert(fd==1||fd==2);return 0;}
void*fake_mmap(void*p,size_t n,int prot,int flags,int fd,long off){assert(!p&&n==65536&&prot==3&&flags==1&&fd==2&&(U)off==KEY93_PHYS);return page;}
long fake_syscall(long op,...){assert(op==178||op==172);return 42;}
int fake_clock(int id,struct ts*out){assert(id==1);out->s=nano/1000000000UL;out->n=nano%1000000000UL;nano+=1000;return 0;}
void*fake_loader(const char*n,int flags){assert(!strcmp(n,"libObj.so")&&flags==5);return (void*)17;}
void*fake_dlsym(void*h,const char*n){assert(h==(void*)-1&&!strcmp(n,"dlopen"));return (void*)fake_loader;}
int fake_dlinfo(void*h,int req,void*out){static struct lm m={0x1000000,0,0,0,0};assert(h==(void*)17&&req==2);*(struct lm**)out=&m;return 0;}
int fake_thread_create(U*t,const void*a,void*(*fn)(void*),void*arg){(void)t;(void)a;(void)fn;(void)arg;assert(0);return -1;}
int fake_thread_detach(U t){(void)t;assert(0);return -1;}
long fake_pread(int fd,void*out,size_t n,long at){assert(fd==3);U val=0;if((U)at==0x1000000+0x2cde48)val=0x5000000;else if((U)at==0x5000020)val=0x6000000;else if((U)at==0x500002c)val=7;else if((U)at==0x5000038)val=0x7000000;else if((U)at>=0x6000000&&(U)at<0x6000000+7*48){unsigned i=((U)at-0x6000000)/48;assert(((U)at-0x6000000)%48==8&&n==4);val=table_keys[i];}else if((U)at>=0x7000000&&(U)at<0x7000000+7*44){assert(((U)at-0x7000000)%44==8&&n==4);val=0;}else assert(0);assert(n==4||n==8);memcpy(out,&val,n);return n;}
static int alloc95(W dst,void**out,W n,W wait){assert(dst==0x807a0020U&&n==20&&wait==1);struct packet95*p=calloc(1,sizeof *p);p->n=n;*out=p->body;return 0;}
static struct packet95*owner95(void*p){return (struct packet95*)((unsigned char*)p-sizeof(W)*2);}
static W size95(void*p){return owner95(p)->n;}
static void source95(void*p,W src){assert(src==0x00410025);owner95(p)->source=src;}
static int free95(W dst,void*p){assert(dst==0x807a0020U);freed++;free(owner95(p));return 0;}
static int send95(W dst,void*p){assert(dst==0x807a0020U&&owner95(p)->source==0x00410025&&size95(p)==20);W*w=p;W expected_key=table_keys[(sent/2)%7];assert(w[0]==expected_key&&w[1]==0&&w[2]==(sent%2==0?1:0)&&w[3]==0&&w[4]==1);sent++;assert(!provider_free(dst,p));return 0;}
int fake_sleep(unsigned micro){nano+=(U)micro*1000;if(micro==100000){assert(sent%2==1);holds++;return 0;}assert(micro==5000);idle++;if(idle<=3){assert(!sent);return 0;}W done=*(W*)(page+24);assert(sent==done*2&&freed==sent);W c[3]={done+1,done<32?table_keys[done%7]:0x99,100};memcpy(page+8,c,12);return 0;}
int main(void){na=alloc95;ns=send95;nf=free95;nz=size95;nss=source95;receiver_seen=1;keyworker(0);assert(sent==64&&freed==64&&holds==32&&failed&&*(W*)(page+24)==32&&*(U*)(page+56)==64);puts("HOSTSTEP96_WORKER_PASS 32commands_31_32_boundary/ delete_exact20B/ actual_guest_worker_no_command_no_send/duplicate_no_replay/one_native_down_up_per_command/explicit_hold50_100/unknown_reject_before_send/exactsource20B/native_receiver_free_once");return 0;}
