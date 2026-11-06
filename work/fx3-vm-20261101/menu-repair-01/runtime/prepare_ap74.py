from pathlib import Path
import json,hashlib,subprocess,os
R=Path(__file__).resolve().parent;H=R/'helpers'
proof=R.parents[1]/'lead-claude/audits/adf-beep-regist/adf-beep-regist-proof.json';v=json.loads(proof.read_text())
for src in v['sources'].values():assert hashlib.sha256(Path(src['path']).read_bytes()).hexdigest()==src['sha256']
# Read every supplied instruction and preserve source receipt, without modifying audit artifacts.
assert all(i['bytes'] and i['instruction'] and i['va'] for image in v['blocks'].values() for block in image.values() for i in block)
(R/'ap74-contract-review.json').write_text(json.dumps({'proof_sha256':hashlib.sha256(proof.read_bytes()).hexdigest(),'instruction_count':sum(len(b) for img in v['blocks'].values() for b in img.values()),'contract':v['contracts'],'normal_sequence':v['normal_sequence']},indent=2))
s=(H/'fx3-capid-v26.c').read_text();code=r'''
struct beep_entry {unsigned char raw[32];unsigned int valid,volume;};
static struct beep_entry beep[14];
static int beep_reject(unsigned int command,unsigned int kind,const char *reason,unsigned int original_status){
 dprintf(2,"FX3_ADF_BEEP_REJECT command=%#x kind=%u reason=%s original_status=%#x reply_added=0 muted=1 original_sound=0\n",command,kind,reason,original_status);return -1024;
}
static int beep_dispatch(void *request,unsigned int command){
 if(fault||!model.initialized||process_owner!=syscall(172)||!muted_memory||!request)return -1021;
 unsigned char *p=request;unsigned int n=command==0x327?40:10,kind=0;
 if((command!=0x327&&command!=0x32a)||msg_size(request)!=n||p[0]!=13||p[1]!=32||p[2]!=(command&255)||p[3]!=3||p[4]!=n||p[5]||p[6]!=1||p[7]!=128)return beep_reject(command,0,"wire",0);
 unsigned int from=source(request);if(!local(from))return beep_reject(command,0,"source",0);
 struct beep_entry next[14];memcpy(next,beep,sizeof next);unsigned long long physical=0;unsigned int size=0,offset=0;
 if(command==0x327){
  kind=p[20];if(!kind||kind>13||p[22]>1)return beep_reject(command,kind,"operation_or_kind",0xe004);
  if(p[22]==0){for(unsigned int i=8;i<40;i++)if(i!=20&&p[i])return beep_reject(command,kind,"unregister_fields",0);next[kind].valid=0;memset(next[kind].raw,0,32);}
  else{
   memcpy(&physical,p+8,8);memcpy(&size,p+16,4);
   if(physical<0x41da00000ULL||physical>=0x41da10000ULL||!size||size>0x41da10000ULL-physical)return beep_reject(command,kind,"backing_bounds",0);
   offset=(unsigned int)(physical-0x41da00000ULL);
   unsigned int cont=0,first=0;memcpy(&cont,p+28,4);memcpy(&first,p+32,4);
   if(p[23]||p[24]!=(cont!=0)||p[25]||p[26]||p[27]||p[36]||p[37]||p[38]||p[39]||first>size||cont>size)return beep_reject(command,kind,"descriptor_fields",0);
   if(p[21]!=(kind==4?3:kind==10||kind==11?4:6))return beep_reject(command,kind,"priority",0);
   if(next[kind].valid&&memcmp(next[kind].raw,p+8,32))return beep_reject(command,kind,"descriptor_conflict",0xe004);
   memcpy(next[kind].raw,p+8,32);next[kind].valid=1;
  }
 }else{
  kind=p[9];if(kind>13)return beep_reject(command,kind,"kind",0);
  if(p[8]>=8)return beep_reject(command,kind,"volume_bounds",0xe002);
  if(kind)next[kind].volume=p[8];else for(unsigned int i=1;i<14;i++)next[i].volume=p[8];
 }
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 unsigned char completion[12]={13,32,0,19,12,0,1,128,0,0,0,0};completion[2]=command&255;memcpy(reply,completion,12);
 set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=command;live[slot].serial=++serial;rc=send_msg(from,reply);
 if(rc){memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 memcpy(beep,next,sizeof beep);int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_ADF_BEEP_COMMIT command=%#x tid=%ld kind=%u registered=%u volume=%u phys=%#llx offset=%#x size=%u lease=%lu request_free=%d muted=1 original_sound=0 playback_supported=0\n",command,syscall(178),kind,beep[kind].valid,beep[kind].volume,physical,offset,size,live[slot].serial,freed);return 0;
}
'''
s=s.replace('extern long pread(',code+'\nextern long pread(')
s=s.replace('profile_stack(dst,request,__builtin_frame_address(0));','''profile_stack(dst,request,__builtin_frame_address(0));
 if(dst==0x5503e0&&request){unsigned int n=msg_size(request);if(n<=128){char raw[257];const char *digits="0123456789abcdef";for(unsigned int i=0;i<n;i++){unsigned char c=((unsigned char *)request)[i];raw[2*i]=digits[c>>4];raw[2*i+1]=digits[c&15];}raw[n*2]=0;struct cap_dl_info ci={0};dladdr(__builtin_return_address(0),&ci);dprintf(2,"FX3_BOOT_QUEUE_SEND tid=%ld bytes=%u source=%#x raw=%s caller_relative=%#lx passive=1 completion_not_assumed=1\\n",syscall(178),n,source(request),raw,ci.base?(unsigned long)__builtin_return_address(0)-(unsigned long)ci.base:0);}}
''')
s=s.replace('if(dst!=0x92840747||count++>=64)return;', 'if((dst!=0x92840747&&dst!=0x5503e0)||count++>=128)return;')
needle='if(h==0x032e200d||h==0x033d200d)';s=s.replace(needle,'if(h==0x0327200d||h==0x032a200d){int rc=beep_dispatch(request,h>>16);leave();*__errno_location()=saved;return rc;}'+needle)
s=s.replace('static unsigned int count;unsigned int h=0;', 'static unsigned int count,boot_count;unsigned int h=0;').replace('if((dst!=0x92840747&&dst!=0x5503e0)||count++>=128)return;', 'if(dst==0x92840747){if(count++>=64)return;}else if(dst==0x5503e0){if(boot_count++>=32)return;}else return;')
(H/'fx3-capid-v27.c').write_text(s)
t=(H/'check-adf-muted-transport.c').read_text().replace('fx3-capid-v26.c','fx3-capid-v27.c');pos=t.index(' pthread_t threads[8]');test=r'''
 reset();model.initialized=1;muted_memory=backing;in_size=40;memset(beep,0,sizeof beep);
 const unsigned char bp[40]={13,32,39,3,40,0,1,128,0,0,160,29,4,0,0,0,0,1,0,0,1,6,1};memcpy(request,bp,40);
 assert(!beep_dispatch(request,0x327)&&beep[1].valid&&reply[2]==39&&reply[3]==19);assert(!osal_free_msg(src,reply));assert(!beep_dispatch(request,0x327));assert(!osal_free_msg(src,reply));
 struct beep_entry priorbeep[14];memcpy(priorbeep,beep,sizeof beep);request[16]++;assert(beep_dispatch(request,0x327)==-1024&&!memcmp(priorbeep,beep,sizeof beep));memcpy(request,bp,40);request[12]=5;assert(beep_dispatch(request,0x327)==-1024);memcpy(request,bp,40);request[22]=2;assert(beep_dispatch(request,0x327)==-1024);
 memcpy(request,bp,40);send_rc=-1020;assert(beep_dispatch(request,0x327)==-1020&&!live[0].p&&!memcmp(priorbeep,beep,sizeof beep));send_rc=0;
 in_size=10;const unsigned char bv[10]={13,32,42,3,10,0,1,128,7,1};memcpy(request,bv,10);assert(!beep_dispatch(request,0x32a)&&beep[1].volume==7);assert(!osal_free_msg(src,reply));request[8]=8;assert(beep_dispatch(request,0x32a)==-1024&&beep[1].volume==7);request[8]=0;request[9]=0;assert(!beep_dispatch(request,0x32a));assert(!osal_free_msg(src,reply));for(unsigned int i=1;i<14;i++)assert(!beep[i].volume);
 in_size=40;memcpy(request,bp,40);memset(request+8,0,32);request[20]=1;assert(!beep_dispatch(request,0x327)&&!beep[1].valid);assert(!osal_free_msg(src,reply));request[20]=4;assert(!beep_dispatch(request,0x327));assert(!osal_free_msg(src,reply));
 puts("ADF_BEEP_PASS registration/duplicate/unregister_index6/volumeall/e004conflict/e002volume/bounds/sendrollback/ownership");
''';t=t[:pos]+test+t[pos:];(H/'check-adf-beep-transport.c').write_text(t)
a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread',str(H/'check-adf-beep-transport.c'),str(H/'capid-service.c'),str(H/'fx3-sa-address-core.c'),'-o',str(H/'check-adf-beep-transport')];subprocess.run(a,check=True);x=subprocess.run([a[-1]],capture_output=True,text=True);(H/'adf-beep-host-check.json').write_text(json.dumps(dict(args=a,exit=x.returncode,stdout=x.stdout,stderr=x.stderr),indent=2));assert not x.returncode,x.stderr
x=json.loads((H/'fx3-capid-v26-build.json').read_text());a=[i.replace('fx3-capid-v26','fx3-capid-v27') for i in x['args']];e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));subprocess.run(a,env=e,check=True);(H/'fx3-capid-v27-build.json').write_text(json.dumps(dict(args=a,exit=0,source_sha256=hashlib.sha256((H/'fx3-capid-v27.c').read_bytes()).hexdigest(),output_sha256=hashlib.sha256((H/'fx3-capid-v27.so').read_bytes()).hexdigest()),indent=2))
s=(R/'build_gpe_candidate73.py').read_text().replace("D=R/'ap73-gpe-v13'","D=R/'ap74-beep-registration-r2'").replace("base=R/'ap72-adf-muted/candidate72.json'","base=R/'ap73-gpe-v13/candidate73.json'").replace("(D/'candidate73.json')","(D/'candidate74.json')").replace('fx3-capid-v26.so','fx3-capid-v27.so');s=s.replace("(D/'candidate74.json').write_text", "v['scope']+=' AP74 strictbeep327/32a descriptorsandvolumes only; mutedstoragebound; unknownfile/DMM/transferunsupported.';v['required_markers']+=['FX3_ADF_BEEP_COMMIT'];(D/'candidate74.json').write_text");(R/'build_beep_candidate74.py').write_text(s);subprocess.run(['python3',str(R/'build_beep_candidate74.py')],check=True)
