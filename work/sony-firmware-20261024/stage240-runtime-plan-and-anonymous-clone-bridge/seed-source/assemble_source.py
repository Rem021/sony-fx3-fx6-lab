"""Compose reviewed OWN receiver/collector pieces, no original-code execution."""
from pathlib import Path
from hashlib import sha256
import json
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage239-parent-SCM-anchor-receiver'
inputs={n:(P/n).read_text() for n in ['parent_receiver.c','collector-ack.c']}
pins={'parent_receiver.c':'82d224b92f4f19ac02f8d421fb7751fadd8a8afc6f925c8da17413b07e3f6771','collector-ack.c':'62bc2f808a181c0a134257ebc8264c553c6ec387c356850db2f0fc2e518dc24e'}
for n,s in inputs.items():assert sha256(s.encode()).hexdigest()==pins[n]
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
parent=inputs['parent_receiver.c'];parent='#include "bridge_job.h"\nstatic struct bridge_job parent_job;\nstatic int *restore_result;\nstatic int release_mask(void);\n'+parent
parent=replace(parent,'if(status!=SENTINEL_STATUS)break;saw=1;','if(status!=SENTINEL_STATUS)break;saw=1;if(!release_mask())break;')
a=parent.index('static void expected(');z=parent.index('static int channel_profile(',a)
parent=parent[:a]+'''static void expected(u8 *p,u32 type,u32 child){bj_packet(p,&parent_job,child,0,type);}
static int release_mask(void){
 if(*restore_result)return *restore_result>0;
 *restore_result=-1;if(sc(135,2,(long)&parent_job.old_mask,0,8,0,0))return 0;
 *restore_result=1;return 1;
}
'''+parent[z:]
for start in ['static void p32(', 'static void p64(', 'static u32 crc(']:
 a=parent.index(start);z=parent.index('\n',a);parent=parent[:a]+parent[z+1:]
parent=replace(parent,'__attribute__((visibility("default"))) int fx3_parent_receiver(long channel,u32 child){','__attribute__((visibility("hidden"))) int fx3_parent_receiver(long channel,u32 child,const struct bridge_job *job,int *handoff){\n bj_copy(&parent_job,job,sizeof(parent_job));restore_result=handoff;handoff[0]=handoff[1]=0;')
parent=replace(parent,'receiver_state=HELD;u64 deadline=3000000000ULL;if(begun<1000000000ULL||begun>=deadline)goto end;expected(hello,3,child);int got=0;','receiver_state=HELD;handoff[1]=1;u64 deadline=parent_job.expires;if((u64)self!=parent_job.parent_pid||begun<parent_job.issued||begun>=deadline)goto end;begun=parent_job.issued;expected(hello,3,child);int got=0;')
collector='#include "bridge_job.h"\nstatic struct bridge_job collector_job;\n'+inputs['collector-ack.c']
collector=replace(collector,'static const u8 magic[16]="FX3ISOCOLLECT2";\n','')
a=collector.index('static void packet(');z=collector.index('static int send1(',a)
collector=collector[:a]+'''static void packet(u8 *p,u32 type,long self,long worker){bj_packet(p,&collector_job,(u32)self,(u32)worker,type);}
'''+collector[z:]
for start in ['static void p64(', 'static u32 crc(']:
 a=collector.index(start);z=collector.index('\n',a);collector=collector[:a]+collector[z+1:]
collector=collector.replace('!=321','!=(long)collector_job.parent_pid').replace('status_guard(self,321)','status_guard(self,(long)collector_job.parent_pid)')
collector=collector.replace('3000000000ULL','collector_job.expires').replace('1000000000ULL','collector_job.issued')
collector=replace(collector,'__attribute__((visibility("default"))) int fx3_isolated_collector_core(void){','__attribute__((visibility("hidden"))) int fx3_isolated_collector_core(long incoming,const struct bridge_job *job){\n bj_copy(&collector_job,job,sizeof(collector_job));')
collector=replace(collector,'long channel=53,anchor=','long channel=incoming,anchor=')
collector=replace(collector,'recv1(channel,321,hello)','recv1(channel,(long)collector_job.parent_pid,hello)')
out={'parent.c':parent,'collector.c':collector}
for n,s in out.items():(H/n).open('x').write(s)
(H/'source-assembly.json').open('x').write(json.dumps(dict(inputs={n:dict(path=str((P/n).relative_to(R)),sha256=pins[n]) for n in pins},outputs={n:sha256(s.encode()).hexdigest() for n,s in out.items()},own_sources_only=True,changes=['runtime job and packetv3','runtime caller/FD/expiry','parent restores saved mask only after exact sentinel','explicit channel handoff ownership']),indent=2)+'\n')
print('assembled parent and collector from pinned OWN sources')
