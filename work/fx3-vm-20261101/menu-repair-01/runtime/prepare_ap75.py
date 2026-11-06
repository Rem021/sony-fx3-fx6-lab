from pathlib import Path
import json,subprocess,os,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'ioctl-trace-v10.c').read_text()
s=s.replace('static unsigned int wait_count,send_count;',r'''static unsigned int wait_count,send_count;
static unsigned long send_seen,send_dedup,send_capacity_drop,send_lock_drop,send_emitted,stats_drop;
static unsigned char stats_lock;
static void send_stats(void){
 int saved=*__errno_location();if(__atomic_test_and_set(&stats_lock,__ATOMIC_ACQUIRE)){__atomic_add_fetch(&stats_drop,1,__ATOMIC_RELAXED);return;}
 char path[96];snprintf(path,sizeof path,"/tmp/fx3-send-stats-%d",getpid());int fd=open(path,0x20241,0600);
 if(fd>=0){dprintf(fd,"FX3_UIPC_OBSERVER_END pid=%d seen=%lu emitted=%lu dedup=%lu capacity_drop=%lu lock_drop=%lu stats_write_drop=%lu capacity=256 snapshot=1\n",getpid(),__atomic_load_n(&send_seen,__ATOMIC_RELAXED),__atomic_load_n(&send_emitted,__ATOMIC_RELAXED),__atomic_load_n(&send_dedup,__ATOMIC_RELAXED),__atomic_load_n(&send_capacity_drop,__ATOMIC_RELAXED),__atomic_load_n(&send_lock_drop,__ATOMIC_RELAXED),__atomic_load_n(&stats_drop,__ATOMIC_RELAXED));close(fd);}
 __atomic_clear(&stats_lock,__ATOMIC_RELEASE);*__errno_location()=saved;
}''')
a=s.index('static void send_unique(');b=s.index('\nstatic unsigned int ioctl_count;',a);s=s[:a]+r'''static void send_unique(unsigned int target,unsigned int op,const unsigned char *body,long n,int result,int error,void *caller){
 if(op<4||op>6||n!=16||target==0x8f013a||target==0x8f0139||target==0x8f0313||target==0x910040||target==0x910041||target==0x910042)return;
 __atomic_add_fetch(&send_seen,1,__ATOMIC_RELAXED);
 unsigned int first,second;__builtin_memcpy(&first,body,4);__builtin_memcpy(&second,body+4,4);int emit=0;
 if(target==0x8288076c||target==0x8280074d||target==0x8280084d)dprintf(2,"FX3_UI_WIRE tid=%ld target=%#x op=%u tag1=%#x tag2=%#x result=%d independent_of_unique_lock=1\n",syscall(178),target,op,first,second,result);
 if(__atomic_test_and_set(&event_lock,__ATOMIC_ACQUIRE)){__atomic_add_fetch(&send_lock_drop,1,__ATOMIC_RELAXED);send_stats();return;}
 unsigned int i;for(i=0;i<send_count;i++)if(sends[i].target==target&&sends[i].op==op&&sends[i].tag1==first&&sends[i].tag2==second)break;
 if(i<send_count)__atomic_add_fetch(&send_dedup,1,__ATOMIC_RELAXED);
 else if(send_count<256){sends[i].target=target;sends[i].op=op;sends[i].tag1=first;sends[i].tag2=second;send_count++;emit=1;__atomic_add_fetch(&send_emitted,1,__ATOMIC_RELAXED);}
 else __atomic_add_fetch(&send_capacity_drop,1,__ATOMIC_RELAXED);
 __atomic_clear(&event_lock,__ATOMIC_RELEASE);
 if(emit)dprintf(2,"FX3_UIPC_SEND_UNIQUE tid=%ld target=%#x op=%u tag1=%#x tag2=%#x result=%d errno=%d caller=%p delegated=1\n",syscall(178),target,op,first,second,result,error,caller);
 send_stats();
}
''' +s[b:];(H/'ioctl-trace-v11.c').write_text(s)
x=json.loads((H/'fx3-capid-v26-build.json').read_text());base=x['args'];start=base.index('-Wl,-soname,fx3-fx3-capid-v26.so');prefix=base[:start];libs=[str(R/'guest-sdk/lib'/n) for n in ['libc-2.25.so','libdl-2.25.so','libpthread-2.25.so','ld-2.25.so']];e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'))
for name in ['fx3-timer-observe-v1','ioctl-trace-v11']:
 a=prefix+['-Wl,-soname,'+name+'.so',str(H/(name+'.c'))]+libs+['-o',str(H/(name+'.so'))];v=subprocess.run(a,env=e,capture_output=True,text=True);assert not v.returncode,v.stderr;(H/(name+'-build.json')).write_text(json.dumps(dict(args=a,exit=0,source_sha256=hashlib.sha256((H/(name+'.c')).read_bytes()).hexdigest(),output_sha256=hashlib.sha256((H/(name+'.so')).read_bytes()).hexdigest()),indent=2))
s=(R/'build_gpe_candidate73.py').read_text().replace("D=R/'ap73-gpe-v13'","D=R/'ap75-timer-observe'").replace("base=R/'ap72-adf-muted/candidate72.json'","base=R/'ap73-gpe-v13/candidate73.json'").replace("(D/'candidate73.json')","(D/'candidate75.json')")
s=s.replace("if name=='init':", "if name=='simulation/ioctl-trace.so':data=(R/'helpers/ioctl-trace-v11.so').read_bytes()\n if name=='simulation/fx3-hdmi-registration-v1.so':entries.append(('simulation/fx3-timer-observe-v1.so',f,(R/'helpers/fx3-timer-observe-v1.so').read_bytes()))\n if name=='init':")
s=s.replace('init=data.decode();data=init.encode()',r'''init=data.decode().replace('/simulation/fx3-icrypt-observe-v1.so:/usr/lib/libInfraCrypt.so','/simulation/fx3-icrypt-observe-v1.so:/simulation/fx3-timer-observe-v1.so:/usr/lib/libInfraCrypt.so').replace('echo FX3_AP_NATURAL_OBSERVATION_END','/bin/busybox cat /tmp/fx3-send-stats-* 2>/dev/null\n echo FX3_AP_NATURAL_OBSERVATION_END').replace('while true; do /bin/busybox sleep 1; done\n','while true; do /bin/busybox cat /tmp/fx3-send-stats-* 2>/dev/null; /bin/busybox sleep 1; done\n');data=init.encode()''')
s=s.replace("(D/'candidate75.json').write_text", "v['scope']+=' AP75 observationonly timer/UI entry wrappers, originalprefixverified, no controlflow/returnchange; tracev11 lossstats.';v['required_markers']=[x for x in v['required_markers'] if x!='FX3_GPE_CMD']+['FX3_TIMER_BOUND','FX3_UI_CONFIG_DONE','FX3_UIPC_OBSERVER_END'];(D/'candidate75.json').write_text")
(R/'build_timer_candidate75.py').write_text(s);subprocess.run(['python3',str(R/'build_timer_candidate75.py')],check=True)
