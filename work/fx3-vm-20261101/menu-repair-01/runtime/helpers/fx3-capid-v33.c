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
 const char *boot=getenv("FX3_BOOT_REPLY");if(enabled&&boot&&!strcmp(boot,"timecode-getfunc-muted-v1"))dprintf(2,"FX3_BOOT_REPLY_BOUND version=31 strict44B=1 dynamic_reply_id=source padding_observe_only=1 muted_capabilities=80x16\n");
 const char *tail=getenv("FX3_BOOT_TAIL");if(enabled&&tail&&!strcmp(tail,"audited-panel-hdmi-v1"))dprintf(2,"FX3_BOOT_TAIL_BOUND version=32 panel165_exact=1 inactive_hdmi=1 backup_observation_required=1 physical_output=0\n");
 const char *pin=getenv("FX3_PIN_GRAPH");if(enabled&&pin&&!strcmp(pin,"empty-owned-mode1-v1"))dprintf(2,"FX3_PIN_GRAPH_BOUND version=33 endpoint_whitelist=22 allowed_edges=11 no_frames=1 native_transport=1\n");
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
#include "fx3-hdmi-tc.c"
static struct fx3_hdmi_tc hdmi_tc;
static int hdmi_tc_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=12)return -1021;
 unsigned int from=source(request);if(!local(from))return -1024;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct fx3_hdmi_tc before=hdmi_tc;rc=fx3_hdmi_tc_apply(&hdmi_tc,request,12,reply);
 if(!rc){set_source(reply,0x909a015a);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x109;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){hdmi_tc=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x909a015a,request);if(freed)fault=1;dprintf(2,"FX3_HDMI_TC_COMMIT command=0x109 completion=0x8109 source=%#x tc_output=%u updates=%u lease=%lu request_free=%d active_output=0 hardware_frames=0 originalCP=0 software_backend=1\n",from,hdmi_tc.tc_output,hdmi_tc.updates,live[slot].serial,freed);return 0;
}
#include "fx3-monitor-lut.c"
static struct fx3_monitor_lut monitor_lut;
static int monitor_lut_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=10)return -1021;
 unsigned int from=source(request);if(!local(from))return -1024;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct fx3_monitor_lut before=monitor_lut;rc=fx3_monitor_lut_apply(&monitor_lut,request,10,reply);
 if(!rc){set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x161;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){monitor_lut=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x92840747,request);if(freed)fault=1;dprintf(2,"FX3_MONITOR_LUT_COMMIT command=0x161 completion=0x1161 source=%#x mode=%u/%u updates=%u pending_f029=%u lease=%lu request_free=%d physical_LUT=0 active_conversion=0 originalCP=0 software_backend=1\n",from,monitor_lut.mode[0],monitor_lut.mode[1],monitor_lut.updates,monitor_lut.pending_f029,live[slot].serial,freed);return 0;
}
#include "fx3-release-inhibit.c"
static struct fx3_release_inhibit release_inhibit;
static int release_inhibit_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=16||release_inhibit.active_release)return -1021;
 unsigned int from=source(request);if(from!=0x80020002)return -1024;int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);if(reply==request&&reply){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct fx3_release_inhibit before=release_inhibit;rc=fx3_release_inhibit_apply(&release_inhibit,request,16,reply);
 if(!rc){set_source(reply,0x90040193);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x403d;live[slot].serial=++serial;rc=send_msg(from,reply);}
 if(rc){release_inhibit=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 dprintf(2,"FX3_RELEASE_INHIBIT_COMMIT command=0x403d source=%#x mask=%#x token=%#x updates=%u lease=%lu status=0xf000 active_release=0 request_caller_owned=1 request_free=not_called originalCP=0 software_idle_only=1\n",from,release_inhibit.mask,release_inhibit.last_token,release_inhibit.updates,live[slot].serial);return 0;
}

/* Bounded software acceptance from vdf011a-0159-proof.json; no hardware completion. */
static struct lcd_shadow {unsigned char payload[6],selector,brightness;unsigned int pending_hardware,updates;} lcd;
static struct osd_shadow {unsigned char legacy[4];unsigned int pending_f030,updates;} osd;
static const unsigned char lcd_packet[14]={0x0d,0x20,0x1a,1,14,0,1,0x80,1,14,0,14,6,0};
static int lcd_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;
 if(msg_size(request)!=14||memcmp(request,lcd_packet,14))return -1024;
 unsigned int from=source(request);if(!local(from))return -1024;
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);
 if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct lcd_shadow before=lcd;
 memcpy(lcd.payload,(unsigned char *)request+8,6);lcd.selector=1;lcd.brightness=6;lcd.pending_hardware=1;lcd.updates++;
 const unsigned char completion[12]={0x0d,0x20,0x1a,0x11,12,0,1,0x80,0,0,0,0};memcpy(reply,completion,12);
 set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x11a;live[slot].serial=++serial;rc=send_msg(from,reply);
 if(rc){lcd=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_LCD_BRIGHTNESS_COMMIT command=0x11a completion=0x111a source=%#x selector=1 brightness=6 pending_hardware=1 updates=%u lease=%lu request_free=%d software_backend=1 physical_complete=0\n",from,lcd.updates,live[slot].serial,freed);return 0;
}
static int osd_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;
 const unsigned char header[8]={0x0d,0x20,0x59,1,10,0,1,0x80};
 if(msg_size(request)!=10||memcmp(request,header,8))return -1024;
 const unsigned char *p=request;if(p[9]||(p[8]!=3&&p[8]!=7)||!local(source(request)))return -1024;
 struct osd_shadow before=osd;memset(osd.legacy,0,4);osd.legacy[0]=p[8];osd.pending_f030=1;osd.updates++;
 unsigned int from=source(request);int rc=release(0x92840747,request);
 if(rc){osd=before;fault=1;return rc;}
 dprintf(2,"FX3_OSD_ONOFF_ACCEPT command=0x159 source=%#x mask=%u pending_f030=1 updates=%u reply_added=0 request_free=0 software_backend=1 physical_complete=0\n",from,osd.legacy[0],osd.updates);return 0;
}

static void *muted_memory;
static unsigned int muted_volume_updates,muted_address_queries;
static int muted_bind(void){
 if(muted_memory)return 0;
 int fd=open("/tmp/fx3-adf-muted.claim",0x200c1,0600);if(fd<0)return -1021;
 dprintf(fd,"pid=%ld physical=41da00000 bytes=10000 muted=1 original_sound=0\n",process_owner);close(fd);
 char cmd[4096]={0};fd=open("/proc/cmdline",0);long n=fd<0?-1:read(fd,cmd,sizeof cmd-1);if(fd>=0)close(fd);
 if(n<=0||!strstr(cmd,"memrsv=0x00010000@0x41da00000:uc")){fault=1;return -1021;}
 fd=open("/dev/mem",2);void *p=fd<0?(void *)-1:mmap(0,0x10000,3,1,fd,0x41da00000UL);if(fd>=0)close(fd);
 if(p==(void *)-1){fault=1;return -1021;}memset(p,0,0x10000);muted_memory=p;
 dprintf(2,"FX3_ADF_MUTED_BIND physical=0x41da00000 bytes=65536 muted=1 original_sound=0 playback_supported=0\n");return 0;
}
static int muted_dispatch(void *request,unsigned int command){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;
 const unsigned char volume[10]={0x0d,0x20,0x2e,3,10,0,1,0x80,8,0},query[8]={0x0d,0x20,0x3d,3,8,0,1,0x80};
 unsigned int size=command==0x32e?10:8,out_size=command==0x32e?12:24;
 if((command!=0x32e&&command!=0x33d)||msg_size(request)!=size||memcmp(request,command==0x32e?volume:query,size))return -1024;
 unsigned int from=source(request);if(!local(from))return -1024;
 if(command==0x33d){int rc=muted_bind();if(rc)return rc;}
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,out_size,1);
 if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 unsigned char *p=reply;memset(p,0,out_size);p[0]=0x0d;p[1]=0x20;p[2]=command&255;p[3]=0x13;p[4]=out_size;p[6]=1;p[7]=0x80;
 if(command==0x33d){unsigned long long physical=0x41da00000ULL;memcpy(p+16,&physical,8);}
 set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=command;live[slot].serial=++serial;rc=send_msg(from,reply);
 if(rc){memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 if(command==0x32e)muted_volume_updates++;else muted_address_queries++;
 int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_ADF_MUTED_COMMIT command=%#x source=%#x status=0 bytes=%u physical=%#llx wire_volume=8 internal_volume=7 muted=1 original_sound=0 request_free=%d lease=%lu\n",command,from,out_size,command==0x33d?0x41da00000ULL:0ULL,freed,live[slot].serial);return 0;
}


#include "fx3-adf-file-core-v2.c"
extern long pread(int,void *,size_t,long);
static unsigned char ff_mem_before[FF_SIZE],ff_transfer_before[FF_CAP];
static unsigned int ff_pending[8];
static int ff_bind(void){
 if(file_model.memory)return 0;int fd=open("/tmp/fx3-adf-file.claim",0x200c1,0600);if(fd<0)return -1021;dprintf(fd,"pid=%ld physical=41db00000 bytes=60000 muted=1\n",process_owner);close(fd);
 char cmd[4096]={0};fd=open("/proc/cmdline",0);long n=fd<0?-1:read(fd,cmd,sizeof cmd-1);if(fd>=0)close(fd);if(n<=0||!strstr(cmd,"memrsv=0x00060000@0x41db00000:uc"))return -1021;
 fd=open("/dev/mem",2);void *p=fd<0?(void *)-1:mmap(0,FF_SIZE,3,1,fd,FF_BASE);if(fd>=0)close(fd);if(p==(void *)-1)return -1021;memset(p,0,FF_SIZE);file_model.memory=p;
 dprintf(2,"FX3_ADF_FILE_BIND physical=0x41db00000 bytes=0x60000 slots=6 stride=0x10000 capacity=0xc800 muted=1 original_sound=0\n");return 0;
}
static int ff_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=40)return -1021;unsigned int from=source(request);if(!local(from))return -1024;
 if(ff_bind())return -1021;int lease=-1;for(int i=0;i<8;i++)if(!live[i].p){lease=i;break;}if(lease<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,40,1);if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}if(rc||!reply){if(reply)release(from,reply);return rc?rc:-1021;}
 struct ff_model before=file_model;memcpy(ff_mem_before,file_model.memory,FF_SIZE);rc=ff_reply(request,reply);unsigned int op=ff_get(request,2),h=0;unsigned long long cp=0;
 if(!rc){h=ff_get((unsigned char *)reply+12,4);memcpy(&cp,(unsigned char *)reply+24,8);set_source(reply,0x9061003c);live[lease].p=reply;live[lease].dst=from;live[lease].command=op;live[lease].serial=++serial;rc=send_msg(from,reply);}
 if(rc){memcpy(file_model.memory,ff_mem_before,FF_SIZE);file_model=before;memset(live+lease,0,sizeof live[lease]);if(release(from,reply))fault=1;dprintf(2,"FX3_ADF_FILE_REJECT op=%#x result=%d request_owned_by_caller=1\n",op,rc);return rc;}
 int freed=release(0x9061003c,request);if(freed)fault=1;dprintf(2,"FX3_ADF_FILE_DMM op=%#x source=%#x handle=%#x CPphysical=%#llx capacity=%#x lease=%lu request_free=%d muted=1\n",op,from,h,cp,ff_get((unsigned char *)reply+32,4),live[lease].serial,freed);return 0;
}
static int ff_read_pointer(unsigned long address,void *p,unsigned int n){
#ifdef FF_HOST_DIRECT
 if(!address)return 0;memcpy(p,(void *)address,n);return 1;
#else
 int fd=open("/proc/self/mem",0);long rc=fd<0?-1:pread(fd,p,n,address);if(fd>=0)close(fd);return rc==n;
#endif
}
static int ff_beep_range(unsigned long long physical,unsigned int size,unsigned int kind,unsigned int *offset){
 if(kind<10){if(physical<0x41da00000ULL||physical>=0x41da10000ULL||!size||size>0x41da10000ULL-physical)return 0;*offset=physical-0x41da00000ULL;return 1;}
 for(unsigned int i=0;i<6;i++)if(file_model.slots[i].allocated&&file_model.slots[i].transferred&&physical==ff_cp(i)&&size&&size<=FF_CAP){*offset=0;return 1;}return 0;
}
static void ff_capture_local(const unsigned char p[40]){
 unsigned int op=ff_get(p,2),h=ff_get(p+12,4);if((short)ff_get(p+2,2)||(h&0x8000))return;
 if(op==0x8023){int i=ff_local_index(h);if(i>=0){file_locals[i].live=0;dprintf(2,"FX3_ADF_FILE_LOCAL_FREE handle=%#x\n",h);}return;}
 if((op!=0x8020&&op!=0x8021)||ff_get(p+16,4)!=0x70817||ff_get(p+8,2)!=1)return;
 unsigned int cap=ff_get(p+32,4);unsigned long long physical=0;memcpy(&physical,p+24,8);if(cap<FF_CAP||!physical)return;
 int found=-1;for(int i=0;i<8;i++)if(file_locals[i].live&&(file_locals[i].handle&1023)==(h&1023)){found=i;break;}if(found<0)for(int i=0;i<8;i++)if(!file_locals[i].live){found=i;break;}if(found<0)return;
 file_locals[found]=(struct ff_local){h,cap,1,physical};dprintf(2,"FX3_ADF_FILE_LOCAL_CAPTURE handle=%#x physical=%#llx capacity=%#x native_reply_free0=1\n",h,physical,cap);
}
static int ff_icdt(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||msg_size(request)!=48)return -1021;
 unsigned char *p=request;unsigned long pointers[2];unsigned int src[2],dst[2],length=ff_get(p+16,4),mode=ff_get(p+20,4);unsigned long callback=0,context=0,probe=0;
 memcpy(pointers,p,16);memcpy(&callback,p+24,8);memcpy(&context,p+32,8);struct cap_dl_info ci={0};
 if(!ff_read_pointer(pointers[0],src,8)||!ff_read_pointer(pointers[1],dst,8)||!context||!ff_read_pointer(context,&probe,8)||!callback||(callback&3)||!dladdr((void *)callback,&ci)||!ci.base||callback-(unsigned long)ci.base!=0x2e1574c)return -1024;
 int index=ff_transfer_check(src[0],src[1],dst[0],dst[1],length,mode);if(index<0){dprintf(2,"FX3_ICDT_REJECT source=%#x dest=%#x length=%u mode=%u result=%d callback_sent=0\n",src[0],dst[0],length,mode,index);return index;}
 int lease=-1;for(int i=0;i<8;i++)if(!live[i].p){lease=i;break;}if(lease<0)return -1021;void *reply=0;int rc=allocate(0x0282078f,&reply,24,1);if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}if(rc||!reply){if(reply)release(0x0282078f,reply);return rc?rc:-1021;}
 struct ff_slot before=file_model.slots[index];unsigned int result_before=ff_get(p+40,4);unsigned char *dest=file_model.memory+index*0x10000+dst[1];memcpy(ff_transfer_before,dest,length);memset(dest,0,length);
 struct ff_slot *slot=file_model.slots+index;slot->transferred=slot->pending=1;slot->source_handle=src[0];slot->source_offset=src[1];slot->dest_offset=dst[1];slot->length=length;slot->callback=callback;slot->context=context;
 memset(reply,0,24);memcpy(reply,&callback,8);memcpy((unsigned char *)reply+8,&context,8);ff_put(p+40,0,4);set_source(reply,0x02820746);live[lease].p=reply;live[lease].dst=0x0282078f;live[lease].command=0x1cd7;live[lease].serial=++serial;ff_pending[lease]=index+1;rc=send_msg(0x0282078f,reply);
 if(rc){memcpy(dest,ff_transfer_before,length);file_model.slots[index]=before;ff_put(p+40,result_before,4);ff_pending[lease]=0;memset(live+lease,0,sizeof live[lease]);if(release(0x0282078f,reply))fault=1;return rc;}
 dprintf(2,"FX3_ICDT_MUTED_COMMIT source=%#x source_offset=%#x dest=%#x dest_offset=%#x length=%u mode=%u callback=%#lx context=%#lx CPphysical=%#llx APbacking=%#llx lease=%lu request_caller_owned=1 request_result=0 original_sound=0 real_DMA=0\n",src[0],src[1],dst[0],dst[1],length,mode,callback,context,ff_cp(index),FF_BASE+(unsigned long long)index*0x10000,live[lease].serial);return 0;
}

struct beep_entry {unsigned char raw[32];unsigned int valid,volume;};
static struct beep_entry beep[14];
static int beep_reject(unsigned int command,unsigned int kind,const char *reason,unsigned int original_status){
 dprintf(2,"FX3_ADF_BEEP_REJECT command=%#x kind=%u reason=%s original_status=%#x reply_added=0 muted=1 original_sound=0\n",command,kind,reason,original_status);return -1024;
}
static int beep_dispatch(void *request,unsigned int command){
 if(fault||!model.initialized||process_owner!=syscall(172)||!muted_memory||!request)return -1021;
 unsigned char *p=request;unsigned int n=command==0x327?40:10,kind=0;
 if((command!=0x327&&command!=0x32a)||msg_size(request)!=n||p[0]!=13||p[1]!=32||p[2]!=(command&255)||p[3]!=3||p[4]!=n||p[5]||p[6]!=1||p[7]!=128)return beep_reject(command,0,"wire",0);
 unsigned int from=source(request);if(!local(from))return beep_reject(command,0,"source",0);
 struct beep_entry next[14];memcpy(next,beep,sizeof next);unsigned long long physical=0;unsigned int size=0,offset=0;
 if(command==0x327){
  kind=p[20];if(!kind||kind>13||p[22]>1)return beep_reject(command,kind,"operation_or_kind",0xe004);
  if(p[22]==0){for(unsigned int i=8;i<40;i++)if(i!=20&&p[i])return beep_reject(command,kind,"unregister_fields",0);next[kind].valid=0;memset(next[kind].raw,0,32);}
  else{
   memcpy(&physical,p+8,8);memcpy(&size,p+16,4);
   if(!ff_beep_range(physical,size,kind,&offset))return beep_reject(command,kind,"backing_bounds",0);
   unsigned int cont=0,first=0;memcpy(&cont,p+28,4);memcpy(&first,p+32,4);
   if(p[23]||p[24]!=(cont!=0)||p[25]||p[26]||p[27]||p[36]||p[37]||p[38]||p[39]||first>size||cont>size)return beep_reject(command,kind,"descriptor_fields",0);
   if(p[21]!=(kind==4?3:kind==10||kind==11?4:6))return beep_reject(command,kind,"priority",0);
   if(next[kind].valid&&memcmp(next[kind].raw,p+8,32))return beep_reject(command,kind,"descriptor_conflict",0xe004);
   memcpy(next[kind].raw,p+8,32);next[kind].valid=1;
  }
 }else{
  kind=p[9];if(kind>13)return beep_reject(command,kind,"kind",0);
  if(p[8]>=8)return beep_reject(command,kind,"volume_bounds",0xe002);
  if(kind)next[kind].volume=p[8];else for(unsigned int i=1;i<14;i++)next[i].volume=p[8];
 }
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 unsigned char completion[12]={13,32,0,19,12,0,1,128,0,0,0,0};completion[2]=command&255;memcpy(reply,completion,12);
 set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=command;live[slot].serial=++serial;rc=send_msg(from,reply);
 if(rc){memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 memcpy(beep,next,sizeof beep);int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_ADF_BEEP_COMMIT command=%#x tid=%ld kind=%u registered=%u volume=%u phys=%#llx offset=%#x size=%u lease=%lu request_free=%d muted=1 original_sound=0 playback_supported=0\n",command,syscall(178),kind,beep[kind].valid,beep[kind].volume,physical,offset,size,live[slot].serial,freed);return 0;
}

extern long pread(int,void *,size_t,long);
static void profile_stack(unsigned int dst,void *request,void *frame){
 static unsigned int count,boot_count,file_count;unsigned int h=0;if(request&&msg_size(request)>=4)memcpy(&h,request,4);
 if(dst==0x92840747){if(count++>=64)return;}else if(dst==0x5503e0){if(boot_count++>=32)return;}else if(dst==0x9061003c||dst==0x0061003c||dst==0x02820746){if(file_count++>=64)return;}else return;
 int fd=open("/proc/self/mem",0);if(fd<0)return;unsigned long start=(unsigned long)frame,fp=start;
 dprintf(2,"FX3_PROFILE_STACK_BEGIN destination=%#x header=%#x tid=%ld frame=%p\n",dst,h,syscall(178),frame);
 for(unsigned int i=0;i<12;i++){unsigned long row[2];if(fp<start||fp-start>0x20000||(fp&15)||pread(fd,row,16,fp)!=16)break;
 struct cap_dl_info info={0};dladdr((void *)row[1],&info);dprintf(2,"FX3_PROFILE_FRAME depth=%u fp=%#lx lr=%#lx module=%s relative=%#lx\n",i,fp,row[1],info.file?info.file:"?",info.base?row[1]-(unsigned long)info.base:0);
 if(row[0]<=fp)break;fp=row[0];}close(fd);dprintf(2,"FX3_PROFILE_STACK_END destination=%#x\n",dst);
}

static void *gf_live_request[8];static void *tc_live_request[8];static unsigned int tc_live_padding[8];
static unsigned int tc_stack_mask(void *frame){int fd=open("/proc/self/mem",0);if(fd<0)return 0;unsigned long start=(unsigned long)frame,fp=start;unsigned int mask=0;for(int i=0;i<16;i++){unsigned long row[2];if(fp<start||fp-start>0x20000||(fp&15)||pread(fd,row,16,fp)!=16)break;struct cap_dl_info info={0};if(dladdr((void *)row[1],&info)&&info.base&&info.file){unsigned long rel=row[1]-(unsigned long)info.base;if(strstr(info.file,"dataflowInfraFramework.so")&&rel==0x33f20)mask|=1;if(strstr(info.file,"appFw.so")&&rel==0x2debc58)mask|=2;if(strstr(info.file,"appFw.so")&&rel==0x2b66f2c)mask|=4;}if(row[0]<=fp)break;fp=row[0];}close(fd);return mask;}
static const unsigned char tc_frozen[52]={0xc0,0x61,0xcf,0x81,0xa0,0xa0,0xa0,0xa0,0x1,0x0,0x34,0x0,0x18,0x0,0x0,0x0,0x34,0x0,0x0,0x0,0x7f,0x0,0x0,0x0,0x1,0x20,0x5,0x2,0x1c,0x0,0x1,0x0,0x1,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0};
static int timecode_dispatch(void *request,unsigned int caller_mask){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;
 if(msg_size(request)!=52||caller_mask!=7)return -1024;unsigned int from=source(request),reply_id=0,padding=0;memcpy(&reply_id,request,4);memcpy(&padding,(unsigned char *)request+20,4);
 if(!from||from!=reply_id||!local(from))return -1024;
 const unsigned char *q=request;for(int i=4;i<52;i++)if((i<20||i>=24)&&q[i]!=tc_frozen[i])return -1024;
 int slot=-1;for(int i=0;i<8;i++){if(tc_live_request[i]==request&&live[i].p)return -1021;if(!live[i].p&&slot<0)slot=i;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,36,1);if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 const unsigned char packet[36]={0,0,0,0,0xa0,0xa0,0xa0,0xa0,1,0,36,0,24,0,0,0,36,0,0,0,0,0,0,0,1,0x20,5,0x12,12,0,1,0,0,0,0,0};memcpy(reply,packet,36);set_source(reply,0x9059000e);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x1205;live[slot].serial=++serial;tc_live_request[slot]=request;tc_live_padding[slot]=padding;rc=send_msg(from,reply);
 if(rc){memset(&live[slot],0,sizeof live[slot]);tc_live_request[slot]=0;tc_live_padding[slot]=0;if(release(from,reply))fault=1;return rc;}
 int freed=release(0x9059000e,request);if(freed)fault=1;dprintf(2,"FX3_TIMECODE_COMMIT source=%#x destination=0x9059000e bytes=36 reply_source=0x9059000e request=%p padding=%08x request_free=%d caller_mask=%u lease=%lu software_ack=1 physical_timecode=0\n",from,request,padding,freed,caller_mask,live[slot].serial);return 0;
}
static int get_func_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;const unsigned char req[8]={13,32,0x25,3,8,0,1,128};if(msg_size(request)!=8||memcmp(request,req,8))return -1024;unsigned int from=source(request);if(!local(from))return -1024;
 int slot=-1;for(int i=0;i<8;i++){if(gf_live_request[i]==request&&live[i].p)return -1021;if(!live[i].p&&slot<0)slot=i;}if(slot<0)return -1021;void *reply=0;int rc=allocate(from,&reply,28,1);if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}unsigned char packet[28]={13,32,0x25,0x13,28,0,1,128,0,0,0,0};memset(packet+12,128,16);memcpy(reply,packet,28);set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x325;live[slot].serial=++serial;gf_live_request[slot]=request;rc=send_msg(from,reply);if(rc){gf_live_request[slot]=0;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}int freed=release(0x92840747,request);if(freed)fault=1;dprintf(2,"FX3_ADF_GET_FUNC_COMMIT source=%#x bytes=28 capabilities=80x16 lowcut=80 request_free=%d lease=%lu muted=1 original_sound=0 playback_supported=0 complementary_AP_flags_not_audio_support=1\n",from,freed,live[slot].serial);return 0;
}


struct tail_panel {unsigned int shadow_valid,selector,enumeration,pending_hardware,cache_valid,cache_enum,updates;};
struct tail_hdmi {unsigned int definition_known,definition,resolution_known,next_port,rate_known[5],rate[5],updates;unsigned char parameters[8];};
static struct tail_panel panel165;static struct tail_hdmi hdmi_boot;static struct {void *request;unsigned int kind;} tail_live[8];static int (*backup_observed)(unsigned int *);
static int tail_dispatch(unsigned int dst,void *request,unsigned int command){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;unsigned int n=msg_size(request),from=source(request),kind=0,port=0,rate=0,backup=0,known=0;if(!local(from))return -1024;
 const unsigned char *q=request;const char *surface=getenv("FX3_DISPLAY_INFO"),*inactive=getenv("FX3_HDMI_BOOT");
 if(dst==0x92840747&&command==0x165){const unsigned char exact[10]={13,32,0x65,1,10,0,1,128,2,0};if(!surface||strcmp(surface,"software-640x480-v1")||n!=10||memcmp(q,exact,10))return -1024;kind=1;}
 else if(dst==0x909a015a){if(!inactive||strcmp(inactive,"disconnected-inactive-v1")||!hdmi_tc.known||hdmi_tc.tc_output)return -1024;
  if(command==0x10a){const unsigned char exact[12]={0,37,10,1,12,0,1,0,0,0,0,0};if(n!=12||memcmp(q,exact,12))return -1024;kind=2;}
  else if(command==0x101){const unsigned char exact[16]={0,37,1,1,16,0,1,0,0,0,0,0,6,5,0,0};if(n!=16||memcmp(q,exact,16))return -1024;kind=3;}
  else if(command==0x117){const unsigned char exact[8]={0,37,23,1,12,0,1,0};if(n!=12||memcmp(q,exact,8))return -1024;port=q[8];rate=q[9];if(!backup_observed)backup_observed=dlsym((void *)-1,"fx3_observed_backup_rate");if(backup_observed)known=backup_observed(&backup);dprintf(2,"FX3_HDMI_RATE_OBSERVE source=%#x port=%u rate=%u echoed_port=%u echoed_rate=%u backup_known=%u backup_02cf1493=%u next_port=%u before_admission=1\n",from,port,rate,q[10],q[11],known,backup,hdmi_boot.next_port);const unsigned char expected[5]={0,0,17,17,0};if(!known||port>=5||port!=hdmi_boot.next_port||q[10]!=port||q[11]!=rate||rate!=(backup==7?7:expected[port]))return -1024;kind=4;}
  else return -1024;
 }else return -1024;
 int slot=-1;for(int i=0;i<8;i++){if(tail_live[i].request&&live[i].p&&((kind==1&&tail_live[i].kind==1)||(kind>=2&&tail_live[i].kind>=2)||tail_live[i].request==request))return -1021;if(!live[i].p&&slot<0)slot=i;}if(slot<0)return -1021;
 struct tail_panel before_panel=panel165;struct tail_hdmi before_hdmi=hdmi_boot;
 if(kind==1){panel165.shadow_valid=1;panel165.selector=2;panel165.enumeration=0;panel165.pending_hardware=1;panel165.updates++;}
 else if(kind==2){hdmi_boot.definition_known=1;hdmi_boot.definition=0;hdmi_boot.updates++;}
 else if(kind==3){hdmi_boot.resolution_known=1;memcpy(hdmi_boot.parameters,q+8,8);hdmi_boot.updates++;}
 else {hdmi_boot.rate_known[port]=1;hdmi_boot.rate[port]=rate;hdmi_boot.next_port++;hdmi_boot.updates++;}
 void *reply=0;int rc=allocate(from,&reply,12,1);if(reply&&reply==request){fault=1;panel165=before_panel;hdmi_boot=before_hdmi;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;panel165=before_panel;hdmi_boot=before_hdmi;return -1021;}if(rc||!reply){panel165=before_panel;hdmi_boot=before_hdmi;if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 unsigned char out[12]={0};if(kind==1){const unsigned char exact[12]={13,32,0x65,0x11,12,0,1,128,0,0,89,0};memcpy(out,exact,12);}else {out[1]=37;out[2]=command&255;out[3]=129;out[4]=12;out[6]=1;if(kind==2)out[8]=1;}memcpy(reply,out,12);set_source(reply,dst);live[slot].p=reply;live[slot].dst=from;live[slot].command=command;live[slot].serial=++serial;tail_live[slot].request=request;tail_live[slot].kind=kind;rc=send_msg(from,reply);
 if(rc){panel165=before_panel;hdmi_boot=before_hdmi;memset(tail_live+slot,0,sizeof tail_live[slot]);memset(live+slot,0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 if(kind==1){panel165.cache_valid=1;panel165.cache_enum=0;}int freed=release(dst,request);if(freed)fault=1;dprintf(2,"FX3_BOOT_TAIL_COMMIT destination=%#x command=%#x source=%#x kind=%u port=%u rate=%u backup_known=%u backup=%u reply_status=%#x lease=%lu request_free=%d selector=%u enum=%u cache_valid=%u pending_hardware=%u hpd=0 output_ready=0 physical_output=0\n",dst,command,from,kind,port,rate,known,backup,kind==1?0x590000:kind==2?1:0,live[slot].serial,freed,panel165.selector,panel165.enumeration,panel165.cache_valid,panel165.pending_hardware);return 0;
}
static void boot_tail_observe(unsigned int dst,void *request,void *frame,unsigned int op){
 if(!request||(!(dst&0x80000000U)&&dst!=0x912f0335&&dst!=0x92840747))return;unsigned int n=msg_size(request),magic=0,head=0;if(n>=8)memcpy(&magic,(unsigned char *)request+4,4);if(n>=4)memcpy(&head,request,4);int flow=n>=24&&magic==0xa0a0a0a0U;int late=dst==0x912f0335||(dst==0x92840747&&(head==0x0328200d||head==0x0119200d));if(!flow&&!late)return;
 static unsigned int flow_count,late_count;unsigned int seq=__atomic_add_fetch(flow?&flow_count:&late_count,1,__ATOMIC_RELAXED),limit=flow?512:64;if(seq>limit){if(seq==limit+1)dprintf(2,"FX3_BOOT_TAIL_OBSERVE_LIMIT flow=%d limit=%u\n",flow,limit);return;}unsigned int bytes=n<=2048?n:2048;char raw[4097];const char *h="0123456789abcdef";for(unsigned int i=0;i<bytes;i++){unsigned char c=((unsigned char *)request)[i];raw[2*i]=h[c>>4];raw[2*i+1]=h[c&15];}raw[bytes*2]=0;dprintf(2,"FX3_BOOT_TAIL_REQUEST tid=%ld destination=%#x op=%u source=%#x bytes=%u observed=%u flow=%d truncated=%d raw=%s attempt_only=1 reply_added_here=0\n",syscall(178),dst,op,source(request),n,seq,flow,bytes!=n,raw);
 int fd=open("/proc/self/mem",0);unsigned long start=(unsigned long)frame,fp=start;for(int i=0;fd>=0&&i<14;i++){unsigned long row[2];if(fp<start||fp-start>0x20000||(fp&15)||pread(fd,row,16,fp)!=16)break;struct cap_dl_info info={0};dladdr((void *)row[1],&info);dprintf(2,"FX3_BOOT_TAIL_FRAME destination=%#x seq=%u depth=%d fp=%#lx lr=%#lx module=%s relative=%#lx\n",dst,seq,i,fp,row[1],info.file?info.file:"?",info.base?row[1]-(unsigned long)info.base:0);if(row[0]<=fp)break;fp=row[0];}if(fd>=0)close(fd);
}


#include "fx3-pin-core-v1.c"
static struct pin_graph pins;
static struct {void *request;long sender;unsigned long generation,peer_generation,serial;int index,peer;unsigned command,owner;} pin_live[8];
static struct {void *pointer;unsigned destination;unsigned long serial;unsigned char fingerprint[56];} pin_retired[64];static unsigned pin_retired_cursor;
static void pin_forget_retired(void *p){for(int i=0;i<64;i++)if(pin_retired[i].pointer==p)memset(pin_retired+i,0,sizeof pin_retired[i]);}
static int pin_duplicate_free(unsigned dst,void *p){if(!p)return 0;for(int i=0;i<64;i++)if(pin_retired[i].pointer==p&&pin_retired[i].destination==dst){unsigned char now[56];int fd=open("/proc/self/mem",0);long n=fd<0?-1:pread(fd,now,56,(long)p);if(fd>=0)close(fd);if(n!=56||!memcmp(now,pin_retired[i].fingerprint,56)){dprintf(2,"FX3_PIN_DUPLICATE_FREE_REJECT destination=%#x pointer=%p serial=%lu\n",dst,p,pin_retired[i].serial);return 1;}memset(pin_retired+i,0,sizeof pin_retired[i]);}return 0;}
unsigned int fx3_pin_snapshot(void *out,unsigned int capacity){int saved=*__errno_location();enter();unsigned int n=0;if(out&&pins.ready&&!pins.fault&&process_owner==syscall(172)&&capacity>=sizeof pins){memcpy(out,&pins,sizeof pins);n=sizeof pins;}leave();*__errno_location()=saved;return n;}
static int pin_dispatch(unsigned dst,void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;if(!pins.ready){pg_init(&pins);dprintf(2,"FX3_PIN_GRAPH_REGISTER endpoints=22 owners=8 edges_allowed=11 cold_state=1 queues_empty=1 buffers_registered=0 physical_output=0 pending_hardware=1\n");}
 for(int i=0;i<8;i++)if(pin_live[i].request==request&&live[i].p)return -1021;
 struct pin_graph before=pins;unsigned char packet[56];struct pin_result r={0};int rc=pg_request(&pins,dst,request,msg_size(request),source(request),packet,&r);if(rc){dprintf(2,"FX3_PIN_REQUEST_REJECT owner=%#x bytes=%u result=%d no_reply=1\n",dst,msg_size(request),rc);return rc;}
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0){pins=before;return -1021;}
 void *reply=0;rc=allocate(r.reply_id,&reply,56,1);if(reply&&reply==request){pins=before;fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){pins=before;fault=1;return -1021;}if(rc||!reply){pins=before;if(reply&&release(r.reply_id,reply))fault=1;return rc?rc:-1021;}
 pin_forget_retired(reply);memcpy(reply,packet,56);set_source(reply,dst);live[slot].p=reply;live[slot].dst=r.reply_id;live[slot].command=0x8000|r.command;live[slot].serial=++serial;
 pin_live[slot].request=request;pin_live[slot].sender=syscall(178);pin_live[slot].index=r.index;pin_live[slot].peer=r.peer;pin_live[slot].command=r.command;pin_live[slot].owner=dst;pin_live[slot].serial=r.serial;
 if(r.index>=0){pins.pins[r.index].reply_refs++;pin_live[slot].generation=pins.pins[r.index].generation;}
 if(r.peer>=0&&r.peer!=r.index){pins.pins[r.peer].reply_refs++;pin_live[slot].peer_generation=pins.pins[r.peer].generation;}
 rc=send_msg(r.reply_id,reply);if(rc){pins=before;memset(pin_live+slot,0,sizeof pin_live[slot]);memset(live+slot,0,sizeof live[slot]);if(release(r.reply_id,reply))fault=1;return rc;}
 int freed=release(dst,request);if(freed)fault=1;unsigned state=r.index>=0?pins.pins[r.index].state:255;int peer=r.index>=0?pins.pins[r.index].peer:-1;
 char raw[113];const char *h="0123456789abcdef";for(int i=0;i<56;i++){raw[2*i]=h[packet[i]>>4];raw[2*i+1]=h[packet[i]&15];}raw[112]=0;
 dprintf(2,"FX3_PIN_COMMIT owner=%#x reply_destination=%#x outer_reply_id=%#x command=%u status=%d index=%d peer=%d state=%u generation=%lu pin_serial=%lu lease=%lu request_free=%d padding=%08x raw=%s software_graph=1 queues_empty=1 buffers_registered=0 physical_output=0\n",dst,r.reply_id,pg_get(packet),r.command,r.status,r.index,peer,state,r.index>=0?pins.pins[r.index].generation:0,r.serial,live[slot].serial,freed,r.padding,raw);return 0;
}
static int pin_can_retire(int slot){if(!pin_live[slot].request)return 1;if(pin_live[slot].sender!=syscall(178)){dprintf(2,"FX3_PIN_FOREIGN_THREAD_FREE_REJECT lease=%lu sender=%ld actual=%ld\n",live[slot].serial,pin_live[slot].sender,syscall(178));return 0;}int a=pin_live[slot].index,b=pin_live[slot].peer;if((a>=0&&(!pins.pins[a].reply_refs||pins.pins[a].generation!=pin_live[slot].generation))||(b>=0&&b!=a&&(!pins.pins[b].reply_refs||pins.pins[b].generation!=pin_live[slot].peer_generation))){dprintf(2,"FX3_PIN_STALE_LEASE_REJECT lease=%lu\n",live[slot].serial);return 0;}return 1;}
static void pin_retire(int slot,void *p,const unsigned char fingerprint[56]){int a=pin_live[slot].index,b=pin_live[slot].peer;if(a>=0)pins.pins[a].reply_refs--;if(b>=0&&b!=a)pins.pins[b].reply_refs--;unsigned i=pin_retired_cursor++%64;pin_retired[i].pointer=p;pin_retired[i].destination=live[slot].dst;pin_retired[i].serial=live[slot].serial;memcpy(pin_retired[i].fingerprint,fingerprint,56);dprintf(2,"FX3_PIN_CONSUMED owner=%#x command=%u pin_serial=%lu lease=%lu sender=%ld consumer=%ld state=%u connections=%lu queues_empty=1 buffer_refs=0 result=0\n",pin_live[slot].owner,pin_live[slot].command,pin_live[slot].serial,live[slot].serial,pin_live[slot].sender,syscall(178),a>=0?pins.pins[a].state:255,pins.connections);memset(pin_live+slot,0,sizeof pin_live[slot]);}

int osal_snd_msg(unsigned int dst,void *request){
 int saved=*__errno_location(),rc;enter();initialize();leave();
 profile_stack(dst,request,__builtin_frame_address(0));
 boot_tail_observe(dst,request,__builtin_frame_address(0),4);
 if(dst==0x5503e0&&request){unsigned int n=msg_size(request);if(n<=128){char raw[257];const char *digits="0123456789abcdef";for(unsigned int i=0;i<n;i++){unsigned char c=((unsigned char *)request)[i];raw[2*i]=digits[c>>4];raw[2*i+1]=digits[c&15];}raw[n*2]=0;struct cap_dl_info ci={0};dladdr(__builtin_return_address(0),&ci);dprintf(2,"FX3_BOOT_QUEUE_SEND tid=%ld bytes=%u source=%#x raw=%s caller_relative=%#lx passive=1 completion_not_assumed=1\n",syscall(178),n,source(request),raw,ci.base?(unsigned long)__builtin_return_address(0)-(unsigned long)ci.base:0);}}

 /* Validate original caller at the outermost interposer, outside model/loader locks.
  * Nested interposers may cease to tail-call after adding instrumentation. */
 if(dst==0x912503d0&&request&&msg_size(request)==8){
  unsigned int command;memcpy(&command,request,4);const char *p=getenv("FX3_CP_VERSION_TRANSPORT");
  struct cap_dl_info info={0};void *caller=__builtin_return_address(0);
  if(command==4&&p&&!strcmp(p,"unavailable-v1")&&dladdr(caller,&info)&&info.base&&(unsigned long)caller-(unsigned long)info.base==0x1984&&info.file&&(!strcmp(info.file,"/usr/lib/libupdaterufp.so")||!strcmp(info.file,"libupdaterufp.so"))){
   dprintf(2,"FX3_CP_VERSION_UNAVAILABLE command=4 bytes=8 source=%#x caller=%p caller_owned=1 reply_added=0 result=-1021 outermost_validated=1\n",source(request),caller);*__errno_location()=saved;return -1021;
  }
 }
 const char *pin_profile=getenv("FX3_PIN_GRAPH");
 if(enabled&&request&&pin_profile&&!strcmp(pin_profile,"empty-owned-mode1-v1")&&pg_owner(dst)&&msg_size(request)>=32){unsigned int type=pg_get((unsigned char *)request+24)&65535;if(type==0x1000&&pg_get((unsigned char *)request+4)==0xa0a0a0a0U){enter();int out=pin_dispatch(dst,request);leave();*__errno_location()=saved;return out;}}
 const char *tail_profile=getenv("FX3_BOOT_TAIL");
 if(enabled&&request&&tail_profile&&!strcmp(tail_profile,"audited-panel-hdmi-v1")&&msg_size(request)>=4){unsigned int header;memcpy(&header,request,4);if((dst==0x92840747&&header==0x0165200d)||(dst==0x909a015a&&(header==0x010a2500||header==0x01012500||header==0x01172500))){unsigned int command=header>>16;enter();int out=tail_dispatch(dst,request,command);leave();*__errno_location()=saved;return out;}}
 const char *boot_profile=getenv("FX3_BOOT_REPLY");
 if(enabled&&boot_profile&&!strcmp(boot_profile,"timecode-getfunc-muted-v1")&&request){
  if(dst==0x9059000e){unsigned int mask=tc_stack_mask(__builtin_frame_address(0));enter();int out=timecode_dispatch(request,mask);leave();*__errno_location()=saved;return out;}
  if(dst==0x92840747&&msg_size(request)>=4){unsigned int head;memcpy(&head,request,4);if(head==0x0325200d){enter();int out=get_func_dispatch(request);leave();*__errno_location()=saved;return out;}}
 }
 enter();
 const char *observe=getenv("FX3_VDF_OBSERVE");
 if((dst==0x02820746||dst==0x0061003c||dst==0x92840747||dst==0x909a015a||dst==0x9061003c||dst==0x909c015b||dst==0x92b4086f||dst==0x90040193)&&request&&observe&&!strcmp(observe,"1")){
  static unsigned int count;unsigned int n=msg_size(request);if(count++<256&&n<=1024){
   const unsigned char *p=request;char hex[2049];const char digits[]="0123456789abcdef";for(unsigned int i=0;i<n;i++){hex[2*i]=digits[p[i]>>4];hex[2*i+1]=digits[p[i]&15];}hex[2*n]=0;
   struct cap_dl_info where={0};dladdr(__builtin_return_address(0),&where);dprintf(2,"FX3_PROVIDER_CALLER module=%s relative=%#lx\n",where.file?where.file:"?",where.base?(unsigned long)__builtin_return_address(0)-(unsigned long)where.base:0);
   dprintf(2,"FX3_PROVIDER_REQUEST destination=%#x bytes=%u source=%#x caller=%p raw=%s dispatch_pending=1\n",dst,n,source(request),__builtin_return_address(0),hex);
  }
 }
 const char *cec_profile=getenv("FX3_CEC_POWER");
 if(enabled&&dst==0x909c015b&&request&&cec_profile&&!strcmp(cec_profile,"software-disconnected-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x01010000){int rc=cec_power_dispatch(request);leave();*__errno_location()=saved;return rc;}}
 const char *tc_profile=getenv("FX3_HDMI_TC");
 if(enabled&&dst==0x909a015a&&request&&tc_profile&&!strcmp(tc_profile,"inactive-disabled-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x01092500){int rc=hdmi_tc_dispatch(request);leave();*__errno_location()=saved;return rc;}}
 const char *lut_profile=getenv("FX3_MONITOR_LUT");
 if(enabled&&dst==0x92840747&&request&&lut_profile&&!strcmp(lut_profile,"inactive-identity-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x0161200d){int rc=monitor_lut_dispatch(request);leave();*__errno_location()=saved;return rc;}}
 const char *release_profile=getenv("FX3_RELEASE_INHIBIT");
 if(enabled&&dst==0x90040193&&request&&release_profile&&!strcmp(release_profile,"idle-only-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x403d0005){int rc=release_inhibit_dispatch(request);leave();*__errno_location()=saved;return rc;}}
 const char *lcd_profile=getenv("FX3_LCD_OSD");
 if(enabled&&dst==0x92840747&&request&&lcd_profile&&!strcmp(lcd_profile,"captured-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x011a200d||h==0x0159200d){int rc=h==0x011a200d?lcd_dispatch(request):osd_dispatch(request);leave();*__errno_location()=saved;return rc;}}
 const char *muted_profile=getenv("FX3_ADF_MUTED");
 if(enabled&&dst==0x92840747&&request&&muted_profile&&!strcmp(muted_profile,"silent-storage-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x0327200d||h==0x032a200d){int rc=beep_dispatch(request,h>>16);leave();*__errno_location()=saved;return rc;}if(h==0x032e200d||h==0x033d200d){int rc=muted_dispatch(request,h>>16);leave();*__errno_location()=saved;return rc;}}
 const char *audio_profile=getenv("FX3_HDMI_AUDIO");
 if(enabled&&dst==0x92840747&&request&&audio_profile&&!strcmp(audio_profile,"inactive-format-v1")&&msg_size(request)>=4){
  unsigned int header;memcpy(&header,request,4);if(header==0x032d200d){int rc=audio_dispatch(request);leave();*__errno_location()=saved;return rc;}
 }
 const char *photo_profile=getenv("FX3_HDMI_PHOTO");
 if(enabled&&dst==0x909a015a&&request&&photo_profile&&!strcmp(photo_profile,"inactive-preset-v1")&&msg_size(request)>=4){
  unsigned int header;memcpy(&header,request,4);if(header==0x01022500){int rc=photo_dispatch(request);leave();*__errno_location()=saved;return rc;}
 }
 const char *file_profile=getenv("FX3_ADF_FILE");
 if(enabled&&file_profile&&!strcmp(file_profile,"muted-user-v1")&&request){
  /* The audited ICDT entry is osal_snd_sync_msg, not asynchronous send. */
  if(dst==0x9061003c&&msg_size(request)==40){unsigned int op=ff_get(request,2),h=ff_get((unsigned char *)request+8,4);if((op==0x20&&ff_get((unsigned char *)request+4,4)==0x70817)||(op!=0x20&&(h&0x8000)&&(h&1023)>=2&&(h&1023)<=7)){int rc=ff_dispatch(request);leave();*__errno_location()=saved;return rc;}}
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
 if(found<0&&pin_duplicate_free(dst,p)){leave();*__errno_location()=saved;return -1021;}
 if(found<0){unsigned char captured[40];int capture=0;const char *fp=getenv("FX3_ADF_FILE");if(p&&fp&&!strcmp(fp,"muted-user-v1")&&msg_size(p)==40){memcpy(captured,p,40);capture=1;}leave();*__errno_location()=saved;int rc=release(dst,p);int after=*__errno_location();if(!rc&&capture){enter();ff_capture_local(captured);leave();}*__errno_location()=after;return rc;}
 unsigned char pin_fingerprint[56];int is_pin=pin_live[found].request!=0;if(is_pin&&(!pin_can_retire(found)||live[found].dst!=dst)){leave();*__errno_location()=saved;return -1021;}if(is_pin)memcpy(pin_fingerprint,p,56);
 int rc=live[found].dst==dst?release(dst,p):-1021;
 dprintf(2,"FX3_CAPID_NATIVE_FREE destination=%#x command=%#x lease=%lu result=%d\n",dst,live[found].command,live[found].serial,rc);
 if(rc)fault=1;else {if(is_pin)pin_retire(found,p,pin_fingerprint);if(tail_live[found].request){dprintf(2,"FX3_BOOT_TAIL_CONSUMED destination=%#x command=%#x kind=%u lease=%lu result=0\n",dst,live[found].command,tail_live[found].kind,live[found].serial);memset(tail_live+found,0,sizeof tail_live[found]);}if(gf_live_request[found]){dprintf(2,"FX3_ADF_GET_FUNC_CONSUMED destination=%#x lease=%lu result=0\n",dst,live[found].serial);gf_live_request[found]=0;}if(tc_live_request[found]){dprintf(2,"FX3_TIMECODE_REPLY_CONSUMED destination=%#x lease=%lu padding=%08x result=0 request_key=%p\n",dst,live[found].serial,tc_live_padding[found],tc_live_request[found]);tc_live_request[found]=0;tc_live_padding[found]=0;}if(ff_pending[found]){file_model.slots[ff_pending[found]-1].pending=0;dprintf(2,"FX3_ICDT_COMPLETION_CONSUMED slot=%u native_callback_precedes_free=1 result=0\n",ff_pending[found]-1);ff_pending[found]=0;}memset(&live[found],0,sizeof live[found]);}leave();*__errno_location()=saved;return rc;
}

int osal_snd_sync_msg(unsigned int dst,void *request){
 int saved=*__errno_location();enter();initialize();leave();boot_tail_observe(dst,request,__builtin_frame_address(0),5);const char *profile=getenv("FX3_ADF_FILE");
 if(enabled&&dst==0x02820746&&profile&&!strcmp(profile,"muted-user-v1")){
  profile_stack(dst,request,__builtin_frame_address(0));unsigned int n=request?msg_size(request):0;
  if(request&&n==48){const unsigned char *p=request;char raw[97];const char *hex="0123456789abcdef";for(unsigned int i=0;i<48;i++){raw[2*i]=hex[p[i]>>4];raw[2*i+1]=hex[p[i]&15];}raw[96]=0;dprintf(2,"FX3_ICDT_SYNC_CAPTURE tid=%ld destination=%#x bytes=48 raw=%s kernel_sync_delegated=0\n",syscall(178),dst,raw);}
  enter();int rc=ff_icdt(request);leave();*__errno_location()=saved;return rc;
 }
 int (*fn)(unsigned int,void *)=dlsym((void *)-1,"osal_snd_sync_msg");if(!fn)_exit(126);*__errno_location()=saved;return fn(dst,request);
}
