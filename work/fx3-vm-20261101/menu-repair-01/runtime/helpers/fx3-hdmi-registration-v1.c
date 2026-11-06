/* FX3 software HDMI observer registration; source proof: hdmi-registration-proof.json.
 * No CP execution, condition changes, hotplug, output or frame readiness is modeled. */
#ifdef HDMI_MODEL_TEST
#define _GNU_SOURCE
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <sched.h>
#else
typedef unsigned long size_t;
extern void *memcpy(void *,const void *,size_t);
extern void *memset(void *,int,size_t);
extern int strcmp(const char *,const char *);
extern int dprintf(int,const char *,...);
extern int sched_yield(void);
extern int *__errno_location(void);
#define errno (*__errno_location())
#endif
static void enter(unsigned char *p){while(__atomic_test_and_set(p,__ATOMIC_ACQUIRE))sched_yield();}
static void leave(unsigned char *p){__atomic_clear(p,__ATOMIC_RELEASE);}
#define CP 0x909a015aU
struct hdmi_io {
 int (*allocate)(unsigned int,void **,unsigned int,int);
 int (*release)(unsigned int,void *);
 void (*set_source)(void *,unsigned int);
 int (*send)(unsigned int,void *);
 unsigned int (*size)(void *);
 unsigned int (*source)(void *);
};
static unsigned char lock;
static unsigned int observers[13],generation,fault;
static struct {void *p;unsigned int destination,lease;} live;
static unsigned int get16(const unsigned char *p){return p[0]|(unsigned int)p[1]<<8;}
static int local(unsigned int p){return (p>>28)==8 && (p&0xfffffff);}
static int dispatch(unsigned int dst,void *request,const struct hdmi_io *io,int *result){
 if(dst!=CP || !request || io->size(request)!=12)return 0;
 const unsigned char *in=request;
 if(get16(in)!=0x2500 || get16(in+2)!=0x127)return 0;
 if(get16(in+4)!=12 || get16(in+6)!=1){*result=-1024;return 1;}
 unsigned int observer;memcpy(&observer,in+8,4);unsigned int source=io->source(request);
 if(!local(observer)||!local(source)){*result=-1024;return 1;}
 enter(&lock);
 if(fault||live.p){*result=-1021;leave(&lock);return 1;}
 void *reply=0;int rc=io->allocate(source,&reply,12,1);
 if(reply==request && reply){fault=1;*result=-1021;leave(&lock);return 1;}
 if(rc||!reply){if(reply && io->release(source,reply))fault=1;*result=rc?rc:-1021;leave(&lock);return 1;}
 const unsigned char response[12]={0,0x25,0x27,0x81,12,0,1,0,0,0,0,0};
 memcpy(reply,response,12);io->set_source(reply,CP);
 unsigned int old[13];memcpy(old,observers,sizeof old);
 for(unsigned int i=0;i<13;i++)observers[i]=observer;
 live.p=reply;live.destination=source;live.lease=++generation;
 rc=io->send(source,reply);
 if(rc){memcpy(observers,old,sizeof old);memset(&live,0,sizeof live);if(io->release(source,reply))fault=1;*result=rc;leave(&lock);return 1;}
 int freed=io->release(CP,request);if(freed)fault=1;
 dprintf(2,"FX3_HDMI_REG_COMMIT observer=%#x reply_destination=%#x reply=%p lease=%u slots=13 request_free=%d hardware_verified=0\n",observer,source,reply,live.lease,freed);
 *result=0;leave(&lock);return 1;
}
static int release_reply(unsigned int dst,void *p,const struct hdmi_io *io,int *result){
 enter(&lock);int handled=live.p && live.p==p;
 if(handled){*result=dst==live.destination?io->release(dst,p):-1021;
 dprintf(2,"FX3_HDMI_REG_NATIVE_FREE destination=%#x expected=%#x reply=%p lease=%u result=%d\n",dst,live.destination,p,live.lease,*result);
 if(*result)fault=1;else memset(&live,0,sizeof live);}
 leave(&lock);return handled;
}
#ifndef HDMI_MODEL_TEST
extern void *dlsym(void *,const char *);
extern char *getenv(const char *);
extern void _exit(int) __attribute__((noreturn));
#define RTLD_NEXT ((void *)-1)
static struct hdmi_io native;
static unsigned char bindlock;
static int enabled,ready;
static void bind(void){
 enter(&bindlock);
 if(!ready){
 native.allocate=dlsym(RTLD_NEXT,"osal_valloc_msg_wait");native.release=dlsym(RTLD_NEXT,"osal_free_msg");
 native.set_source=dlsym(RTLD_NEXT,"osal_set_msg_src");native.send=dlsym(RTLD_NEXT,"osal_snd_msg");
 native.size=dlsym(RTLD_NEXT,"osal_msg_size");native.source=dlsym(RTLD_NEXT,"osal_get_msg_src");
 if(!native.allocate||!native.release||!native.set_source||!native.send||!native.size||!native.source)_exit(126);
 const char *p=getenv("FX3_HDMI_REGISTRATION");enabled=p&&!strcmp(p,"software-v1");ready=1;
 dprintf(2,"FX3_HDMI_REG_BIND enabled=%d profile=software-v1 original_transport=1\n",enabled);
 }
 leave(&bindlock);
}
int osal_snd_msg(unsigned int dst,void *p){
 int saved=errno;bind();int result;
 if(enabled && dispatch(dst,p,&native,&result)){errno=saved;return result;}
 errno=saved;return native.send(dst,p);
}
int osal_free_msg(unsigned int dst,void *p){
 int saved=errno;bind();int result;
 if(enabled && release_reply(dst,p,&native,&result)){errno=saved;return result;}
 errno=saved;return native.release(dst,p);
}
#endif
