from pathlib import Path
import json,hashlib,subprocess,struct,importlib.util,plistlib
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap96-v1-setup-replay-input-diag';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def new(p,s):
 with p.open('x') as f:f.write(s)
authority='msg_48dccc7b7d3d';source=R/'runs/ap95v6r3ui600-3715c225/backup-after-setup.bin';expected='191924ef39d996171ae06ab4ca85e249b655b16db6b68fd1e2ddea45efc60bdc';assert source.stat().st_size==0x221000 and sha(source)==expected
# Same reviewed replay algorithm, pinned to the newly saved setup RAM.
old='fx3-backup-replay-v1';replay='fx3-backup-replay-v2-setup96';s=(H/(old+'.c')).read_text().replace('38cf44637c44d3f47d7b8541dddf7ecc443e262f40dec3aec59f7b94d5b8b38f',expected);new(H/(replay+'.c'),s);args=[a.replace(old,replay) for a in json.loads((H/(old+'-build.json')).read_text())['args']];c=subprocess.run(args,capture_output=True,text=True);assert not c.returncode,c.stderr;new(H/(replay+'-build.json'),json.dumps({'args':args,'exit':c.returncode,'sha256':sha(H/replay),'source_sha256':sha(H/(replay+'.c')),'input_sha256':expected,'authority':authority},indent=2)+'\n')
test=(H/'check-replay89.c').read_text().replace('fx3-backup-replay-v1.c',replay+'.c').replace('REPLAY89_PASS','REPLAY96_PASS');new(H/'check-replay96.c',test);subprocess.run(['clang','-O1','-g','-fsanitize=address,undefined',str(H/'check-replay96.c'),'-o',str(H/'check-replay96')],check=True);c=subprocess.run([str(H/'check-replay96'),str(source),str(R.parent/'original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin')],capture_output=True,text=True);new(H/'check-replay96.log',c.stdout+c.stderr);assert not c.returncode,c.stdout+c.stderr
# Passive diagnostics in our own software-owned page; no new original-state gates.
inc=(H/'fx3-rm-key-gate-v4-hoststep.inc').read_text();diag=r'''
static int key_last_send=-2147483647;static U key_diag_polls,key_diag_last_log,key_diag_last_query;static W key_diag_last_command=0xffffffffU;static int key_diag_queue_exists=-2;
struct key_diag96 {U magic,polls,ns;W tid,stage,failed_value,receiver_seen_value,done,control_step,control_key,hold_ms;int last_send,receiver_queue_exists;W screen_gate_used,screen_observed_in_worker;U receiver_query_ns;};
static void key_diag96(W done,W stage){if(!key_control)return;int saved=*__errno_location();U t=now();W cmd=__atomic_load_n((volatile W*)(key_control+8),__ATOMIC_ACQUIRE);if(t-key_diag_last_query>=1000000000UL){key_diag_queue_exists=nst?alive(0x807a0020U):-2;key_diag_last_query=t;}struct key_diag96 v={0x314741494436394bUL,++key_diag_polls,t,(W)syscall(178),stage,__atomic_load_n(&failed,__ATOMIC_ACQUIRE),__atomic_load_n(&receiver_seen,__ATOMIC_ACQUIRE),done,cmd,*(volatile W*)(key_control+12),*(volatile W*)(key_control+16),key_last_send,key_diag_queue_exists,0,0xffffffffU,key_diag_last_query};memcpy((void*)(key_control+64),&v,sizeof v);if(cmd!=key_diag_last_command||t-key_diag_last_log>=1000000000UL||stage!=1){dprintf(2,"FX3_KEY96_POLL tid=%u poll=%lu stage=%u failed=%u receiver_seen=%u done=%u control_step=%u key=%#x hold_ms=%u last_send=%d native_receiver_queue_exists=%d receiver_query_ns=%lu screen_gate_used=0 screen_from_native_open_log=1 software_diagnostic_only=1 ns=%lu\n",v.tid,v.polls,stage,v.failed_value,v.receiver_seen_value,done,cmd,v.control_key,v.hold_ms,v.last_send,v.receiver_queue_exists,v.receiver_query_ns,t);key_diag_last_log=t;key_diag_last_command=cmd;}*__errno_location()=saved;}
'''
assert 'static int key_send' in inc;inc=inc.replace('static int key_send',diag+'\nstatic int key_send',1).replace('return rc;}','key_last_send=rc;return rc;}',1)
inc=inc.replace('key_control=p;memset(p,0,65536);','key_control=p;int identity_fd=open("/tmp/fx3-keyworker96.identity",0x200c1,0600);if(identity_fd>=0){dprintf(identity_fd,"%lu %lu\\n",syscall(172),syscall(178));close(identity_fd);}memset(p,0,65536);')
inc=inc.replace('for(;;){if(__atomic_load_n(&failed,__ATOMIC_ACQUIRE))return 0;W command=','for(;;){key_diag96(done,1);if(__atomic_load_n(&failed,__ATOMIC_ACQUIRE))return 0;W command=')
inc=inc.replace('W cache=0;if(!key_cache','key_diag96(done,3);W cache=0;if(!key_cache').replace('U start=now();if(key_send','U start=now();key_diag96(done,4);if(key_send').replace('U down=now();','key_diag96(done,5);U down=now();').replace('if(key_send(c.step,c.key,0))','key_diag96(done,6);if(key_send(c.step,c.key,0))').replace('if(wait_rc){event','key_diag96(done,7);if(wait_rc){event').replace('FX3_KEY95_READY','FX3_KEY96_READY')
new(H/'fx3-rm-key-gate-v5-diag96.inc',inc)
provider='fx3-rm-empty-provider-v7-diag96';s=(H/'fx3-rm-empty-provider-v6-delete-hoststep.c').read_text().replace('fx3-rm-key-gate-v4-hoststep.inc','fx3-rm-key-gate-v5-diag96.inc');new(H/(provider+'.c'),s);args=[a.replace('fx3-rm-empty-provider-v6-delete-hoststep',provider) for a in json.loads((H/'fx3-rm-empty-provider-v6-delete-hoststep-build.json').read_text())['args']];c=subprocess.run(args,capture_output=True,text=True);assert not c.returncode,c.stderr;new(H/(provider+'-build.json'),json.dumps({'args':args,'exit':c.returncode,'source_sha256':sha(H/(provider+'.c')),'output_sha256':sha(H/(provider+'.so')),'only_new_control_page_diag_and_optional_tmp_identity_file':True,'screen_gate_used':False,'authority':authority},indent=2)+'\n')
# Actual worker passes thirteen commands, including MENU after the old boundary.
s=(H/'check-hoststep95-v6-worker.c').read_text().replace('fx3-rm-empty-provider-v6-delete-hoststep.c',provider+'.c').replace('assert(fd==1||fd==2);','assert(fd==1||fd==2);').replace('assert(0);return -1;}\nlong fake_read','if(!strcmp(p,"/tmp/fx3-keyworker96.identity"))return -1;assert(0);return -1;}\nlong fake_read')
s=s.replace('W expected_key=sent<2?3:sent<4?0x1ab:0x1f8;','W schedule[13]={3,0x1ac,0x1ac,0x1f8,0x1ac,0x1ac,0x1ac,0x1ac,0x30,0x1ac,0x1ac,0x1ac,0x1ab};W expected_key=schedule[sent/2];')
a=s.index('int fake_sleep(');z=s.index('int main(void)',a);s=s[:a]+'''int fake_sleep(unsigned micro){nano+=(U)micro*1000;if(micro==100000){assert(sent%2==1);holds++;return 0;}assert(micro==5000);idle++;if(idle<=3){assert(!sent);return 0;}W done=*(W*)(page+24);assert(sent==done*2&&freed==sent);W schedule[13]={3,0x1ac,0x1ac,0x1f8,0x1ac,0x1ac,0x1ac,0x1ac,0x30,0x1ac,0x1ac,0x1ac,0x1ab};W c[3]={done+1,done<13?schedule[done]:0x99,100};memcpy(page+8,c,12);return 0;}\n'''+s[z:]
s=s.replace('sent==6&&freed==6&&holds==3&&idle==10&&failed&&*(W*)(page+24)==3&&*(U*)(page+56)==6','sent==26&&freed==26&&holds==13&&failed&&*(W*)(page+24)==13&&*(U*)(page+56)==26').replace('HOSTSTEP95_V6_WORKER_PASS','HOSTSTEP96_WORKER_PASS 13commands_MENU_after12/');new(H/'check-hoststep96-worker.c',s);subprocess.run(['clang','-O1','-g','-fsanitize=address,undefined',str(H/'check-hoststep96-worker.c'),'-o',str(H/'check-hoststep96-worker')],check=True);c=subprocess.run([str(H/'check-hoststep96-worker')],capture_output=True,text=True);new(H/'check-hoststep96-worker.log',c.stdout+c.stderr);assert not c.returncode,c.stdout+c.stderr
# New observer version; input algorithm unchanged, fresh names and authority.
for oldn,newn in [('gate_input95.py','gate_input96.py'),('key_readback95.py','key_readback96.py'),('run_candidate95_v2.py','run_candidate96.py'),('ap95_decide_v1.py','ap96_decide_v1.py')]:
 s=(R/oldn).read_text().replace('gate_input95','gate_input96').replace('key_readback95','key_readback96').replace('ap95-','ap96-').replace('FX3_KEY95_READY','FX3_KEY96_READY').replace('msg_8162589b2b22',authority).replace("'size':64,'name':'ap96-control-final.bin'","'size':256,'name':'ap96-control-final.bin'")
 # An already-served read-only request is preserved but does not gate later steps.
 if newn=='run_candidate96.py':s=s.replace("if not re.fullmatch(r'[a-z0-9-]{1,40}',label) or request.get('step')!=host_step:","if not re.fullmatch(r'[a-z0-9-]{1,40}',label) or (request.get('step')!=host_step and not (run/('ap96-'+label+'.json')).exists()):")
 new(R/newn,s);compile(s,str(R/newn),'exec')
base=R/'ap95-v6-delete-hoststep/candidate.json';v=json.loads(base.read_text());data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];off=0;entries=[];changed=[]
replacement={'simulation/fx3-rm-empty-provider-v3-setup.so':(H/(provider+'.so')).read_bytes(),'simulation/fx3-backup-replay-v1':(H/replay).read_bytes(),'simulation/ap89-backup-ram.bin':source.read_bytes()}
proc=r''' if [ -r /tmp/fx3-keyworker96.identity ]; then
  read key96_pid key96_tid < /tmp/fx3-keyworker96.identity
  echo FX3_KEY96_THREAD_BEGIN pid=$key96_pid tid=$key96_tid
  /bin/busybox cat /proc/uptime
  if [ -r /proc/$key96_pid/task/$key96_tid/status ]; then
   /bin/busybox grep -E '^(Name|State|Tgid|Pid|PPid|Threads|voluntary_ctxt_switches|nonvoluntary_ctxt_switches):' /proc/$key96_pid/task/$key96_tid/status
   echo FX3_KEY96_THREAD_WCHAN
   /bin/busybox cat /proc/$key96_pid/task/$key96_tid/wchan
   echo FX3_KEY96_THREAD_STACK
   /bin/busybox cat /proc/$key96_pid/task/$key96_tid/stack
  else echo FX3_KEY96_THREAD_ABSENT; fi
  echo FX3_KEY96_THREAD_END
 fi
'''
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];name=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name in replacement:b=replacement[name];changed.append(name)
 if name=='init':
  s=b.decode();needle=' for im_pid in $(/bin/busybox pidof im.elf); do';assert needle in s;s=s.replace(needle,proc+needle);b=s.encode();changed.append(name)
 entries.append((name,f,b))
assert set(changed)==set(replacement)|{'init'};D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out)
sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)};v['backup_replay']['source']=str(source);v['backup_replay']['sha256']=expected;v['required_markers']=[x.replace('FX3_KEY95_READY','FX3_KEY96_READY') for x in v['required_markers'] if x not in ['FX3_GPE_NATIVE_TARGET','FX3_GPE_CHILD_REGISTER','approx_stretch=nearest_v2']]+['FX3_KEY96_POLL','FX3_KEY96_THREAD_BEGIN'];v['scope']='AP96 Lead msg_48dccc7b7d3d: replay exact AP95 preMENU after-setup raw RAM after native backup load before AP; original bounded replay/rollback algorithm with new fixed SHA and independent preAP host QMP SHA unchanged. Same seven-key hoststep contract; new worker passive own-page poll diagnostics and independent init proc thread/status/stack/wchan. No original key tables, UI state, thresholds, callbacks or protocol changes. GPE19r4/backend5/OSDv6 retained. Start stable then MENU step1, actualPNG decides each nextkey;600s.';v['host_step_contract']['authority']=authority;v['input_diagnostics']={'software_page':'0x41df00040','record_bytes':104,'each_poll_latest_counter_and_fields':True,'serial_transition_and_1s_sample':True,'native_receiver_queue_query_interval_seconds':1,'screen_gate_used':False,'screen_correlates_original_open_log':True,'thread_proc_independent_of_worker':True};(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n')
from cpio_audit import parse,audit
_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);assert [n for n in bm if bm[n]!=am[n]]==[n for n,_,_ in entries if n in changed];ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base),'changed_member_bodies':changed,'all_other_members_unchanged':True,'DTB_only_initrd_end':True,'source_backup':str(source),'source_sha256':expected,'replay_host_ASan_UBSan':'PASS','actual_worker_13commands_MENU_after12_ASan_UBSan':'PASS','new_gate_semantics':False,'authority':authority},indent=2)+'\n');print(D/'candidate.json')
