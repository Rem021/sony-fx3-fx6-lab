
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
typedef unsigned long U;typedef unsigned int W;
_Static_assert(sizeof(U)==8,"fixture requires LP64");
#define UI_BASE 0x41dc00000UL
#define EXT_BASE 0x430400000UL
#define EXT_BYTES 0xcfc00000UL
#define RESOURCE_LIMIT 512
#define MAP26_LIMIT 64
struct resource_record {U object,identity,type,logical,phys,bytes,epoch,vptr;unsigned uhdl,active,native_open;};
struct map26_record {U object,epoch,base,bytes,map_bytes;void*area;unsigned prot,active;};
struct screen_identity {U unused;};
static struct resource_record resources[RESOURCE_LIMIT];
static struct map26_record maps26[MAP26_LIMIT];
static U resource_epoch,resource_class_vptr=0xabc000,screen_anchor_object,screen_anchor_epoch;
static U map26_hits,map26_misses,map26_fallbacks;
static int process_mem=3,physical=4,mock_errno,native_calls,native_rc,life_in,life_out;
static unsigned char object[0x70],physical_mock[0x10000];
static U mapped_offset,mapped_bytes;static int mapped_prot,map_calls,map_fail,ui_mode,ui_fail,close_calls;
static volatile U *ram;
static U load64(const unsigned char*p){U x;memcpy(&x,p,8);return x;}
static W load32(const unsigned char*p){W x;memcpy(&x,p,4);return x;}
static void put64(unsigned n,U x){memcpy(object+n,&x,8);}
static void put32(unsigned n,W x){memcpy(object+n,&x,4);}
static int *fixture_errno(void){return &mock_errno;}
#define __errno_location fixture_errno
static int fixture_dprintf(int fd,const char*fmt,...){(void)fd;(void)fmt;return 0;}
#define dprintf fixture_dprintf
static long fixture_pread(int fd,void*out,unsigned long n,long at){(void)fd;assert((U)at==(U)object&&n==sizeof object);memcpy(out,object,n);return (long)n;}
#define pread fixture_pread
static void *fixture_mmap(void*a,unsigned long n,int prot,int flags,int fd,long offset){(void)a;(void)fd;assert(flags==1);map_calls++;mapped_offset=(U)offset;mapped_bytes=n;mapped_prot=prot;if(map_fail||(ui_mode&&ui_fail==4))return(void*)-1;assert(n<=sizeof physical_mock);return physical_mock;}
#define mmap fixture_mmap
static int fixture_open(const char*p,int flags,...){(void)flags;if(strstr(p,"claim"))return ui_fail==1?-1:1;if(!strcmp(p,"/proc/cmdline"))return 2;if(!strcmp(p,"/dev/mem"))return ui_fail==3?-1:3;assert(0);return -1;}
#define open fixture_open
static long fixture_read(int fd,void*out,unsigned long n){(void)fd;const char*s=ui_fail==2?"missing":"memrsv=0x00010000@0x41dc00000:uc";unsigned long z=strlen(s);assert(z<n);memcpy(out,s,z);return (long)z;}
#define read fixture_read
static int fixture_close(int fd){(void)fd;close_calls++;return 0;}
#define close fixture_close
static long fixture_syscall(long n,...){assert(n==172);return 241;}
#define syscall fixture_syscall
static void life_enter(void){life_in++;}static void life_leave(void){life_out++;}
static void map26_retire(U o){(void)o;}static void child_retire(U a,U b,const char*c){(void)a;(void)b;(void)c;}
static int screen_proc_live(struct screen_identity*s){(void)s;return 1;}
static int mock_native(void*o,const void*c){(void)o;(void)c;native_calls++;mock_errno=91;return native_rc;}
static int(*native_resource_open)(void*,const void*)=mock_native;
static int object_fields(void *o,struct resource_record *r){
 unsigned char b[0x70];if(process_mem<0||!o||pread(process_mem,b,sizeof(b),(long)o)!=(long)sizeof(b))return 0;
 if(load32(b+0x20)!=0x10)return 0;
 r->object=(U)o;r->vptr=load64(b);r->identity=load64(b+0x10);r->type=load64(b+0x38);r->uhdl=load32(b+0x40);
 r->logical=load64(b+0x58);r->phys=load64(b+0x60);r->bytes=load64(b+0x68);
 return r->identity&&r->uhdl&&r->logical&&r->phys&&r->bytes&&r->bytes<=0x10000000UL&&r->bytes<=~0UL-r->phys&&r->bytes<=~0UL-r->logical;
}

static int resource_same(const struct resource_record*a,const struct resource_record*b){
 return a->object==b->object&&a->vptr==b->vptr&&a->identity==b->identity&&a->type==b->type&&a->uhdl==b->uhdl&&a->logical==b->logical&&a->phys==b->phys&&a->bytes==b->bytes;
}

static void resource_retire(void *o,const char *event){
 map26_retire((U)o);
 for(unsigned i=0;i<RESOURCE_LIMIT;i++)if(resources[i].active&&resources[i].object==(U)o){
  child_retire((U)o,0,event);resources[i].active=0;dprintf(2,"FX3_GPE_RESOURCE_RETIRE object=%p uhdl=%#x epoch=%lu event=%s before_native_release=1\n",o,resources[i].uhdl,resources[i].epoch,event);
 }
}

static void resource_add(void *o,const char *origin){
 struct resource_record r={0};if(!object_fields(o,&r)){dprintf(2,"FX3_GPE_RESOURCE_REJECT event=open object=%p reason=fields_or_state10 no_address_allowlist=1\n",o);return;}
 resource_retire(o,"object_reopen");unsigned slot=RESOURCE_LIMIT;
 for(unsigned i=0;i<RESOURCE_LIMIT;i++)if(!resources[i].active){slot=i;break;}
 if(slot==RESOURCE_LIMIT||resource_epoch==~0UL){dprintf(2,"FX3_GPE_RESOURCE_REJECT event=open reason=capacity_or_epoch\n");return;}
 r.epoch=++resource_epoch;r.active=1;r.native_open=!strcmp(origin,"native_open_return_v1");resources[slot]=r;
 if(r.native_open&&r.type==0x403&&r.uhdl==0x402&&r.phys==EXT_BASE&&r.bytes==EXT_BYTES&&r.vptr==resource_class_vptr){screen_anchor_object=r.object;screen_anchor_epoch=r.epoch;struct screen_identity auxiliary26={0};(void)screen_proc_live(&auxiliary26);dprintf(2,"FX3_GPE_SCREEN_AUTHORITY_BOUND object=%#lx epoch=%lu identity=%#lx token=%#x native_open_type403=1 original_state10=1 authority=native_object_fields_and_epoch proc_auxiliary=1\n",r.object,r.epoch,r.identity,r.uhdl);}

 dprintf(2,"FX3_GPE_RESOURCE_REGISTER object=%p identity=%#lx type=%#lx uhdl=%#x logical=%#lx phys=%#lx bytes=%#lx epoch=%lu original_success_status=0 state=0x10 scope=allocation_interval subblock_lifetime_unproven=1 queued_ABA_uncovered=1 vptr=%#lx registration_origin=%s\n",o,r.identity,r.type,r.uhdl,r.logical,r.phys,r.bytes,r.epoch,r.vptr,origin);
}

static int observe_resource_open(void *o,const void *cfg){
 int before=*__errno_location();*__errno_location()=before;int rc=native_resource_open(o,cfg);int after=*__errno_location();
 life_enter();resource_retire(o,"open_or_replace_attempt");if(!rc)resource_add(o,"native_open_return_v1");life_leave();
 *__errno_location()=after;return rc;
}

static int resource_lookup(U address,U step,U line,unsigned rows,struct resource_record *out){
 unsigned count=0;struct resource_record selected={0};
 if(!rows||!line)return 0;
 for(unsigned i=0;i<RESOURCE_LIMIT;i++)if(resources[i].active){
  struct resource_record *r=&resources[i];int valid=1;
  for(unsigned y=0;y<rows;y++){U a=address+(U)y*step;if(a<address||a<r->phys||a-r->phys>r->bytes||line>r->bytes-(a-r->phys)){valid=0;break;}}
  if(!valid)continue;struct resource_record now={0};
  if(!object_fields((void*)r->object,&now)||!resource_same(r,&now)){map26_retire(r->object);child_retire(r->object,0,"parent_identity_changed");r->active=0;continue;}
  selected=*r;count++;
 }
 if(count!=1)return 0;*out=selected;return 1;
}

static void *map26_get(U object,U epoch,U base,U bytes,unsigned prot,unsigned*cached,U*out_page,U*out_bytes){
 U page=base&~4095UL,leading=base-page;*cached=0;
 if(!bytes||bytes>~0UL-leading-4095UL)return(void*)-1;
 U n=(leading+bytes+4095UL)&~4095UL;*out_page=page;*out_bytes=n;
 for(unsigned i=0;i<MAP26_LIMIT;i++){struct map26_record*r=&maps26[i];if(r->active&&r->object==object&&object&&r->epoch==epoch&&r->base==base&&r->bytes==bytes&&(r->prot&prot)==prot){*cached=1;map26_hits++;return r->area;}}
 map26_misses++;void*area=mmap(0,n,(int)prot,1,physical,(long)page);if(area==(void*)-1)return area;
 unsigned slot=MAP26_LIMIT;for(unsigned i=0;i<MAP26_LIMIT;i++)if(!maps26[i].active){slot=i;break;}
 if(!object||!epoch||slot==MAP26_LIMIT){map26_fallbacks++;return area;}
 maps26[slot]=(struct map26_record){object,epoch,base,bytes,n,area,prot,1};*cached=1;return area;
}

static int bind_ram(void){int fd=open("/tmp/fx3-ui-gate.claim",0x200c1,0600);if(fd<0)return -1;dprintf(fd,"pid=%ld physical=41dc00000 bytes=10000 observer=1\n",syscall(172));close(fd);char cmd[4096]={0};fd=open("/proc/cmdline",0);long n=fd<0?-1:read(fd,cmd,4095);if(fd>=0)close(fd);if(n<=0||!strstr(cmd,"memrsv=0x00010000@0x41dc00000:uc"))return -2;fd=open("/dev/mem",2);void *p=fd<0?(void *)-1:mmap(0,0x10000,3,1,fd,0x41dc00000UL);if(fd>=0)close(fd);if(p==(void *)-1)return -3;memset(p,0,0x10000);ram=p;ram[0]=0x3145544147335846UL;ram[1]=2;ram[4]=syscall(172);return 0;}
static void fresh(void){memset(resources,0,sizeof resources);memset(maps26,0,sizeof maps26);memset(object,0,sizeof object);resource_epoch=0;native_calls=0;native_rc=0;life_in=life_out=0;mock_errno=37;map_calls=0;map_fail=0;ui_mode=0;ui_fail=0;ram=0;put64(0,resource_class_vptr);put64(0x10,0x123);put32(0x20,0x10);put64(0x38,0x403);put32(0x40,0x403);put64(0x58,0x7f00000000UL);put64(0x60,UI_BASE);put64(0x68,0x10000);}
static void pass(const char*n){printf("{\"case\":\"%s\",\"passed\":true}\n",n);}
int main(void){struct resource_record r={0};unsigned cached;U page,bytes;int rc;
 fresh();rc=observe_resource_open(object,0);assert(rc==0&&native_calls==1&&mock_errno==91&&life_in==1&&life_out==1);assert(resources[0].native_open&&resources[0].type==0x403&&resources[0].vptr==resource_class_vptr);assert(resource_lookup(UI_BASE+0x7000,0x800,0x800,1,&r));assert(map26_get(r.object,r.epoch,r.phys,r.bytes,3,&cached,&page,&bytes)==physical_mock);assert(map_calls==1&&mapped_prot==3&&mapped_offset==UI_BASE&&mapped_bytes==0x10000);pass("synthetic_native_open_ui_resource_accepts_gap_and_maps_full_reserve");
 printf("{\"counterexample\":{\"MOCK_native_open_rc\":0,\"MOCK_screen_assumed_live\":true,\"native_calls\":%d,\"physical\":\"%#lx\",\"mapped_bytes\":%lu,\"prot\":%d,\"actual_firmware_reachability\":\"UNPROVEN\",\"actual_physical_write\":false}}\n",native_calls,mapped_offset,mapped_bytes,mapped_prot);
 fresh();native_rc=-7;assert(observe_resource_open(object,0)==-7&&native_calls==1&&mock_errno==91&&!resources[0].active);pass("native_error_rc_once_preserved");
 fresh();put32(0x20,0);observe_resource_open(object,0);assert(!resources[0].active);pass("wrong_native_state_rejected");
 fresh();put64(0x10,0);observe_resource_open(object,0);assert(!resources[0].active);pass("missing_identity_rejected");
 fresh();put64(0x60,~0UL-0x100);observe_resource_open(object,0);assert(!resources[0].active);pass("physical_overflow_rejected");
 fresh();observe_resource_open(object,0);assert(!resource_lookup(UI_BASE+0x10000,4,4,1,&r));pass("outside_resource_rejected");
 fresh();observe_resource_open(object,0);put64(0x10,0x456);assert(!resource_lookup(UI_BASE+0x7000,4,4,1,&r));assert(!resources[0].active);pass("changed_identity_invalidates_lookup");
 fresh();observe_resource_open(object,0);resources[1]=resources[0];assert(!resource_lookup(UI_BASE+0x7000,4,4,1,&r));pass("ambiguous_multiple_resources_rejected");
 fresh();put64(0x60,UI_BASE+0x7000);put64(0x68,0x800);observe_resource_open(object,0);assert(resource_lookup(UI_BASE+0x7000,0x800,0x800,1,&r));assert(map26_get(r.object,r.epoch,r.phys,r.bytes,3,&cached,&page,&bytes)==physical_mock);assert(mapped_offset==UI_BASE+0x7000&&mapped_bytes==0x1000);pass("synthetic_gap_only_parent_rounds_to_4KiB_page");
 fresh();for(int failure=1;failure<=4;failure++){ui_mode=1;ui_fail=failure;int result=bind_ram();assert(result==(failure<=2?-failure:-3));assert(!ram);}pass("baseline_ui_bind_claim_cmdline_open_mmap_failures");
 fresh();ui_mode=1;memset(physical_mock,0xa5,sizeof physical_mock);assert(!bind_ram());for(unsigned i=0x7000;i<0x7800;i++)assert(!physical_mock[i]);assert(ram==(U*)physical_mock&&ram[0]==0x3145544147335846UL&&ram[1]==2&&ram[4]==241);pass("actual_ui_bind_erases_early_gap_witness_then_sets_pid_header");
 return 0;
}
