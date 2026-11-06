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
struct cap_dl_info {const char *file;void *base;const char *symbol;void *address;};
extern int dladdr(const void *,struct cap_dl_info *);
/* AArch64 Linux futex, private to this process. Contenders must block:
 * a realtime receiver spinning in sched_yield can starve the lock owner. */
static unsigned int lock;
static void enter(void){for(;;){unsigned int expected=0;if(__atomic_compare_exchange_n(&lock,&expected,1,0,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED))return;syscall(98,&lock,128,1,0,0,0);}}
static void leave(void){__atomic_store_n(&lock,0,__ATOMIC_RELEASE);syscall(98,&lock,129,1,0,0,0);}
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
extern int sa_address_reply(const unsigned char *,unsigned char *);
static int sa_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=80)return -1021;
 const unsigned int *w=request;if(w[0]!=0xb850||w[3]||!local(w[2]))return -1024;
 unsigned int target=w[2],count=w[1]&65535,reverse=w[1]>>16;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(target,&reply,80,1);
 if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&live[i].p==reply){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(target,reply))fault=1;return rc?rc:-1021;}
 rc=sa_address_reply(request,reply);unsigned char status=((unsigned char *)reply)[6],detail=((unsigned char *)reply)[7];
 unsigned long long input=0,output=0;memcpy(&input,(unsigned char *)request+16,8);memcpy(&output,(unsigned char *)reply+16,8);
 if(!rc){set_source(reply,0x00930101);live[slot].p=reply;live[slot].dst=target;live[slot].command=0xb850;live[slot].serial=++serial;rc=send_msg(target,reply);}
 if(rc){memset(&live[slot],0,sizeof live[slot]);if(release(target,reply))fault=1;return rc;}
 int freed=release(0x00930101,request);if(freed)fault=1;
 dprintf(2,"FX3_SA_REPLY source=%#x count=%u reverse=%u first_input=%#llx first_output=%#llx status=%u detail=%u lease=%lu request_free=%d virtual_contract=1 original_CP=0\n",target,count,reverse,input,output,status,detail,live[slot].serial,freed);
 return 0;
}
#include "fx3-hdmi-audio-format.c"
static struct fx3_audio_format audio;
static int audio_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=10)return -1021;
 unsigned int from=source(request);if(!local(from))return -1024;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);
 if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct fx3_audio_format before=audio;rc=fx3_audio_format_apply(&audio,request,10,reply);
 if(!rc){set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x32d;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){audio=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_HDMI_AUDIO_COMMIT command=0x32d completion=0x132d source=%#x format=%u applied=%u notification_reason=%u raw_status=0x580000 lease=%lu request_free=%d active_output=0 audio_frames=0 CP_executed=0\n",from,audio.format,audio.applied,audio.notification_reason,live[slot].serial,freed);return 0;
}
#include "fx3-hdmi-photo-core.c"
static struct fx3_hdmi_photo photo;
static int photo_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=12)return -1021;
 unsigned int from=source(request);if(!local(from))return -1024;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);
 if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct fx3_hdmi_photo before=photo;rc=fx3_hdmi_photo_apply(&photo,request,12,reply);
 if(!rc){set_source(reply,0x909a015a);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x102;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){photo=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x909a015a,request);if(freed)fault=1;
 dprintf(2,"FX3_HDMI_PHOTO_COMMIT command=0x102 completion=0x8102 source=%#x raw=%u preset6=%u applied=%u lease=%lu request_free=%d active_output=0 frames=0 CP_executed=0\n",from,photo.raw,photo.preset6,photo.applied,live[slot].serial,freed);return 0;
}
#include "fx3-dmm-model.c"
static struct dmm_service remote_dmm;
static int dmm_bind(void){
 if(remote_dmm.memory)return 0;
 int fd=open("/tmp/fx3-dmm.claim",0x200c1,0600);if(fd<0)return -1021;
 dprintf(fd,"pid=%ld physical=41d900000 bytes=100000\n",process_owner);close(fd);
 char cmd[4096]={0};fd=open("/proc/cmdline",0);long n=fd<0?-1:read(fd,cmd,sizeof cmd-1);if(fd>=0)close(fd);
 if(n<=0||!strstr(cmd,"memrsv=0x00100000@0x41d900000:uc")){fault=1;return -1021;}
 fd=open("/dev/mem",2);void *p=fd<0?(void *)-1:mmap(0,DMM_TEST_SIZE,3,1,fd,DMM_TEST_PHYSICAL);if(fd>=0)close(fd);
 if(p==(void *)-1){fault=1;return -1021;}
 remote_dmm.memory=p;remote_dmm.physical=DMM_TEST_PHYSICAL;
 volatile unsigned int *probe=(volatile unsigned int *)((unsigned char *)p+DMM_TEST_SIZE-16);
 *probe=0x44534d4d;unsigned int readback=*probe;*probe=0;
 if(readback!=0x44534d4d){fault=1;return -1021;}
 dprintf(2,"FX3_REMOTE_DMM_BIND physical=%#llx bytes=%#x readback=%#x original_CP=0\n",remote_dmm.physical,DMM_TEST_SIZE,readback);return 0;
}
static int dmm_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=40)return -1021;
 unsigned int from=source(request);if(!local(from))return -1024;
 unsigned short op;memcpy(&op,request,2);if(!((op>=0x20&&op<=0x23)||op==0x2a))return -1024;
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 if(dmm_bind())return -1021;
 void *reply=0;int rc=allocate(from,&reply,40,1);
 if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct dmm_service before=remote_dmm;rc=dmm_service_reply(&remote_dmm,request,40,reply);
 unsigned int handle=0,length=0;unsigned long long address=0;short status=0;
 if(!rc){memcpy(&handle,(char *)reply+12,4);memcpy(&length,(char *)reply+32,4);memcpy(&address,(char *)reply+24,8);memcpy(&status,(char *)reply+2,2);set_source(reply,0x9061003c);live[slot].p=reply;live[slot].dst=from;live[slot].command=op;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){remote_dmm=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x9061003c,request);if(freed)fault=1;
 dprintf(2,"FX3_REMOTE_DMM_COMMIT op=%#x source=%#x status=%d handle=%#x address=%#llx bytes=%#x slots=%d/%d opens=%u/%u allocations=%llu lease=%lu request_free=%d virtual_storage=1 original_CP=0\n",op,from,status,handle,address,length,remote_dmm.slots[0].allocated,remote_dmm.slots[1].allocated,remote_dmm.slots[0].open_count,remote_dmm.slots[1].open_count,remote_dmm.allocations,live[slot].serial,freed);return 0;
}
#include "fx3-display-info.c"
static struct fx3_display_info display;
static int display_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=8)return -1021;
 unsigned int from=source(request);if(!local(from))return -1024;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,18,1);
 if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct fx3_display_info before=display;rc=fx3_display_info_apply(&display,request,8,reply);
 if(!rc){set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x16a;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){display=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_DISPLAY_INFO_COMMIT command=0x16a completion=0x116a source=%#x panel=640x480 evf=640x480 aspect=1/1 queries=%u lease=%lu request_free=%d virtual_geometry=1 physical_display=0 original_CP=0\n",from,display.queries,live[slot].serial,freed);return 0;
}
#include "fx3-vdf-config.c"
static struct fx3_vdf_config vdf_config;
static int vdf_config_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;
 unsigned int n=msg_size(request);if(n!=10&&n!=40)return -1024;unsigned int from=source(request);if(!local(from))return -1024;
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);
 if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 unsigned int command=((unsigned char *)request)[2];struct fx3_vdf_config before=vdf_config;
 rc=fx3_vdf_config_apply(&vdf_config,request,n,reply);
 if(!rc){set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=command|0x100;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){vdf_config=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_VDF_CONFIG_COMMIT command=%#x completion=%#x source=%#x raw_status=0x590000 pending_layouts=%u slope_known=%u/%u slope=%u/%u reset_pending=%#x slope_updates=%u lease=%lu request_free=%d pixels=0 active_output=0 original_CP=0\n",command|0x100,command|0x1100,from,vdf_config.pending_count,vdf_config.slope_known[0],vdf_config.slope_known[1],vdf_config.slope[0],vdf_config.slope[1],vdf_config.reset_pending,vdf_config.slope_updates,live[slot].serial,freed);return 0;
}
#include "fx3-vdf-plane.c"
static struct fx3_plane_config plane;
static int plane_dispatch(void *request){
 dprintf(2,"FX3_PLANE_TRACE step=entry fault=%d initialized=%d owner=%ld pid=%ld bytes=%u\n",fault,model.initialized,process_owner,syscall(172),msg_size(request));
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=776)return -1021;
 unsigned int from=source(request);if(!local(from))return -1024;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);
 if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 dprintf(2,"FX3_PLANE_TRACE step=allocated rc=%d reply=%p\n",rc,reply);
 struct fx3_plane_config before=plane;rc=fx3_plane_config_apply(&plane,request,776,reply);
 dprintf(2,"FX3_PLANE_TRACE step=applied rc=%d\n",rc);
 if(!rc){set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x147;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){plane=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_VDF_PLANE_COMMIT command=0x147 completion=0x1147 source=%#x raw_status=0x590000 records=24 bank=%u committed=%u pending_f024=%u lease=%lu request_free=%d pixels=0 active_output=0 original_CP=0\n",from,plane.next_bank^1,plane.committed,plane.pending_f024,live[slot].serial,freed);return 0;
}
#include "fx3-cec-power.c"
static struct fx3_cec_power cec;
static int cec_power_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=12)return -1021;
 unsigned int from=source(request);if(!local(from))return -1024;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,16,1);if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct fx3_cec_power before=cec;rc=fx3_cec_power_apply(&cec,request,12,reply);
 if(!rc){set_source(reply,0x909c015b);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x101;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){cec=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x909c015b,request);if(freed)fault=1;dprintf(2,"FX3_CEC_POWER_COMMIT command=0x101 completion=0x8101 source=%#x power=%u generation=%u lease=%lu request_free=%d hpd=0 wire_messages=0 originalCP=0 software_backend=1\n",from,cec.power,cec.generation,live[slot].serial,freed);return 0;
}
extern long pread(int,void *,size_t,long);
static void profile_stack(unsigned int dst,void *request,void *frame){
 static unsigned int count;unsigned int h=0;if(request&&msg_size(request)>=4)memcpy(&h,request,4);
 if(!(dst==0x909c015b||(dst==0x92840747&&h==0x0118200d))||count++>=6)return;
 int fd=open("/proc/self/mem",0);if(fd<0)return;unsigned long start=(unsigned long)frame,fp=start;
 dprintf(2,"FX3_PROFILE_STACK_BEGIN destination=%#x header=%#x tid=%ld frame=%p\n",dst,h,syscall(178),frame);
 for(unsigned int i=0;i<12;i++){unsigned long row[2];if(fp<start||fp-start>0x20000||(fp&15)||pread(fd,row,16,fp)!=16)break;
 struct cap_dl_info info={0};dladdr((void *)row[1],&info);dprintf(2,"FX3_PROFILE_FRAME depth=%u fp=%#lx lr=%#lx module=%s relative=%#lx\n",i,fp,row[1],info.file?info.file:"?",info.base?row[1]-(unsigned long)info.base:0);
 if(row[0]<=fp)break;fp=row[0];}close(fd);dprintf(2,"FX3_PROFILE_STACK_END destination=%#x\n",dst);
}
int osal_snd_msg(unsigned int dst,void *request){
 int saved=*__errno_location(),rc;enter();initialize();leave();
 profile_stack(dst,request,__builtin_frame_address(0));
 /* Validate original caller at the outermost interposer, outside model/loader locks.
  * Nested interposers may cease to tail-call after adding instrumentation. */
 if(dst==0x912503d0&&request&&msg_size(request)==8){
  unsigned int command;memcpy(&command,request,4);const char *p=getenv("FX3_CP_VERSION_TRANSPORT");
  struct cap_dl_info info={0};void *caller=__builtin_return_address(0);
  if(command==4&&p&&!strcmp(p,"unavailable-v1")&&dladdr(caller,&info)&&info.base&&(unsigned long)caller-(unsigned long)info.base==0x1984&&info.file&&(!strcmp(info.file,"/usr/lib/libupdaterufp.so")||!strcmp(info.file,"libupdaterufp.so"))){
   dprintf(2,"FX3_CP_VERSION_UNAVAILABLE command=4 bytes=8 source=%#x caller=%p caller_owned=1 reply_added=0 result=-1021 outermost_validated=1\n",source(request),caller);*__errno_location()=saved;return -1021;
  }
 }
 enter();
 const char *observe=getenv("FX3_VDF_OBSERVE");
 if((dst==0x92840747||dst==0x909a015a||dst==0x9061003c||dst==0x909c015b||dst==0x92b4086f)&&request&&observe&&!strcmp(observe,"1")){
  static unsigned int count;unsigned int n=msg_size(request);if(count++<64&&n<=1024){
   const unsigned char *p=request;char hex[2049];const char digits[]="0123456789abcdef";for(unsigned int i=0;i<n;i++){hex[2*i]=digits[p[i]>>4];hex[2*i+1]=digits[p[i]&15];}hex[2*n]=0;
   struct cap_dl_info where={0};dladdr(__builtin_return_address(0),&where);dprintf(2,"FX3_PROVIDER_CALLER module=%s relative=%#lx\n",where.file?where.file:"?",where.base?(unsigned long)__builtin_return_address(0)-(unsigned long)where.base:0);
   dprintf(2,"FX3_PROVIDER_REQUEST destination=%#x bytes=%u source=%#x caller=%p raw=%s dispatch_pending=1\n",dst,n,source(request),__builtin_return_address(0),hex);
  }
 }
 const char *cec_profile=getenv("FX3_CEC_POWER");
 if(enabled&&dst==0x909c015b&&request&&cec_profile&&!strcmp(cec_profile,"software-disconnected-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x01010000){int rc=cec_power_dispatch(request);leave();*__errno_location()=saved;return rc;}}
 const char *audio_profile=getenv("FX3_HDMI_AUDIO");
 if(enabled&&dst==0x92840747&&request&&audio_profile&&!strcmp(audio_profile,"inactive-format-v1")&&msg_size(request)>=4){
  unsigned int header;memcpy(&header,request,4);if(header==0x032d200d){int rc=audio_dispatch(request);leave();*__errno_location()=saved;return rc;}
 }
 const char *photo_profile=getenv("FX3_HDMI_PHOTO");
 if(enabled&&dst==0x909a015a&&request&&photo_profile&&!strcmp(photo_profile,"inactive-preset-v1")&&msg_size(request)>=4){
  unsigned int header;memcpy(&header,request,4);if(header==0x01022500){int rc=photo_dispatch(request);leave();*__errno_location()=saved;return rc;}
 }
 const char *dmm_profile=getenv("FX3_REMOTE_DMM");
 if(enabled&&dst==0x9061003c&&request&&dmm_profile&&!strcmp(dmm_profile,"two-slot-storage-v1")){int rc=dmm_dispatch(request);leave();*__errno_location()=saved;return rc;}
 const char *display_profile=getenv("FX3_DISPLAY_INFO");
 if(enabled&&dst==0x92840747&&request&&display_profile&&!strcmp(display_profile,"software-640x480-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x016a200d){int rc=display_dispatch(request);leave();*__errno_location()=saved;return rc;}}
 const char *config_profile=getenv("FX3_VDF_CONFIG");
 if(enabled&&dst==0x92840747&&request&&config_profile&&!strcmp(config_profile,"acceptance-shadow-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x014c200d||h==0x013d200d){int rc=vdf_config_dispatch(request);leave();*__errno_location()=saved;return rc;}}
 const char *plane_profile=getenv("FX3_VDF_PLANE");
 if(enabled&&dst==0x92840747&&request&&plane_profile&&!strcmp(plane_profile,"double-cache-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x0147200d){int rc=plane_dispatch(request);leave();*__errno_location()=saved;return rc;}}
 const char *sa=getenv("FX3_SA_ADDRESS");
 if(enabled&&dst==0x00930101&&sa&&!strcmp(sa,"source-ranges-v1")){int rc=sa_dispatch(request);leave();*__errno_location()=saved;return rc;}
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
