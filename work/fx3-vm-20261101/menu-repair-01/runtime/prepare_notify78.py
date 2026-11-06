from pathlib import Path
import json,subprocess,os,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-ui-gate-v3.c').read_text();s=s.replace('static U known_sequence,boot_reserve;', 'static U future_event,future_cv,future_tid,boot_sequence;static U known_sequence,boot_reserve;');needle=' if(id==31&&r[0])token=*(U *)r[0];';assert needle in s
extra='''
 if(id==32){U *mf=(U *)r[20];token=mf[0];save(&future_event,token);save(&future_cv,mf[2]);save(&future_tid,tid);}
 if(id==33){token=r[0];save(&boot_sequence,r[19]);}
 if(id==34){token=r[0];important=token==load(&future_cv);}
 if(id==35){token=*(U *)(r[19]+0x1b8);important=r[19]==load(&boot_sequence);}
 if(id==36){token=r[0];important=r[30]-app_base==0x2b68390;}
 if(id==37){token=r[0];important=token==load(&future_cv);}
 if(id==38){token=load(&future_event);important=tid==load(&future_tid);}
 if(id==39){token=*(U *)r[20];important=tid==load(&future_tid);}
 if(id==40){important=n<=4;}
 if(id==41){token=r[0];important=r[19]==load(&boot_sequence);}
 if(id>=32&&important){U event=(id==34||id==37)?token-8:token;dprintf(2,"FX3_BOOT_EVENT_LINK id=%lu tid=%lu sequence=%#lx event=%#lx cv=%#lx future_cv=%#lx byte_done=%u caller=%#lx original_result=%#lx\\n",id,tid,load(&boot_sequence),event,event?event+8:0,load(&future_cv),event?*(unsigned char *)event:255,r[30]-app_base,r[0]);}
''';s=s.replace(needle,extra+needle);s=s.replace('if(id>=40){','if(id>=46){')
for a,b in [('offsets[32]','offsets[42]'),('words[32]','words[42]'),('regs[32]','regs[42]'),('i<32;i++)if(*(W *)','i<42;i++)if(*(W *)'),('i<32;i++){rc=install','i<42;i++){rc=install'),('BOUND count=32','BOUND count=42'),('pool->used+128>4096','pool->used+128>8192'),('mmap((void *)hint,4096','mmap((void *)hint,8192'),('munmap(p,4096)','munmap(p,8192)'),('mprotect(pool->p,4096','mprotect(pool->p,8192'),('-(1L<<26)+4096','-(1L<<26)+8192'),('(1L<<26)-4096','(1L<<26)-8192')]:s=s.replace(a,b)
review=json.loads((R/'ap78-notify-instruction-review.json').read_text());vas=[int(k,16) for k in review];words=[int.from_bytes(bytes.fromhex(review[hex(va)][0]['bytes']),'little') for va in vas]
for name,values in [('offsets',vas),('words',words),('regs',[31]*10)]:
 a=s.index('const '+('W' if name=='words' else 'U')+' '+name+'[42]');b=s.index('};',a);s=s[:b]+','+','.join(hex(v) for v in values)+s[b:]
s+=r'''
void _ZNSt18condition_variable4waitERSt11unique_lockISt5mutexE(void *cv,void *lock){
 int saved=*__errno_location();static void (*next)(void *,void *);void (*fn)(void *,void *)=__atomic_load_n(&next,__ATOMIC_ACQUIRE);if(!fn){fn=dlsym((void *)-1,"_ZNSt18condition_variable4waitERSt11unique_lockISt5mutexE");if(!fn)__builtin_trap();__atomic_store_n(&next,fn,__ATOMIC_RELEASE);}U tid=syscall(178),caller=(U)__builtin_return_address(0)-app_base;int observe=(U)cv==load(&future_cv)&&tid==load(&future_tid);if(observe)dprintf(2,"FX3_BOOT_CV_WAIT tid=%lu cv=%p event=%#lx caller=%#lx observed_only=1\n",tid,cv,load(&future_event),caller);*__errno_location()=saved;fn(cv,lock);saved=*__errno_location();if(observe)dprintf(2,"FX3_BOOT_CV_RETURN tid=%lu cv=%p event=%#lx caller=%#lx byte_done=%u observed_only=1\n",tid,cv,load(&future_event),caller,*(unsigned char *)load(&future_event));*__errno_location()=saved;
}
''';(H/'fx3-ui-gate-v4.c').write_text(s);a=[x.replace('fx3-ui-gate-v3','fx3-ui-gate-v4') for x in json.loads((H/'fx3-ui-gate-v3-build.json').read_text())['args']];e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));p=subprocess.run(a,env=e,capture_output=True,text=True);assert not p.returncode,p.stderr;(H/'fx3-ui-gate-v4-build.json').write_text(json.dumps({'args':a,'exit':0,'source_sha256':hashlib.sha256((H/'fx3-ui-gate-v4.c').read_bytes()).hexdigest(),'output_sha256':hashlib.sha256((H/'fx3-ui-gate-v4.so').read_bytes()).hexdigest()},indent=2)+'\n');print('gate v4 compiled;42 points and conditionalwait forwarding')
