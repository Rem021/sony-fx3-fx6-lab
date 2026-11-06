from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap102-v1-observe';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();base=R/'ap101-r4-repeat-tile/candidate.json';v=json.loads(base.read_text());assert sha(base)=='fdcd0a3cf614473e233d0d39df78a47765f9eff433b9a0e5d67e9253f943a1f9'
replacements={'simulation/fx3-preset-context-v2-screen.so':'fx3-preset-context-v6-save102.so','simulation/fx3-backup-return-v1.so':'fx3-backup-return-v5-save102.so','simulation/fx3-gpe-observe-v7.so':'fx3-gpe-observe-v23-capture102.so','simulation/fx3-osd-headless-v5.so':'fx3-osd-headless-v7-observe102.so'}
for name in replacements.values():assert sha(H/name)==json.loads((H/(Path(name).stem+'-build.json')).read_text())['output_sha256']
assert 'AP102_TEXTURE_SHA_ROWS_HIST_EMPTY_ERRNO_PASS' in (H/'check-texture102-v1.log').read_text()
data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];off=0;entries=[];changed=[]
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n in replacements:b=(H/replacements[n]).read_bytes();changed.append(n)
 if n=='init':
  old=b' echo FX3_OSAL_UIPC_BSS=';assert old in b;b=b.replace(old,b' echo FX3_BACKUP102_TEXT_BASE=$(/bin/busybox cat /sys/module/backup/sections/.text)\n'+old,1);changed.append(n)
 entries.append((n,f,b))
assert set(changed)==set(replacements)|{'init'};D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out)
sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)}
v['host_step_contract']['authority']='msg_7eb2cdbf663a';v['ap102_contract']={'authority':['msg_451e29d2c9b9','msg_7eb2cdbf663a','msg_2c7707dd92c8'],'original_proof':{'path':str(R/'ap102-observer-original-proof-v1.json'),'sha256':sha(R/'ap102-observer-original-proof-v1.json')},'baseline':str(base),'baseline_SHA256':sha(base),'original_models_and_native_file_unchanged':True,'new_passive_observers':replacements,'no_new_protocol_responses':True,'no_direct_flush':True,'stages':['native language change then standby idle >=60 seconds','if no file language save native date same-value confirmation']}
v['scope']+=' AP102: new passive user language/idle probes and native subsystem API return wrapper; QEMU TCG Z1 kernel breakpoint reads/one-original-instruction steps; source texture SHA/histogram and destination before/after SHA within unchanged validated v8 raster model; per-commit OSD identity/descriptor/GPE observation. No new reply/model/allocator/flush/parameter writes.'
(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n')
from cpio_audit import parse,audit
_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);assert set(bm)==set(am);diff=[n for n in bm if bm[n]!=am[n]];assert diff==changed;assert hashlib.sha256(am['setting/Backup.bin']).hexdigest()==v['native_Backup_seed']['sha256'];ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');(D/'init-reviewed.sh').write_bytes(am['init']);subprocess.run(['/bin/sh','-n',str(D/'init-reviewed.sh')],check=True)
(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base),'changed_member_bodies':diff,'all_other_members_unchanged':True,'DTB_only_initrd_end':True,'native_Backup_seed_unchanged':True,'models_unchanged_observers_only':True,'backend_v8_source_SHA256':sha(H/'fx3-gpe-backend-v8.c'),'passive_sha_hist_host_ASan_UBSan':sha(H/'check-texture102-v1.log')},indent=2)+'\n');print(D/'candidate.json')
