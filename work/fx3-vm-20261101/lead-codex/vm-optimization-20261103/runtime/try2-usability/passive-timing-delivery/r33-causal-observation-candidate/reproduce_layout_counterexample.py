#!/usr/bin/env python3
"""Host-only audit of exact extracted baseline predicates, NOT a guest candidate.
No runner imports, VM, browser, service, QMP, device or actual mmap/pread calls.
Native open, process memory, physical mmap and screen state below are MOCKS.
"""
from pathlib import Path
import json,hashlib,subprocess,os,re
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if p.name=='Mac')
G=ROOT/'work/fx3-vm-20261101/lead-claude/impl/gpe-perf'
UI=HERE.parent/'v25-r15-snapshot-tail/fx3-ui-gate-v15.c'
def function(p,name):
 s=p.read_text();m=re.search(r'^static [^\n]*\b'+name+r'\(',s,re.M);assert m,name
 start=m.start();a=s.index('{',m.start());depth=1;i=a+1;quote=None;escape=False
 while depth:
  c=s[i]
  if quote:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c==quote:quote=None
  elif c in ('"',"'"):quote=c
  elif c=='{':depth+=1
  elif c=='}':depth-=1
  i+=1
 text=s[start:i]
 return text,dict(path=str(p),function=name,start_line=s.count('\n',0,start)+1,end_line=s.count('\n',0,i)+1,sha256=hashlib.sha256(text.encode()).hexdigest())
def main():
 fixtures=HERE/'host-fixture';fixtures.mkdir(exist_ok=True)
 pre=r'''
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
'''
 names=['object_fields','resource_same','resource_retire','resource_add','observe_resource_open','resource_lookup']
 parts=[];bindings=[]
 for n in names:
  text,b=function(G/'resource-v26.inc',n);parts.append(text);bindings.append(b)
 for p,n in [(G/'cache-v26.inc','map26_get'),(UI,'bind_ram')]:
  text,b=function(p,n);parts.append(text);bindings.append(b)
 post=r'''
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
'''
 src=fixtures/'baseline-local-predicates.c';src.write_text(pre+'\n\n'.join(parts)+post)
 (HERE/'EXTRACTED-FUNCTIONS.json').write_text(json.dumps(bindings,indent=2)+'\n')
 exe=fixtures/'baseline-local-predicates';cmd=['/usr/bin/xcrun','clang','-std=c11','-O0','-Wall','-Wextra',str(src),'-o',str(exe)]
 env=os.environ.copy();env['TMPDIR']=str(fixtures)
 comp=subprocess.run(cmd,capture_output=True,env=env);(fixtures/'compile.stdout').write_bytes(comp.stdout);(fixtures/'compile.stderr').write_bytes(comp.stderr)
 result={'scope':'HOST FIXTURE ONLY; exact extracted baseline functions; MOCK native open, memory and mmap; no runtime candidate','compiler_argv':cmd,'compile_exit':comp.returncode,'compiler_stderr':comp.stderr.decode(errors='replace'),'cases':[]}
 if comp.returncode==0:
  run=subprocess.run([str(exe)],capture_output=True,env=env);(fixtures/'run.stdout').write_bytes(run.stdout);(fixtures/'run.stderr').write_bytes(run.stderr);result['run_exit']=run.returncode
  result['cases']=[json.loads(l) for l in run.stdout.splitlines()];result['passed_cases']=sum(x.get('passed',False) for x in result['cases']);result['run_stderr']=run.stderr.decode(errors='replace')
 (HERE/'HOST-AUDIT-RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert comp.returncode==0 and result['run_exit']==0
if __name__=='__main__':main()
