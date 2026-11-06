#define FF_HOST_DIRECT 1
#define syscall fake_syscall
#define dladdr fake_dladdr
#include "fx3-capid-v49-touch100.c"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <stdarg.h>
#include <stddef.h>
static __thread int ecode;int *__errno_location(void){return &ecode;}
static __thread long tid97=7;static long pid97=3;
static pthread_mutex_t mutex97=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cond97=PTHREAD_COND_INITIALIZER;
long fake_syscall(long n,...){if(n!=98)return n==172?pid97:tid97;va_list a;va_start(a,n);unsigned*p=va_arg(a,unsigned*);int op=va_arg(a,int);int v=va_arg(a,int);va_end(a);assert((op==128||op==129)&&v==1);pthread_mutex_lock(&mutex97);if(op==128){while(__atomic_load_n(p,__ATOMIC_ACQUIRE)==1)pthread_cond_wait(&cond97,&mutex97);}else pthread_cond_signal(&cond97);pthread_mutex_unlock(&mutex97);return 0;}
int fake_dladdr(const void*p,struct cap_dl_info*d){(void)p;d->file="/usr/lib/appFw.so";d->base=0;return 1;}
struct message97{unsigned source,destination,n,kind,released;unsigned char data[80];};
static struct message97 *objects97[512];static unsigned object_count97,alloc_count97,send_count97,req_free97,reply_free97;
static __thread int alloc_rc97,send_rc97;static __thread void*delivered97;
static const unsigned char wire97[10]={13,32,70,1,10,0,1,128,1,0};
static struct message97*owner97(void*p){return (struct message97*)((unsigned char*)p-sizeof(unsigned)*5);}
static void*make97(unsigned from,unsigned n,unsigned kind){assert(object_count97<512);struct message97*m=calloc(1,sizeof *m);assert(m);m->source=from;m->destination=kind==1?0x92840747:from;m->n=n;m->kind=kind;objects97[object_count97++]=m;if(kind==1)memcpy(m->data,wire97,n<10?n:10);return m->data;}
static unsigned size97(void*p){return owner97(p)->n;}
static unsigned source97(void*p){assert(owner97(p)->kind==1&&!owner97(p)->released);return owner97(p)->source;}
static int allocate97(unsigned dst,void**p,unsigned n,unsigned wait){assert(n==12&&wait==1);alloc_count97++;if(alloc_rc97){*p=0;return alloc_rc97;}*p=make97(dst,n,2);return 0;}
static void src97(void*p,unsigned src){assert(src==0x92840747&&owner97(p)->kind==2);owner97(p)->source=src;}
static int send97(unsigned dst,void*p){struct message97*m=owner97(p);assert(m->kind==2&&!m->released&&m->destination==dst&&m->source==0x92840747&&m->n==12);const unsigned char reply[12]={13,32,70,17,12,0,1,128,0,0,89,0};assert(!memcmp(p,reply,12));send_count97++;if(!send_rc97)delivered97=p;return send_rc97;}
static int release97(unsigned dst,void*p){struct message97*m=owner97(p);assert(!m->released&&m->destination==dst);m->released=1;if(m->kind==1)req_free97++;else reply_free97++;return 0;}
static void reset97(void){for(unsigned i=0;i<object_count97;i++)free(objects97[i]);object_count97=0;memset(&virtual_panel,0,sizeof virtual_panel);memset(panel_live,0,sizeof panel_live);memset(panel_issued_generation,0,sizeof panel_issued_generation);memset(panel_retired,0,sizeof panel_retired);memset(live,0,sizeof live);panel_retired_cursor=0;serial=0;fault=0;enabled=initialized=1;process_owner=3;model.initialized=1;memset(&touch100,0,sizeof touch100);memset(touch100_live,0,sizeof touch100_live);memset(touch100_issued,0,sizeof touch100_issued);memset(touch100_retired,0,sizeof touch100_retired);touch100_cursor=0;pid97=3;tid97=7;allocate=allocate97;release=release97;send_msg=send97;set_source=src97;msg_size=size97;source=source97;alloc_count97=send_count97=req_free97=reply_free97=0;alloc_rc97=send_rc97=0;delivered97=0;}
static int dispatch97(void*p){enter();int r=touch100_dispatch(p);leave();return r;}
struct thread97{unsigned source;long tid;void*reply;int result;};
static void*worker97(void*v){struct thread97*t=v;tid97=t->tid;void*p;enter();p=make97(t->source,28,1);leave();t->result=dispatch97(p);t->reply=delivered97;return 0;}
int main(void){
 reset97();for(unsigned i=0;i<4;i++){unsigned from=0x81cf61c0+i;tid97=7+i;void*q=make97(from,10,1);assert(!dispatch97(q)&&!owner97(q)->released&&touch100.generation==i+1&&touch100.on&&touch100.pending);void*reply=delivered97;assert(dispatch97(q)==-1021);assert(!osal_free_msg(from,reply));assert(osal_free_msg(from,reply)==-1021);}assert(send_count97==4&&!req_free97&&reply_free97==4);
 reset97();void*q=make97(0x81cf61c4,10,1);alloc_rc97=-1022;assert(dispatch97(q)==-1022&&!touch100.generation&&!owner97(q)->released);alloc_rc97=0;send_rc97=-1020;assert(dispatch97(q)==-1020&&!touch100.generation&&!owner97(q)->released&&reply_free97==1);send_rc97=0;assert(!dispatch97(q)&&touch100.generation==1);void*reply=delivered97;tid97=8;assert(osal_free_msg(0x81cf61c4,reply)==-1021);tid97=7;assert(osal_free_msg(0x81cf61c5,reply)==-1021);assert(!osal_free_msg(0x81cf61c4,reply));
 for(unsigned b=0;b<10;b++){reset97();q=make97(0x81cf61c4,10,1);((unsigned char*)q)[b]^=1;assert(dispatch97(q)==-1024&&!alloc_count97&&!send_count97&&!touch100.generation&&!owner97(q)->released);}
 for(unsigned n=9;n<=11;n+=2){reset97();q=make97(0x81cf61c4,n,1);assert(dispatch97(q)==-1024&&!alloc_count97);}
 reset97();q=make97(0x90000001,10,1);assert(dispatch97(q)==-1024&&!alloc_count97);reset97();q=make97(0x81cf61c4,10,1);pid97=4;assert(dispatch97(q)==-1021&&!alloc_count97);reset97();puts("AP100_TOUCH_PASS exact10B/allbytes/source/size/process/repeated_independent_ON1/owned12B_1146_status590000/sourceQ/alloc_send_rollback/request_caller_owned/duplicate_live_reject/native_reply_free_once/tid_destination_guard/pending_hardware");return 0;}
