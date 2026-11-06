#define HDMI_MODEL_TEST
#include "fx3-hdmi-registration-v1.c"
#include <assert.h>
static unsigned char request[16],reply[16];static unsigned int src=0x81cf6187,bytes=12,alloc_dst,free_dst,send_dst,setsrc;
static int alloc_rc,send_rc,free_rc,alloc_alias;static void *freed,*sent;static unsigned int allocations,releases,sends;
static int allocate(unsigned int d,void **p,unsigned int n,int wait){assert(n==12&&wait==1);allocations++;alloc_dst=d;*p=alloc_rc?0:alloc_alias?request:reply;return alloc_rc;}
static int release(unsigned int d,void *p){releases++;free_dst=d;freed=p;return free_rc;}
static void set_source(void *p,unsigned int s){assert(p==reply);setsrc=s;}
static int send(unsigned int d,void *p){sends++;send_dst=d;sent=p;return send_rc;}
static unsigned int size(void *p){assert(p==request);return bytes;}
static unsigned int source(void *p){assert(p==request);return src;}
static struct hdmi_io io={allocate,release,set_source,send,size,source};
static void reset(void){memset(observers,0,sizeof observers);memset(&live,0,sizeof live);fault=generation=0;alloc_rc=send_rc=free_rc=alloc_alias=0;allocations=releases=sends=0;src=0x81cf6187;bytes=12;unsigned char r[12]={0,0x25,0x27,1,12,0,1,0,0x16,1,0x2a,0x80};memcpy(request,r,12);}
int main(void){int rc=77;
 reset();assert(!dispatch(0x909a015b,request,&io,&rc)&&!allocations);bytes=8;assert(!dispatch(CP,request,&io,&rc));bytes=12;request[2]=2;assert(!dispatch(CP,request,&io,&rc));
 reset();request[4]=8;assert(dispatch(CP,request,&io,&rc)&&rc==-1024&&!allocations);
 reset();src=CP;assert(dispatch(CP,request,&io,&rc)&&rc==-1024&&!allocations);
 reset();alloc_rc=-1022;assert(dispatch(CP,request,&io,&rc)&&rc==-1022&&!releases&&!sends&&!observers[0]);
 reset();alloc_alias=1;assert(dispatch(CP,request,&io,&rc)&&rc==-1021&&fault&&!releases&&!sends);
 reset();send_rc=-1020;assert(dispatch(CP,request,&io,&rc)&&rc==-1020&&releases==1&&freed==reply&&!live.p&&!observers[0]);
 reset();assert(dispatch(CP,request,&io,&rc)&&rc==0&&releases==1&&freed==request&&free_dst==CP&&setsrc==CP&&alloc_dst==src&&send_dst==src);
 const unsigned char expected[12]={0,0x25,0x27,0x81,12,0,1,0,0,0,0,0};assert(!memcmp(reply,expected,12));for(int i=0;i<13;i++)assert(observers[i]==0x802a0116);
 assert(dispatch(CP,request,&io,&rc)&&rc==-1021&&allocations==1);assert(release_reply(src,reply,&io,&rc)&&rc==0&&!live.p);
 request[8]=0x17;assert(dispatch(CP,request,&io,&rc)&&rc==0&&live.lease==2);assert(release_reply(src,reply,&io,&rc)&&rc==0);for(int i=0;i<13;i++)assert(observers[i]==0x802a0117);
 send_rc=-1020;request[8]=0x18;assert(dispatch(CP,request,&io,&rc)&&rc==-1020);for(int i=0;i<13;i++)assert(observers[i]==0x802a0117);
 reset();assert(dispatch(CP,request,&io,&rc)&&rc==0);assert(release_reply(src+1,reply,&io,&rc)&&rc==-1021&&fault&&live.p);assert(!release_reply(src,request,&io,&rc));
 reset();free_rc=-1021;assert(dispatch(CP,request,&io,&rc)&&rc==0&&fault&&live.p);
 puts("HDMI registration: envelope, routing, thirteen fields, wire bytes, leases, repeat registration, allocation/send/free failures passed");return 0;
}
