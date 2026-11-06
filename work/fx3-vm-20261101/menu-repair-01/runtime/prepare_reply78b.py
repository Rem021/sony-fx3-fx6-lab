# Preparation draft; final v31 source and SHA-pinned build args are authoritative.
# Final active-request dedupe and bind marker were applied before final ASan/build.
from pathlib import Path
import json,hashlib,subprocess,os
R=Path(__file__).resolve().parent;H=R/'helpers';assert not (H/'fx3-capid-v31.c').exists(),'v31 already frozen; create a new helper version instead of overwriting';s=(H/'fx3-capid-v30.c').read_text();frozen=(R/'ap78a-frozen-request.bin').read_bytes();assert len(frozen)==52
code=r'''
static void *tc_live_request[8];static unsigned int tc_live_padding[8];
static unsigned int tc_stack_mask(void *frame){int fd=open("/proc/self/mem",0);if(fd<0)return 0;unsigned long start=(unsigned long)frame,fp=start;unsigned int mask=0;for(int i=0;i<16;i++){unsigned long row[2];if(fp<start||fp-start>0x20000||(fp&15)||pread(fd,row,16,fp)!=16)break;struct cap_dl_info info={0};if(dladdr((void *)row[1],&info)&&info.base&&info.file){unsigned long rel=row[1]-(unsigned long)info.base;if(strstr(info.file,"dataflowInfraFramework.so")&&rel==0x33f20)mask|=1;if(strstr(info.file,"appFw.so")&&rel==0x2debc58)mask|=2;if(strstr(info.file,"appFw.so")&&rel==0x2b66f2c)mask|=4;}if(row[0]<=fp)break;fp=row[0];}close(fd);return mask;}
static const unsigned char tc_frozen[52]={FROZEN};
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
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;void *reply=0;int rc=allocate(from,&reply,28,1);if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}unsigned char packet[28]={13,32,0x25,0x13,28,0,1,128,0,0,0,0};memset(packet+12,128,16);memcpy(reply,packet,28);set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x325;live[slot].serial=++serial;rc=send_msg(from,reply);if(rc){memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}int freed=release(0x92840747,request);if(freed)fault=1;dprintf(2,"FX3_ADF_GET_FUNC_COMMIT source=%#x bytes=28 capabilities=80x16 lowcut=80 request_free=%d lease=%lu muted=1 original_sound=0 playback_supported=0 complementary_AP_flags_not_audio_support=1\n",from,freed,live[slot].serial);return 0;
}
'''.replace('FROZEN',','.join(hex(x) for x in frozen))
needle='int osal_snd_msg(unsigned int dst,void *request){';s=s.replace(needle,code+'\n'+needle)
needle=' enter();\n const char *observe=getenv("FX3_VDF_OBSERVE");';assert needle in s
s=s.replace(needle,''' const char *boot_profile=getenv("FX3_BOOT_REPLY");
 if(enabled&&boot_profile&&!strcmp(boot_profile,"timecode-getfunc-muted-v1")&&request){
  if(dst==0x9059000e){unsigned int mask=tc_stack_mask(__builtin_frame_address(0));enter();int out=timecode_dispatch(request,mask);leave();*__errno_location()=saved;return out;}
  if(dst==0x92840747&&msg_size(request)>=4){unsigned int head;memcpy(&head,request,4);if(head==0x0325200d){enter();int out=get_func_dispatch(request);leave();*__errno_location()=saved;return out;}}
 }
'''+needle)
needle='if(rc)fault=1;else {if(ff_pending[found])';assert needle in s;s=s.replace(needle,'if(rc)fault=1;else {if(tc_live_request[found]){dprintf(2,"FX3_TIMECODE_REPLY_CONSUMED destination=%#x lease=%lu padding=%08x result=0 request_key=%p\\n",dst,live[found].serial,tc_live_padding[found],tc_live_request[found]);tc_live_request[found]=0;tc_live_padding[found]=0;}if(ff_pending[found])')
(H/'fx3-capid-v31.c').write_text(s);a=[x.replace('fx3-capid-v30','fx3-capid-v31') for x in json.loads((H/'fx3-capid-v30-build.json').read_text())['args']];e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));p=subprocess.run(a,env=e,capture_output=True,text=True);assert not p.returncode,p.stderr;(H/'fx3-capid-v31-build.json').write_text(json.dumps({'args':a,'exit':0,'source_sha256':hashlib.sha256((H/'fx3-capid-v31.c').read_bytes()).hexdigest(),'output_sha256':hashlib.sha256((H/'fx3-capid-v31.so').read_bytes()).hexdigest(),'frozen_request_sha256':hashlib.sha256(frozen).hexdigest()},indent=2)+'\n');print('v31 compiled')
