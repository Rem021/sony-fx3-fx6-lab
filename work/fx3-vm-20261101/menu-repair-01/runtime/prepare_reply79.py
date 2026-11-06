from pathlib import Path
import json,subprocess,os,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';assert not (H/'fx3-capid-v32.c').exists();s=(H/'fx3-capid-v31.c').read_text()
code=r'''
struct tail_panel {unsigned int shadow_valid,selector,enumeration,pending_hardware,cache_valid,cache_enum,updates;};
struct tail_hdmi {unsigned int definition_known,definition,resolution_known,next_port,rate_known[5],rate[5],updates;unsigned char parameters[8];};
static struct tail_panel panel165;static struct tail_hdmi hdmi_boot;static struct {void *request;unsigned int kind;} tail_live[8];static int (*backup_observed)(unsigned int *);
static int tail_dispatch(unsigned int dst,void *request,unsigned int command){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;unsigned int n=msg_size(request),from=source(request),kind=0,port=0,rate=0,backup=0,known=0;if(!local(from))return -1024;
 const unsigned char *q=request;const char *surface=getenv("FX3_DISPLAY_INFO"),*inactive=getenv("FX3_HDMI_BOOT");
 if(dst==0x92840747&&command==0x165){const unsigned char exact[10]={13,32,0x65,1,10,0,1,128,2,0};if(!surface||strcmp(surface,"software-640x480-v1")||n!=10||memcmp(q,exact,10))return -1024;kind=1;}
 else if(dst==0x909a015a){if(!inactive||strcmp(inactive,"disconnected-inactive-v1")||!hdmi_tc.known||hdmi_tc.tc_output)return -1024;
  if(command==0x10a){const unsigned char exact[12]={0,37,10,1,12,0,1,0,0,0,0,0};if(n!=12||memcmp(q,exact,12))return -1024;kind=2;}
  else if(command==0x101){const unsigned char exact[16]={0,37,1,1,16,0,1,0,0,0,0,0,6,5,0,0};if(n!=16||memcmp(q,exact,16))return -1024;kind=3;}
  else if(command==0x117){const unsigned char exact[8]={0,37,23,1,12,0,1,0};if(n!=12||memcmp(q,exact,8))return -1024;port=q[8];rate=q[9];if(!backup_observed)backup_observed=dlsym((void *)-1,"fx3_observed_backup_rate");if(backup_observed)known=backup_observed(&backup);dprintf(2,"FX3_HDMI_RATE_OBSERVE source=%#x port=%u rate=%u echoed_port=%u echoed_rate=%u backup_known=%u backup_02cf1493=%u next_port=%u before_admission=1\n",from,port,rate,q[10],q[11],known,backup,hdmi_boot.next_port);const unsigned char expected[5]={0,0,17,17,0};if(!known||port>=5||port!=hdmi_boot.next_port||q[10]!=port||q[11]!=rate||rate!=(backup==7?7:expected[port]))return -1024;kind=4;}
  else return -1024;
 }else return -1024;
 int slot=-1;for(int i=0;i<8;i++){if(tail_live[i].request&&live[i].p&&((kind==1&&tail_live[i].kind==1)||(kind>=2&&tail_live[i].kind>=2)||tail_live[i].request==request))return -1021;if(!live[i].p&&slot<0)slot=i;}if(slot<0)return -1021;
 struct tail_panel before_panel=panel165;struct tail_hdmi before_hdmi=hdmi_boot;
 if(kind==1){panel165.shadow_valid=1;panel165.selector=2;panel165.enumeration=0;panel165.pending_hardware=1;panel165.updates++;}
 else if(kind==2){hdmi_boot.definition_known=1;hdmi_boot.definition=0;hdmi_boot.updates++;}
 else if(kind==3){hdmi_boot.resolution_known=1;memcpy(hdmi_boot.parameters,q+8,8);hdmi_boot.updates++;}
 else {hdmi_boot.rate_known[port]=1;hdmi_boot.rate[port]=rate;hdmi_boot.next_port++;hdmi_boot.updates++;}
 void *reply=0;int rc=allocate(from,&reply,12,1);if(reply&&reply==request){fault=1;panel165=before_panel;hdmi_boot=before_hdmi;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;panel165=before_panel;hdmi_boot=before_hdmi;return -1021;}if(rc||!reply){panel165=before_panel;hdmi_boot=before_hdmi;if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 unsigned char out[12]={0};if(kind==1){const unsigned char exact[12]={13,32,0x65,0x11,12,0,1,128,0,0,89,0};memcpy(out,exact,12);}else {out[1]=37;out[2]=command&255;out[3]=129;out[4]=12;out[6]=1;if(kind==2)out[8]=1;}memcpy(reply,out,12);set_source(reply,dst);live[slot].p=reply;live[slot].dst=from;live[slot].command=command;live[slot].serial=++serial;tail_live[slot].request=request;tail_live[slot].kind=kind;rc=send_msg(from,reply);
 if(rc){panel165=before_panel;hdmi_boot=before_hdmi;memset(tail_live+slot,0,sizeof tail_live[slot]);memset(live+slot,0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 if(kind==1){panel165.cache_valid=1;panel165.cache_enum=0;}int freed=release(dst,request);if(freed)fault=1;dprintf(2,"FX3_BOOT_TAIL_COMMIT destination=%#x command=%#x source=%#x kind=%u port=%u rate=%u backup_known=%u backup=%u reply_status=%#x lease=%lu request_free=%d selector=%u enum=%u cache_valid=%u pending_hardware=%u hpd=0 output_ready=0 physical_output=0\n",dst,command,from,kind,port,rate,known,backup,kind==1?0x590000:kind==2?1:0,live[slot].serial,freed,panel165.selector,panel165.enumeration,panel165.cache_valid,panel165.pending_hardware);return 0;
}
static void boot_tail_observe(unsigned int dst,void *request,void *frame,unsigned int op){
 if(!request)return;unsigned int n=msg_size(request),magic=0,head=0;if(n>=8)memcpy(&magic,(unsigned char *)request+4,4);if(n>=4)memcpy(&head,request,4);int flow=n>=24&&magic==0xa0a0a0a0U;int late=dst==0x912f0335||(dst==0x92840747&&(head==0x0328200d||head==0x0119200d));if(!flow&&!late)return;
 static unsigned int flow_count,late_count;unsigned int seq=__atomic_add_fetch(flow?&flow_count:&late_count,1,__ATOMIC_RELAXED),limit=flow?512:64;if(seq>limit){if(seq==limit+1)dprintf(2,"FX3_BOOT_TAIL_OBSERVE_LIMIT flow=%d limit=%u\n",flow,limit);return;}unsigned int bytes=n<=2048?n:2048;char raw[4097];const char *h="0123456789abcdef";for(unsigned int i=0;i<bytes;i++){unsigned char c=((unsigned char *)request)[i];raw[2*i]=h[c>>4];raw[2*i+1]=h[c&15];}raw[bytes*2]=0;dprintf(2,"FX3_BOOT_TAIL_REQUEST tid=%ld destination=%#x op=%u source=%#x bytes=%u observed=%u flow=%d truncated=%d raw=%s attempt_only=1 reply_added_here=0\n",syscall(178),dst,op,source(request),n,seq,flow,bytes!=n,raw);
 int fd=open("/proc/self/mem",0);unsigned long start=(unsigned long)frame,fp=start;for(int i=0;fd>=0&&i<14;i++){unsigned long row[2];if(fp<start||fp-start>0x20000||(fp&15)||pread(fd,row,16,fp)!=16)break;struct cap_dl_info info={0};dladdr((void *)row[1],&info);dprintf(2,"FX3_BOOT_TAIL_FRAME destination=%#x seq=%u depth=%d fp=%#lx lr=%#lx module=%s relative=%#lx\n",dst,seq,i,fp,row[1],info.file?info.file:"?",info.base?row[1]-(unsigned long)info.base:0);if(row[0]<=fp)break;fp=row[0];}if(fd>=0)close(fd);
}
'''
# The new helpers use existing hdmi_tc and transport declarations, so insert after the old functions.
needle='int osal_snd_msg(unsigned int dst,void *request){';s=s.replace(needle,code+'\n'+needle)
s=s.replace(' profile_stack(dst,request,__builtin_frame_address(0));\n if(dst==0x5503e0', ' profile_stack(dst,request,__builtin_frame_address(0));\n boot_tail_observe(dst,request,__builtin_frame_address(0),4);\n if(dst==0x5503e0',1)
needle=' const char *boot_profile=getenv("FX3_BOOT_REPLY");';s=s.replace(needle,''' const char *tail_profile=getenv("FX3_BOOT_TAIL");
 if(enabled&&request&&tail_profile&&!strcmp(tail_profile,"audited-panel-hdmi-v1")&&msg_size(request)>=4){unsigned int header;memcpy(&header,request,4);if((dst==0x92840747&&header==0x0165200d)||(dst==0x909a015a&&(header==0x010a2500||header==0x01012500||header==0x01172500))){unsigned int command=header>>16;enter();int out=tail_dispatch(dst,request,command);leave();*__errno_location()=saved;return out;}}
'''+needle)
s=s.replace('else {if(gf_live_request[found])','else {if(tail_live[found].request){dprintf(2,"FX3_BOOT_TAIL_CONSUMED destination=%#x command=%#x kind=%u lease=%lu result=0\\n",dst,live[found].command,tail_live[found].kind,live[found].serial);memset(tail_live+found,0,sizeof tail_live[found]);}if(gf_live_request[found])')
s=s.replace(' int saved=*__errno_location();enter();initialize();leave();const char *profile=getenv("FX3_ADF_FILE");',' int saved=*__errno_location();enter();initialize();leave();boot_tail_observe(dst,request,__builtin_frame_address(0),5);const char *profile=getenv("FX3_ADF_FILE");')
(H/'fx3-capid-v32.c').write_text(s);a=[x.replace('fx3-capid-v31','fx3-capid-v32') for x in json.loads((H/'fx3-capid-v31-build.json').read_text())['args']];e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));p=subprocess.run(a,env=e,capture_output=True,text=True);assert not p.returncode,p.stderr;(H/'fx3-capid-v32-build.json').write_text(json.dumps({'args':a,'exit':0,'source_sha256':hashlib.sha256((H/'fx3-capid-v32.c').read_bytes()).hexdigest(),'output_sha256':hashlib.sha256((H/'fx3-capid-v32.so').read_bytes()).hexdigest()},indent=2)+'\n');print('v32 ready')
