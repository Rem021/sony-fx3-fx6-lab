/* Explicit virtual CAPID storage, no capture producer or CP execution. */
typedef unsigned long size_t;
extern void *memcpy(void *,const void *,size_t);
extern void *memset(void *,int,size_t);
extern int memcmp(const void *,const void *,size_t);
extern int strcmp(const char *,const char *);
extern char *strstr(const char *,const char *);
extern char *getenv(const char *);
extern void *dlsym(void *,const char *);
extern int open(const char *,int,...);
extern long read(int,void *,size_t);
extern int close(int);
extern void *mmap(void *,size_t,int,int,int,long);
extern int sched_yield(void);
extern long syscall(long,...);
extern int dprintf(int,const char *,...);
extern int *__errno_location(void);
extern void _exit(int) __attribute__((noreturn));
#include "capid-service.h"
static unsigned char lock;
static void enter(void){while(__atomic_test_and_set(&lock,__ATOMIC_ACQUIRE))sched_yield();}
static void leave(void){__atomic_clear(&lock,__ATOMIC_RELEASE);}
static struct cap_service model;
static struct cap_table previous_table;
static int initialized,enabled,fault;
static long process_owner;
static int (*allocate)(unsigned int,void **,unsigned int,unsigned int);
static int (*release)(unsigned int,void *);
static void (*set_source)(void *,unsigned int);
static int (*send_msg)(unsigned int,void *);
static unsigned int (*msg_size)(void *),(*source)(void *);
static struct {void *p;unsigned int dst,command;unsigned long serial;} live[8];
static unsigned long serial;
static void initialize(void){
 if(initialized)return;
 allocate=dlsym((void *)-1,"osal_valloc_msg_wait");release=dlsym((void *)-1,"osal_free_msg");set_source=dlsym((void *)-1,"osal_set_msg_src");send_msg=dlsym((void *)-1,"osal_snd_msg");msg_size=dlsym((void *)-1,"osal_msg_size");source=dlsym((void *)-1,"osal_get_msg_src");
 if(!allocate||!release||!set_source||!send_msg||!msg_size||!source)_exit(126);
 const char *p=getenv("FX3_CAPID_STORAGE");enabled=p&&!strcmp(p,"reserved-v1");
 initialized=1;
}
static void reserve_table(void){
 if(enabled){
  process_owner=syscall(172);
  int claim=open("/tmp/fx3-capid.claim",0x200c1,0600);
  if(claim<0){fault=1;return;}dprintf(claim,"pid=%ld physical=41d800000 bytes=10000\n",process_owner);close(claim);
  char cmd[4096]={0};int fd=open("/proc/cmdline",0);long n=fd<0?-1:read(fd,cmd,sizeof cmd-1);if(fd>=0)close(fd);
  if(n<=0||!strstr(cmd,"memrsv=0x00010000@0x41d800000:uc")){fault=1;}
  else{fd=open("/dev/mem",2);void *area=fd<0?(void *)-1:mmap(0,0x5000,3,1,fd,0x41d800000UL);if(fd>=0)close(fd);
   if(area==(void *)-1)fault=1;else{model.table=area;model.address=0x41d800000ULL;memset(area,0,sizeof *model.table);}}
  dprintf(2,"FX3_CAPID_BIND enabled=1 physical=%#llx bytes=%#lx fault=%d exclusive_reservation_required=1 CP_executed=0\n",model.address,(unsigned long)sizeof(struct cap_table),fault);
 }
}
static int local(unsigned int id){return (id>>28)==8 && (id&0xfffffff);}
int osal_snd_msg(unsigned int dst,void *request){
 int saved=*__errno_location(),rc;enter();initialize();
 if(!enabled||(dst!=0x9004015e&&dst!=0x92850750)){leave();*__errno_location()=saved;return send_msg(dst,request);}
 if(!model.table&&!fault)reserve_table();
 if(process_owner!=syscall(172)){leave();*__errno_location()=saved;return -1021;}
 unsigned int size=request?msg_size(request):0,owner=0,op=0;const unsigned int *words=request;
 if(!request||fault||!model.table){leave();*__errno_location()=saved;return -1021;}
 if(dst==0x9004015e){
  if(size!=24||words[0]||words[2]||words[3]||words[4]||words[5])goto invalid;
  op=words[1];if(op<0x1000||op>0x1003)goto invalid;size=op==0x1000?16:op==0x1003?0:8;
 }else{if(size<16||size>sizeof(struct cap_table)+16)goto invalid;op=words[2];size=24;}
 owner=source(request);if(!local(owner))goto invalid;
 void *reply=0;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}
 if(size && slot<0){leave();*__errno_location()=saved;return -1021;}
 rc=size?allocate(owner,&reply,size,1):0;
 if(reply==request && reply){fault=1;rc=-1021;goto done;}
 for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;rc=-1021;goto done;}
 if(rc || (size&&!reply)){if(reply&&release(owner,reply))fault=1;rc=rc?rc:-1021;goto done;}
 struct cap_service before=model;memcpy(&previous_table,model.table,sizeof previous_table);unsigned char unused[16];
 rc=dst==0x9004015e?cap_control(&model,op,syscall(178),reply?reply:unused,&size):cap_sync(&model,request,msg_size(request),reply);
 unsigned long lease=0;
 if(!rc&&size){set_source(reply,dst);lease=++serial;live[slot].p=reply;live[slot].dst=owner;live[slot].command=op;live[slot].serial=lease;rc=send_msg(owner,reply);}
 if(rc){memcpy(model.table,&previous_table,sizeof previous_table);model=before;if(reply){memset(&live[slot],0,sizeof live[slot]);if(release(owner,reply))fault=1;}}
 else{int freed=release(dst,request);if(freed)fault=1;dprintf(2,"FX3_CAPID_COMMIT destination=%#x op=%#x source=%#x reply=%p lease=%lu bytes=%u request_free=%d header=%u,%u,%u,%u,%u initialized=%d\n",dst,op,owner,reply,lease,size,freed,model.table->header[0],model.table->header[1],model.table->header[2],model.table->header[3],model.table->header[4],model.initialized);}
 done:leave();*__errno_location()=saved;return rc;
 invalid:leave();*__errno_location()=saved;return -1024;
}
int osal_free_msg(unsigned int dst,void *p){
 int saved=*__errno_location(),found=-1;enter();initialize();for(int i=0;i<8;i++)if(live[i].p&&live[i].p==p){found=i;break;}
 if(found>=0 && process_owner!=syscall(172)){leave();*__errno_location()=saved;return -1021;}
 if(found<0){leave();*__errno_location()=saved;return release(dst,p);}
 int rc=live[found].dst==dst?release(dst,p):-1021;
 dprintf(2,"FX3_CAPID_NATIVE_FREE destination=%#x command=%#x lease=%lu result=%d\n",dst,live[found].command,live[found].serial,rc);
 if(rc)fault=1;else memset(&live[found],0,sizeof live[found]);leave();*__errno_location()=saved;return rc;
}
