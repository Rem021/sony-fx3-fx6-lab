from pathlib import Path
import json,hashlib,re
R=Path(__file__).resolve().parent;H=R/'helpers';S=R.parent/'success-cases/display-reuse/supplemental-source/runtime/analysis';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
h=(S/'dmm-service.h').read_text().replace('0x41e000000ULL','0x41d900000ULL');(H/'fx3-dmm-model.h').write_text(h)
s=(S/'dmm-service.c').read_text().replace('#include "dmm-service.h"','#include "fx3-dmm-model.h"')
a=s.index('unsigned int dmm_speech_initial_creator(');b=s.index('static unsigned int get(',a)
s=s[:a]+'''/* FX3 creator provenance unknown: never use A7C2 ELF frame offsets. */
unsigned int dmm_speech_initial_creator(const unsigned long *pcs,unsigned int n){(void)pcs;(void)n;return DMM_CREATOR_UNKNOWN;}
'''+s[b:];s=s[:s.index('#ifdef DMM_SERVICE_SELFTEST')];(H/'fx3-dmm-model.c').write_text(s)
s=(H/'fx3-capid-v8.c').read_text();pos=s.index('int osal_snd_msg(')
frag='''#include "fx3-dmm-model.c"
static struct dmm_service remote_dmm;
static int dmm_bind(void){
 if(remote_dmm.memory)return 0;
 int fd=open("/tmp/fx3-dmm.claim",0x200c1,0600);if(fd<0)return -1021;
 dprintf(fd,"pid=%ld physical=41d900000 bytes=100000\\n",process_owner);close(fd);
 char cmd[4096]={0};fd=open("/proc/cmdline",0);long n=fd<0?-1:read(fd,cmd,sizeof cmd-1);if(fd>=0)close(fd);
 if(n<=0||!strstr(cmd,"memrsv=0x00100000@0x41d900000:uc")){fault=1;return -1021;}
 fd=open("/dev/mem",2);void *p=fd<0?(void *)-1:mmap(0,DMM_TEST_SIZE,3,1,fd,DMM_TEST_PHYSICAL);if(fd>=0)close(fd);
 if(p==(void *)-1){fault=1;return -1021;}
 remote_dmm.memory=p;remote_dmm.physical=DMM_TEST_PHYSICAL;
 volatile unsigned int *probe=(volatile unsigned int *)((unsigned char *)p+DMM_TEST_SIZE-16);
 *probe=0x44534d4d;unsigned int readback=*probe;*probe=0;
 if(readback!=0x44534d4d){fault=1;return -1021;}
 dprintf(2,"FX3_REMOTE_DMM_BIND physical=%#llx bytes=%#x readback=%#x original_CP=0\\n",remote_dmm.physical,DMM_TEST_SIZE,readback);return 0;
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
 dprintf(2,"FX3_REMOTE_DMM_COMMIT op=%#x source=%#x status=%d handle=%#x address=%#llx bytes=%#x slots=%d/%d opens=%u/%u allocations=%llu lease=%lu request_free=%d virtual_storage=1 original_CP=0\\n",op,from,status,handle,address,length,remote_dmm.slots[0].allocated,remote_dmm.slots[1].allocated,remote_dmm.slots[0].open_count,remote_dmm.slots[1].open_count,remote_dmm.allocations,live[slot].serial,freed);return 0;
}
'''
s=s[:pos]+frag+s[pos:];pos=s.index(' const char *sa=getenv(');s=s[:pos]+''' const char *dmm_profile=getenv("FX3_REMOTE_DMM");
 if(enabled&&dst==0x9061003c&&request&&dmm_profile&&!strcmp(dmm_profile,"two-slot-storage-v1")){int rc=dmm_dispatch(request);leave();*__errno_location()=saved;return rc;}
'''+s[pos:];(H/'fx3-capid-v9.c').write_text(s)
(H/'fx3-dmm-source-derivation.json').write_text(json.dumps({'upstream_commit':'b3d7c1fed349f1d918acc4259f1d2b3a7c52a500','input_sha256':{n:sha(S/n) for n in ['dmm-service.c','dmm-service.h']},'output_sha256':{n:sha(H/n) for n in ['fx3-dmm-model.c','fx3-dmm-model.h','fx3-capid-v9.c']},'changes':['Privatevirtual1MiB reserve41d900000 replacesA7C2 testphysical','Creatorclassifier returnsunknown; allA7C2 privatePCs removed','Hostselftest replacedbyFX3 transport/storage failure tests','No originalCP orcaptureproducer; independentvirtualstorageonly']},indent=2)+'\n')
