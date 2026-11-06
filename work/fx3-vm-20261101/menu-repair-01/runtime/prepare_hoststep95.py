from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers'
core=r'''#ifndef FX3_INPUT95_HOSTSTEP_V1_H
#define FX3_INPUT95_HOSTSTEP_V1_H
/* Host-owned command12 at+8. No predefined sequence; no autonomous next key.
 * delete_key=0 until independent key audit is approved by Lead. */
#define HP95_MAGIC 0x3545594b334d5253UL
#define HP95_MAX_STEPS 30U
struct hp95_command {unsigned step,key,hold_ms;};
static int hp95_allowed(unsigned key,unsigned delete_key){return key==3||key==0x30||key==0x15||key==0x1af||key==0x1ac||key==0x1ab||(delete_key&&key==delete_key);}
static int hp95_validate(unsigned done,const struct hp95_command*c,unsigned delete_key){if(!c||done>=30||c->step!=done+1||c->step>30)return -1;if(!hp95_allowed(c->key,delete_key))return -2;if(c->hold_ms<50||c->hold_ms>200)return -3;return 0;}
static int hp95_pack(unsigned key,unsigned down,unsigned delete_key,unsigned char*p){if(!p||down>1||!hp95_allowed(key,delete_key))return -1;for(unsigned i=0;i<20;i++)p[i]=0;for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(key>>(8*i));p[8]=(unsigned char)down;p[16]=1;return 0;}
#endif
''';(H/'fx3-input95-hoststep-v1.h').write_text(core)
s=(H/'fx3-rm-key-gate-v3-up-enter.inc').read_text();s=s.replace('#include "fx3-synth-key-core-v1.h"\n#include "fx3-input94-plan-v1.h"','#include "fx3-input95-hoststep-v1.h"\n#ifndef HP95_DELETE_KEY\n#define HP95_DELETE_KEY 0U\n#endif');s=s.replace('KEY93_MAGIC 0x3345594b334d5253UL','KEY93_MAGIC HP95_MAGIC').replace('sk_pack(key,down,b)','hp95_pack(key,down,HP95_DELETE_KEY,b)');a=s.index(' W done=0;struct plan93');b=s.index('\n return 0;}',a)
s=s[:a]+r''' W done=0;dprintf(2,"FX3_KEY95_READY physical=%#lx bytes=65536 header_magic=%#lx host_command_bytes=12 step_key_hold_ms_offset8=1 done_offset24=1 max_steps=30 hold_ms_min=50 hold_ms_max=200 delete_key=%#x native_NOLOAD_base=%#lx synthetic_input=1 original_cp_key_detection=0 host_step_only=1\n",KEY93_PHYS,KEY93_MAGIC,HP95_DELETE_KEY,key_obj);
 for(;;){if(__atomic_load_n(&failed,__ATOMIC_ACQUIRE))return 0;W command=__atomic_load_n((volatile W*)(key_control+8),__ATOMIC_ACQUIRE);if(command==done){usleep(5000);continue;}struct hp95_command c={command,__atomic_load_n((volatile W*)(key_control+12),__ATOMIC_ACQUIRE),__atomic_load_n((volatile W*)(key_control+16),__ATOMIC_ACQUIRE)};if(command!=__atomic_load_n((volatile W*)(key_control+8),__ATOMIC_ACQUIRE)||hp95_validate(done,&c,HP95_DELETE_KEY)||!__atomic_load_n(&receiver_seen,__ATOMIC_ACQUIRE)){event("KEY_REJECT",5,c.step,c.key);return 0;}W cache=0;if(!key_cache(c.key,&cache)){event("KEY_REJECT",6,c.step,c.key);return 0;}dprintf(2,"FX3_KEY_CACHE step=%u key=%#x when=before_down readable=1 status=%#x native_cache_readonly=1\n",c.step,c.key,cache);U start=now();if(key_send(c.step,c.key,1)){event("KEY_REJECT",7,c.step,c.key);return 0;}U down=now();*(volatile U*)(key_control+32)=down;int wait_rc=usleep(c.hold_ms*1000);if(key_send(c.step,c.key,0)){event("KEY_REJECT",8,c.step,c.key);return 0;}U up=now();*(volatile U*)(key_control+40)=up;*(volatile W*)(key_control+28)=c.key;*(volatile W*)(key_control+48)=c.hold_ms;*(volatile W*)(key_control+52)=wait_rc?1:0;*(volatile U*)(key_control+56)=c.step*2;done=c.step;__atomic_store_n((volatile W*)(key_control+24),done,__ATOMIC_RELEASE);dprintf(2,"FX3_KEY95_STEP_DONE step=%u key=%#x requested_hold_ms=%u measured_down_up_ns=%lu elapsed_ns=%lu wait_result=%d native_input_queue=1 one_down_one_up=1 host_next_required=1\n",done,c.key,c.hold_ms,up-down,now()-start,wait_rc);if(wait_rc){event("KEY_REJECT",9,c.step,c.key);return 0;}if(done>=30)return 0;}
'''+s[b:];(H/'fx3-rm-key-gate-v4-hoststep.inc').write_text(s)
s=(H/'fx3-rm-empty-provider-v4-up-enter.c').read_text().replace('fx3-rm-key-gate-v3-up-enter.inc','fx3-rm-key-gate-v4-hoststep.inc');(H/'fx3-rm-empty-provider-v5-hoststep.c').write_text(s)
# Same local Unix GDB transport; only the new software-owned command12 is written.
s=(R/'gate_input94.py').read_text();a=s.index('PHYS=');b=s.index('class InputGate:',a);s=s[:a]+'''PHYS=0x41df00000;MAGIC=0x3545594b334d5253;BASE_KEYS={3,0x30,0x15,0x1af,0x1ac,0x1ab}
def valid_command(step,key,hold_ms,count,delete_key=0):
 return count<30 and step==count+1 and 1<=step<=30 and key in BASE_KEYS|({delete_key} if delete_key else set()) and 50<=hold_ms<=200
'''+s[b:];s=s.replace('def __init__(self,run):self.run=Path(run);self.sock=None;self.history=[]','def __init__(self,run,delete_key=0):self.run=Path(run);self.sock=None;self.history=[];self.delete_key=delete_key');a=s.index(' def command(self,');s=s[:a]+''' def command(self,step,key,hold_ms,observed_page,reason):
  if not observed_page or not reason or not valid_command(step,key,hold_ms,len(self.history),self.delete_key):raise ValueError('Unapproved host-step command/key/hold/visual reasoning')
  self.connect();raw=bytes.fromhex(self.packet(f'm{PHYS:x},40'))
  if len(raw)!=64:raise RuntimeError('short host-step software header')
  magic,previous,oldkey,oldhold,reserved,done,donekey=struct.unpack_from('<Q6I',raw)
  result=struct.unpack_from('<I',raw,52)[0]
  if magic!=MAGIC or previous!=step-1 or done!=step-1 or reserved or result:raise RuntimeError('host-step software identity/order/result mismatch')
  data=struct.pack('<III',step,key,hold_ms);address=PHYS+8
  if self.packet(f'M{address:x},c:{data.hex()}')!='OK':raise RuntimeError('host-step command write failed')
  check=bytes.fromhex(self.packet(f'm{address:x},c'))
  if check!=data:raise RuntimeError('host-step command readback mismatch')
  item={'step':step,'key':hex(key),'hold_ms':hold_ms,'observed_page':observed_page,'reason':reason,'physical':hex(address),'bytes':12,'before_header_hex':raw.hex(),'written_hex':data.hex(),'readback_hex':check.hex(),'software_gate_only':True,'no_original_UI_or_parameter_write':True,'host_monotonic':time.monotonic()};self.history.append(item);(self.run/'ap95-host-input-gate.json').write_text(json.dumps(self.history,ensure_ascii=False,indent=2)+'\\n');return item
''';(R/'gate_input95.py').write_text(s);compile(s,'gate_input95.py','exec')
# New readback stem only; physical lease and SHA checks are unchanged.
s=(R/'key_readback93_v2_frame.py').read_text().replace("stem='ap93-'+label","stem='ap95-'+label");(R/'key_readback95.py').write_text(s)
s=(R/'run_candidate94.py').read_text().replace('from gate_input94 import InputGate','from gate_input95 import InputGate,valid_command').replace('key_readback93_v2_frame','key_readback95').replace("'gate_input94.py'","'gate_input95.py'").replace('input_gate=InputGate(run)','input_gate=InputGate(run,delete_key=int(candidate.get("host_step_contract",{}).get("delete_key","0"),0))').replace('FX3_KEY93_READY','FX3_KEY95_READY').replace('ap94-step-readbacks.json','ap95-step-readbacks.json').replace('ap94-phaseA.json','ap95-phaseA.json')
s=s.replace("                        input_gate.command(1,3);host_step=1;qmp('cont')", "                        qmp('cont')")
a=s.index('                if host_step>=1 and host_step<19');b=s.index("                if 'FX3_AP89_BACKUP_REPLAY_VERIFIED'",a)
s=s[:a]+'''                if phaseA_capture is not None and host_step<30 and (host_step==0 or step_captures and step_captures[-1]['step']==host_step and time.monotonic()-up_seen[host_step][0]>=4):
                    proposed_path=run/'ap95-next-key.json'
                    if proposed_path.exists():
                        proposed=json.loads(proposed_path.read_text())
                        if proposed.get('step')==host_step+1:
                            key=int(proposed['key'],0);hold_ms=proposed.get('hold_ms');description=proposed.get('observed_page');reason_text=proposed.get('reason')
                            if proposed.get('authorization')!='msg_8162589b2b22' or not isinstance(hold_ms,int) or not valid_command(host_step+1,key,hold_ms,host_step,input_gate.delete_key) or not description or not reason_text:
                                early_stop_reason='AP95 host single-step whitelist/hold/visual authorization rejected before any guest write';break
                            qmp('stop');host_step+=1;input_gate.command(host_step,key,hold_ms,description,reason_text);qmp('cont')
                        elif proposed.get('step',0)>host_step+1:
                            early_stop_reason='AP95 out-of-order host single-step command';break
'''+s[b:];s=s.replace("'AP93 per-step QMP readback failed'","'AP95 per-step QMP readback failed'");(R/'run_candidate95.py').write_text(s);compile(s,'run_candidate95.py','exec')
# Core acceptance/rejection and exact native20 byte pack under sanitizer.
s=r'''#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "fx3-input95-hoststep-v1.h"
int main(void){unsigned keys[6]={3,0x30,0x15,0x1af,0x1ac,0x1ab};unsigned char p[20],expected[20];for(unsigned step=1;step<=30;step++){struct hp95_command c={step,keys[(step-1)%6],100};assert(!hp95_validate(step-1,&c,0));for(unsigned down=0;down<2;down++){memset(expected,0,20);memcpy(expected,&c.key,4);expected[8]=down;expected[16]=1;assert(!hp95_pack(c.key,down,0,p)&&!memcmp(p,expected,20));}}struct hp95_command c={1,3,100};assert(hp95_validate(30,&c,0));c.step=2;assert(hp95_validate(0,&c,0));c.step=1;c.key=0x99;assert(hp95_validate(0,&c,0));c.key=0x1f8;assert(hp95_validate(0,&c,0));c.key=3;c.hold_ms=49;assert(hp95_validate(0,&c,0));c.hold_ms=201;assert(hp95_validate(0,&c,0));c.hold_ms=50;assert(!hp95_validate(0,&c,0));c.hold_ms=200;assert(!hp95_validate(0,&c,0));assert(hp95_pack(3,2,0,p));puts("HOSTSTEP95_CORE_PASS six_audited_keys/30steps_monotonic/exact20B_downup/unknown_and_pending_delete_reject/hold50to200_boundaries/no_auto_next_script");return 0;}
''';(H/'check-hoststep95-core.c').write_text(s);args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(H/'check-hoststep95-core.c'),'-o',str(H/'check-hoststep95-core')];p=subprocess.run(args,capture_output=True,text=True);assert not p.returncode,p.stderr;p=subprocess.run([str(H/'check-hoststep95-core')],capture_output=True,text=True);(H/'check-hoststep95-core.log').write_text(p.stdout+p.stderr);assert not p.returncode;print(p.stdout)
(R/'ap95-hoststep-preparation.json').write_text(json.dumps({'authority':'msg_8162589b2b22','pending_delete_audit':True,'guest_delete_key_enabled':False,'guest_not_built_or_run':True,'core_ASan_UBSan_exit':0,'software_control_layout':{'magic':'0x3545594b334d5253','host_command_step_key_hold_ms_at8_bytes':12,'done_at24':'u32','done_key_at28':'u32','down_ns_at32':'u64','up_ns_at40':'u64','done_hold_ms_at48':'u32','result_at52':'u32','native_send_count_at56':'u64'},'host_only_no_autonomous_first_UP':True,'hoststep_max':30,'hold_ms_bounds':[50,200]},indent=2)+'\n')
print('created AP95 host-step code, guest delete disabled, no guest build/run before audit')
