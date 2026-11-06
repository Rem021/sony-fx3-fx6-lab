#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "helpers/fx3-rm-empty-core-v2.h"
struct item{void*p;unsigned dst,n;int owned;};static struct item items[256];static int total,allocs,frees,sends,replays,failalloc,failsend,dead;static unsigned char last[136];static unsigned lastn;
static int a(unsigned d,void**p,unsigned n){if(failalloc)return -1;*p=malloc(n);assert(*p);assert(total<256);items[total++]=(struct item){*p,d,n,1};allocs++;return 0;}
static struct item*find(void*p){for(int i=total-1;i>=0;i--)if(items[i].p==p&&items[i].owned)return items+i;abort();}
static int f(unsigned d,void*p){struct item*i=find(p);assert(i->dst==d);i->owned=0;free(p);frees++;return 0;}
static int s(unsigned d,void*p){struct item*i=find(p);assert(i->dst==d);if(failsend)return -7;sends++;if(i->n==7){assert(!memcmp(p,rm93_empty,7));replays++;}else{lastn=i->n;memcpy(last,p,lastn);}return f(d,p);}
static void src(void*p,unsigned d){assert(find(p)->dst==d||d==RM93_ID);}
static int alive(unsigned d){return d&&!dead?1:0;}static void logx(const char*k,unsigned a,unsigned b,unsigned c){(void)k;(void)a;(void)b;(void)c;}
static struct rm93_ops o={a,s,f,src,alive,logx};
static void*req(unsigned cmd,unsigned n,unsigned declared,unsigned id){void*p=0;assert(!a(RM93_ID,&p,n));memset(p,0,n);if(n>=24){rm93_put(p,cmd,4);rm93_put((unsigned char*)p+4,1,2);rm93_put((unsigned char*)p+6,declared,2);rm93_put((unsigned char*)p+8,0x80af6111,4);if(n>=28)rm93_put((unsigned char*)p+24,id,4);}return p;}
int main(void){struct rm93_state m={0};void*p=req(9,136,112,0);assert(!rm93_process(&m,&o,p,136));assert(lastn==136&&!memcmp(last+24,rm93_config,112)&&rm93_u32(last+12)==0);
 p=req(3,28,4,0x80af6180);assert(!rm93_process(&m,&o,p,28));assert(m.notify==0x80af6180&&m.generation==1&&replays==1&&lastn==28);
 p=req(3,28,4,0x80af6180);assert(!rm93_process(&m,&o,p,28));assert(m.generation==2&&replays==2);/* Original replays once on each explicit duplicate registration. */
 p=req(3,28,4,0);assert(!rm93_process(&m,&o,p,28));assert(m.notify==0&&replays==2);
 p=req(3,28,4,0x80af6181);assert(!rm93_process(&m,&o,p,28));assert(m.notify==0x80af6181&&replays==3);
 p=req(0x777,40,16,0);assert(!rm93_process(&m,&o,p,40));assert(lastn==24&&rm93_u32(last+12)==RM93_UNKNOWN&&rm93_u16(last+6)==0);
 for(unsigned len=0;len<24;len++){p=req(9,len,0,0);assert(rm93_process(&m,&o,p,len)==-2);}
 for(unsigned len=24;len<50;len++){p=req(3,len,65535,0);assert(!rm93_process(&m,&o,p,len));assert(lastn==24&&rm93_u32(last+12)==RM93_UNKNOWN);}
 p=req(9,136,112,0);failalloc=1;assert(rm93_process(&m,&o,p,136)==-5);failalloc=0;
 p=req(9,136,112,0);failsend=1;assert(rm93_process(&m,&o,p,136)==-6);failsend=0;
 p=req(3,28,4,0x80af6182);failsend=1;assert(rm93_process(&m,&o,p,28)==-6);assert(m.notify==0);failsend=0;
 p=req(9,136,112,0);dead=1;assert(!rm93_process(&m,&o,p,136));/* Receive-only dynamic reply queue remains valid without callback. */p=req(3,28,4,0x80af6189);assert(!rm93_process(&m,&o,p,28));assert(m.notify==0&&rm93_u32(last+12)==RM93_ERROR);dead=0;
 assert(allocs==frees);for(int i=0;i<total;i++)assert(!items[i].owned);puts("RM93 ASAN_UBSAN PASS lengths/config/replay/duplicate/cancel/unknown/failures/exactownership");return 0;}
