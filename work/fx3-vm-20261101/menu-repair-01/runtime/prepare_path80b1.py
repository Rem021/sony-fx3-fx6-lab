from pathlib import Path
import json,subprocess,hashlib,os
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-capid-v33.c').read_text();code=r'''
static struct {unsigned known,path,updates,playback_enabled;void *active_request;} sound_path;
static unsigned char sound_path_lease[8];
static int sound_path_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request||!muted_memory)return -1021;
 const unsigned char exact[10]={13,32,40,3,10,0,1,128,3,0};if(msg_size(request)!=10||memcmp(request,exact,10))return -1024;unsigned from=source(request);if(!local(from))return -1024;if(sound_path.active_request)return -1021;
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;void *reply=0;int rc=allocate(from,&reply,12,1);if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 unsigned before_known=sound_path.known,before_path=sound_path.path,before_updates=sound_path.updates;sound_path.known=1;sound_path.path=3;sound_path.playback_enabled=0;sound_path.updates++;sound_path.active_request=request;const unsigned char out[12]={13,32,40,19,12,0,1,128,0,0,88,0};memcpy(reply,out,12);set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x328;live[slot].serial=++serial;sound_path_lease[slot]=1;rc=send_msg(from,reply);
 if(rc){sound_path.known=before_known;sound_path.path=before_path;sound_path.updates=before_updates;sound_path.active_request=0;sound_path_lease[slot]=0;memset(live+slot,0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}int freed=release(0x92840747,request);if(freed)fault=1;dprintf(2,"FX3_ADF_PATH_COMMIT source=%#x path=3 status=0x580000 lease=%lu request_free=%d original_sound=0 playback_enabled=0\n",from,live[slot].serial,freed);return 0;
}
''';s=s.replace('int osal_snd_msg(unsigned int dst,void *request){',code+'\nint osal_snd_msg(unsigned int dst,void *request){');needle=' const char *pin_profile=getenv("FX3_PIN_GRAPH");';s=s.replace(needle,''' const char *path_profile=getenv("FX3_BOOT_DEFERRED");if(enabled&&request&&path_profile&&!strcmp(path_profile,"muted-path3-v1")&&dst==0x92840747&&msg_size(request)>=4&&pg_get(request)==0x0328200d){enter();int out=sound_path_dispatch(request);leave();*__errno_location()=saved;return out;}
'''+needle);s=s.replace('else {if(is_pin)pin_retire','else {if(sound_path_lease[found]){dprintf(2,"FX3_ADF_PATH_CONSUMED lease=%lu path=%u result=0\\n",live[found].serial,sound_path.path);sound_path_lease[found]=0;sound_path.active_request=0;}if(is_pin)pin_retire');(H/'fx3-capid-v34.c').write_text(s)
s=(H/'fx3-ui-gate-v6.c').read_text();s=s.replace('static U observed_backup_known,','static U observed_reverse_known,observed_reverse_enum;int fx3_observed_reverse_enum(unsigned int *out){if(!__atomic_load_n(&observed_reverse_known,__ATOMIC_ACQUIRE))return 0;*out=(unsigned int)__atomic_load_n(&observed_reverse_enum,__ATOMIC_RELAXED);return 1;}\nstatic U observed_backup_known,');needle=' if(id==42){';s=s.replace(needle,''' if(id==45){token=*(W *)(r[0]+0x304);save(&observed_reverse_enum,token);__atomic_store_n(&observed_reverse_known,1,__ATOMIC_RELEASE);if(ram){ram[12]=1;ram[13]=token;}dprintf(2,"FX3_PANEL_REVERSE_ENUM tid=%lu sequence=%#lx enum=%lu captured_before_wrapper=1\\n",tid,r[0],token);}
'''+needle);s=s.replace('offsets[45]','offsets[46]').replace('words[45]','words[46]').replace('regs[45]','regs[46]').replace('i<45;i++)if(*(W *)','i<46;i++)if(*(W *)').replace('i<45;i++){rc=install','i<46;i++){rc=install').replace('BOUND count=45','BOUND count=46')
for name,value in [('offsets',0x2b5fc68),('words',0xa9bc7bfd),('regs',31)]:
 a=s.index('const '+('W' if name=='words' else 'U')+' '+name+'[46]');b=s.index('};',a);s=s[:b]+','+hex(value)+s[b:]
(H/'fx3-ui-gate-v7.c').write_text(s)
e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'))
for name,old in [('fx3-capid-v34','fx3-capid-v33'),('fx3-ui-gate-v7','fx3-ui-gate-v6')]:
 a=[x.replace(old,name) for x in json.loads((H/(old+'-build.json')).read_text())['args']];p=subprocess.run(a,env=e,capture_output=True,text=True);assert not p.returncode,p.stderr;(H/(name+'-build.json')).write_text(json.dumps({'args':a,'exit':0,'source_sha256':hashlib.sha256((H/(name+'.c')).read_bytes()).hexdigest(),'output_sha256':hashlib.sha256((H/(name+'.so')).read_bytes()).hexdigest()},indent=2)+'\n')
print('v34 path3/gatev7 staged')
