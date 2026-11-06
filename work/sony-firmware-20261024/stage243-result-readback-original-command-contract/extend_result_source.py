"""Extend our own front end with a fixed RAM local-observation record."""
from pathlib import Path
from hashlib import sha256
import json
H=Path(__file__).resolve().parent
s=(H/'front.before-result.c').read_text()
start=s.index('/* Zero explicit arguments:')
head=s[:start]
tail=r'''
/* This record claims ONLY the core's local return. It is constructed before
 * its own write/close/final-clock operations, so cannot certify those later
 * operations, Sony setter return, USB return or global resource completion. */
static int publish_local(const u8 plan[256],u32 core_state,u32 core_reason){
 long root=-1,owner=-1;struct kstat st;u8 report[256];u64 finished=0,last=0;int ok=0;
 if(!tick(&finished)||finished<get64(plan+144))return 0;
 if(core_state==11&&finished>=get64(plan+152)){core_state=2;core_reason=201;}
 zero(report,256);copy(report,(const u8 *)"FX3LOCALRESULT1",15);
 put32(report+16,1);put32(report+20,1);put32(report+24,core_state);put32(report+28,core_reason);
 copy(report+32,plan+32,16);copy(report+48,plan+164,32);copy(report+80,plan+112,32);hash(plan,256,report+112);
 copy(report+144,plan+48,32);copy(report+176,plan+80,32);put64(report+208,get64(plan+144));put64(report+216,get64(plan+152));put64(report+224,finished);
 put32(report+232,(u32)sc(172,0,0,0,0));put32(report+236,(u32)sc(178,0,0,0,0));put32(report+240,1);finish_crc(report);
 root=sc(56,AT_FDCWD,(long)"/tmp_wbshd",DIR,0);
 if(root<0||!ram(root,65536)||!stat_(root,&st)||(st.mode&0170000)!=0040000||st.uid||((st.mode&022)&&!(st.mode&01000)))goto end;
 owner=sc(56,root,(long)"fx3-plan-preparation-v1",DIR,0);
 if(owner<0||!ram(owner,0)||!stat_(owner,&st)||(st.mode&0170000)!=0040000||st.uid||(st.mode&07777)!=0700)goto end;
 if(store(owner,"entry.local-result-v1.bin",report,0))ok=1;
end:
 if(owner>=0&&sc(57,owner,0,0,0))ok=0;
 if(root>=0&&sc(57,root,0,0,0))ok=0;
 last=finished;if(!tick(&last)||last>=get64(plan+152))ok=0;
 return ok;
}
/* Named directly by DT_INIT, no explicit plan argument or shell. */
__attribute__((visibility("hidden"))) void fx3_entry_init(void){
 u8 private_plan[256];if(!prepare_fixed(private_plan))return;
 state=2;int r=fx3_bridge_start(private_plan,256);u32 observed=r==11?11u:2u,why=r==11?0u:100u+(u32)r;
 int recorded=publish_local(private_plan,observed,why);
 if(recorded){state=(int)observed;reason=(int)why;}else{state=2;reason=210;}
}
__attribute__((visibility("hidden"))) int fx3_entry_state(void){return state;}
__attribute__((visibility("hidden"))) int fx3_entry_reason(void){return reason;}
'''
(H/'front.c').open('x').write(head+tail)
(H/'result-source-extension.json').open('x').write(json.dumps(dict(before_sha256=sha256(s.encode()).hexdigest(),after_sha256=sha256((head+tail).encode()).hexdigest(),own_source_only=True,record_bytes=256,record_phase='LOCAL_CORE_OBSERVATION_BEFORE_OWN_PUBLICATION_CLEANUP',host_or_device_execution=False),indent=2)+'\n')
