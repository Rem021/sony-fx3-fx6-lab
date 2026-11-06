from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util,fcntl,os
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap95-v6-delete-hoststep'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not D.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write_new(p,s):
 with p.open('x') as f:f.write(s)
proof=R.parents[1]/'lead-claude/audits/key-delete-c4/key-delete-proof.json'
p=json.loads(proof.read_text());k=p['keys']['DELETE_C4'];assert k['infra_code']=='0x1f8' and k['down20']=='f801000000000000010000000000000001000000' and k['up20']=='f801000000000000000000000000000001000000'
provider='fx3-rm-empty-provider-v6-delete-hoststep'
write_new(H/(provider+'.c'),'/* AP95 approved DELETE/C4 physical key; all other host-step code unchanged. */\n#define HP95_DELETE_KEY 0x1f8U\n'+(H/'fx3-rm-empty-provider-v5-hoststep.c').read_text())
core=(H/'check-hoststep95-core.c').read_text().replace('unsigned keys[6]={3,0x30,0x15,0x1af,0x1ac,0x1ab}','unsigned keys[7]={3,0x30,0x15,0x1af,0x1ac,0x1ab,0x1f8}').replace('%6','%7').replace(',&c,0)',',&c,0x1f8)').replace('c.key,down,0,p','c.key,down,0x1f8,p').replace('c.key=0x1f8;assert(hp95_validate(0,&c,0x1f8));','c.key=0x1f8;assert(!hp95_validate(0,&c,0x1f8));assert(hp95_validate(0,&c,0));').replace('six_audited_keys','seven_audited_keys').replace('unknown_and_pending_delete_reject','delete_enabled_other_unknown_reject')
core=core.replace('unsigned char p[20],expected[20];','unsigned char p[20],expected[20];unsigned char dd[20]={0xf8,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0};assert(!hp95_pack(0x1f8,1,0x1f8,p)&&!memcmp(p,dd,20));dd[8]=0;assert(!hp95_pack(0x1f8,0,0x1f8,p)&&!memcmp(p,dd,20));')
write_new(H/'check-hoststep95-v6-core.c',core)
worker=(H/'check-hoststep95-worker.c').read_text().replace('fx3-rm-empty-provider-v5-hoststep.c',provider+'.c').replace('table_keys[6]={3,0x30,0x15,0x1af,0x1ac,0x1ab}','table_keys[7]={3,0x30,0x15,0x1af,0x1ac,0x1ab,0x1f8}').replace('val=6;','val=7;').replace('+6*48','+7*48').replace('+6*44','+7*44').replace('sent<2?3:0x1ab','sent<2?3:sent<4?0x1ab:0x1f8').replace('sent==1||sent==3','sent==1||sent==3||sent==5')
worker=worker.replace('assert(idle==9&&sent==4&&freed==4&&*(W*)(page+24)==2&&*(W*)(page+48)==50);W bad[3]={3,0x99,100};','if(idle==9){assert(sent==4&&freed==4&&*(W*)(page+24)==2);W c[3]={3,0x1f8,100};memcpy(page+8,c,12);return 0;}assert(idle==10&&sent==6&&freed==6&&*(W*)(page+24)==3&&*(W*)(page+48)==100);W bad[3]={4,0x99,100};')
worker=worker.replace('sent==4&&freed==4&&holds==2&&idle==9&&failed&&*(W*)(page+24)==2&&*(U*)(page+56)==4','sent==6&&freed==6&&holds==3&&idle==10&&failed&&*(W*)(page+24)==3&&*(U*)(page+56)==6').replace('HOSTSTEP95_WORKER_PASS','HOSTSTEP95_V6_WORKER_PASS delete_exact20B/')
write_new(H/'check-hoststep95-v6-worker.c',worker)
checks=[]
for name in ['check-hoststep95-v6-core','check-hoststep95-v6-worker']:
 args=['clang','-fsanitize=address,undefined','-O1','-g',str(H/(name+'.c')),'-o',str(H/name)]
 c=subprocess.run(args,capture_output=True,text=True);assert not c.returncode,c.stderr
 c=subprocess.run([str(H/name)],capture_output=True,text=True);write_new(H/(name+'.log'),c.stdout+c.stderr);assert not c.returncode,c.stdout+c.stderr;checks.append({'name':name,'exit':c.returncode,'log':str(H/(name+'.log')),'sha256':sha(H/(name+'.log'))})
args=json.loads((H/'fx3-rm-empty-provider-v5-hoststep-build.json').read_text())['args'];args=[a.replace('fx3-rm-empty-provider-v5-hoststep',provider) for a in args];c=subprocess.run(args,capture_output=True,text=True);assert not c.returncode,c.stderr
write_new(H/(provider+'-build.json'),json.dumps({'args':args,'exit':c.returncode,'source_sha256':sha(H/(provider+'.c')),'output_sha256':sha(H/(provider+'.so')),'delete_key':'0x1f8','audit_proof_sha256':sha(proof),'authority':'RUNTIME-HANDOFF.md AP95 / PLAN approved DELETE'},indent=2)+'\n')
# Same host gate as prepared, in a fresh mock fixture; no driver mutation.
sp=importlib.util.spec_from_file_location('g95',R/'gate_input95.py');gmod=importlib.util.module_from_spec(sp);sp.loader.exec_module(gmod)
source=(R/'test_hoststep95.py').read_text().split('# Safe malformed JSON')[0].replace("super().__init__(run)","super().__init__(run,delete_key=0x1f8)").replace('ap95-hoststep-fixture','ap95-v6-hoststep-fixture').replace('(1,0x1f8,100),','').replace('key=list(sorted(m.BASE_KEYS))[(step-2)%6]','key=list(sorted(m.BASE_KEYS|{0x1f8}))[(step-2)%7]').replace("(R/'ap95-hoststep-host-test.json')","(R/'ap95-v6-hoststep-host-test.json')").replace("'pending_delete_reject':True","'approved_delete_enabled':True").replace("'delete_extension_math_not_authorization':True","'delete_authority': 'RUNTIME-HANDOFF AP95'")
write_new(R/'test_hoststep95_v6.py',source);subprocess.run(['python3','-B',str(R/'test_hoststep95_v6.py')],check=True)
base=R/'ap94-r4-object-source-policy/candidate.json';v=json.loads(base.read_text());data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];assert sha(Path(v['dtb']['path']))==v['dtb']['sha256'];off=0;entries=[];changed=[]
member='simulation/fx3-rm-empty-provider-v3-setup.so'
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];name=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name==member:b=(H/(provider+'.so')).read_bytes();changed.append(name)
 entries.append((name,f,b))
assert changed==[member];D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out)
sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)};v['required_markers']=[x.replace('FX3_KEY93_READY','FX3_KEY95_READY') for x in v['required_markers']];v['scope']='AP95 host-stepped button simulation from AP94-r4; only RM input provider body changed to v6. Seven audited physical keys including DELETE/C4 0x1f8; explicit 12B step/key/hold_ms software control command, 30 steps max, 50..200ms; host actually views each independent PNG before deciding next button. No original input table, UI state, callback or parameter writes. GPE19r4/backend5/OSDv6/init and all original assets retained; approximation and lifetime limitations inherited.'
v['host_step_contract']={'authority':'msg_8162589b2b22','delete_key':'0x1f8','whitelist':['0x3','0x30','0x15','0x1af','0x1ac','0x1ab','0x1f8'],'physical':'0x41df00008','bytes':12,'max_steps':30,'hold_ms':[50,200],'audit_proof':str(proof),'audit_sha256':sha(proof)};v['input_gate']={'physical':'0x41df00000','bytes':65536,'host_write_offset':8,'host_write_bytes':12,'magic':'0x3545594b334d5253','navigation_requires_host_visual_confirmation':True,'no_predefined_sequence':True}
(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n');(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base),'changed_CPIO_members':changed,'all_other_member_bodies_and_init_unchanged':True,'DTB_only_initrd_end':True,'host_checks':checks,'audit_sha256':sha(proof),'provider_sha256':sha(H/(provider+'.so')),'candidate_sha256':sha(D/'candidate.json')},indent=2)+'\n')
# Independent archive-body comparison.
from cpio_audit import parse,audit
before,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));after,am=parse(cp);assert list(bm)==list(am);assert [n for n in bm if bm[n]!=am[n]]==[member]
report=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert report['safe_to_unpack'];(D/'cpio-build-audit.json').write_text(json.dumps(report,indent=2)+'\n')
state=json.loads((R/'STATE.json').read_text());state.update({'runtime_owner_orca_session':'orca_session_id:55d86cce-d07a-4447-93a2-e4d69baf2650','runtime_task':'task_7a0872899d3c','runtime_dispatch':'ctx_e2f5ecce8005','phase':'AP95_V6_DELETE_CANDIDATE_READY','work_in_progress':'AP95 seven-key host-step candidate built and host tests passed; pending 300s run','AP95_candidate':str(D/'candidate.json')});(R/'STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n');print(D/'candidate.json')
