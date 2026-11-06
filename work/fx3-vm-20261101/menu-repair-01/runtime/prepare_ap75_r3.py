from pathlib import Path
import json,hashlib,os,subprocess
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-timer-observe-v2.c').read_text();pos=s.index('void *dlopen(');s=s[:pos]+r'''
void fx3_timer_snapshot(void){
 int saved=*__errno_location();U addresses[4]={app_base+0x176fb4c,obj_base+0x176ab0,obj_base+0x100c48,app_base+0x16ee6f8};void *hooks[4]={(void *)timer_hook,(void *)table_hook,(void *)fill_hook,(void *)config_hook};unsigned int mask=0;
 if(bound)for(int i=0;i<4;i++){unsigned int words[2]={0};U dest=0;if(peek(addresses[i],words,8)&&peek(addresses[i]+8,&dest,8)&&words[0]==0x58000050&&words[1]==0xd61f0200&&dest==(U)hooks[i])mask|=1U<<i;}
 dprintf(2,"FX3_TIMER_SNAPSHOT tid=%ld bound=%u patch_mask=%#x timer_entry=%lu id_compare=%lu info=%lu table=%lu config=%lu config_target=%lu fill=%lu event_seq=%lu original_memory_read_only=1\n",syscall(178),bound,mask,timer_calls,id_calls,info_calls,table_calls,config_calls,config_target_calls,fill_calls,seq);timer_stats();*__errno_location()=saved;
}
''' +s[pos:];(H/'fx3-timer-observe-v3.c').write_text(s)
s=(H/'ioctl-trace-v11.c').read_text();needle='if(target==0x8288076c||target==0x8280074d||target==0x8280084d)dprintf';s=s.replace(needle,'if(target==0x8288076c||target==0x8280074d||target==0x8280084d){void (*snap)(void)=dlsym((void *)0,"fx3_timer_snapshot");if(snap)snap();}\n '+needle);(H/'ioctl-trace-v12.c').write_text(s)
env=os.environ.copy();env.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'))
for old,new in [('fx3-timer-observe-v2','fx3-timer-observe-v3'),('ioctl-trace-v11','ioctl-trace-v12')]:
 x=json.loads((H/(old+'-build.json')).read_text());a=[i.replace(old,new) for i in x['args']];v=subprocess.run(a,env=env,capture_output=True,text=True);assert not v.returncode,v.stderr;(H/(new+'-build.json')).write_text(json.dumps(dict(args=a,exit=0,source_sha256=hashlib.sha256((H/(new+'.c')).read_bytes()).hexdigest(),output_sha256=hashlib.sha256((H/(new+'.so')).read_bytes()).hexdigest()),indent=2))
s=(R/'build_timer_candidate75_r2.py').read_text().replace("D=R/'ap75-timer-observe-r2'","D=R/'ap75-timer-observe-r3'").replace("(R/'helpers/fx3-timer-observe-v2.so')","(R/'helpers/fx3-timer-observe-v3.so')").replace("(R/'helpers/ioctl-trace-v11.so')","(R/'helpers/ioctl-trace-v12.so')");(R/'build_timer_candidate75_r3.py').write_text(s);subprocess.run(['python3',str(R/'build_timer_candidate75_r3.py')],check=True)
