from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap102-r2-offlock-serial';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();base=R/'ap102-v1-observe/candidate.json';v=json.loads(base.read_text());assert sha(base)=='4d9293b3fd47ca3ca84020c0eda2eb40fc2ec2614d40b5f146880b5d6b7f2c19'
replacements={'simulation/fx3-gpe-observe-v7.so':'fx3-gpe-observe-v24-serial102.so'}
for name in replacements.values():assert sha(H/name)==json.loads((H/(Path(name).stem+'-build.json')).read_text())['output_sha256']
assert 'AP102_R2_OFFLOCK_PROT_NONE_COPY_SHA_HIST_ERRNO_BOUNDED_WAIT_PASS' in (H/'check-observe102-r2-v1.log').read_text()
data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];off=0;entries=[];changed=[]
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n in replacements:b=(H/replacements[n]).read_bytes();changed.append(n)
 entries.append((n,f,b))
assert set(changed)==set(replacements);D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out)
sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)}
v['host_step_contract']['authority']='msg_7eb2cdbf663a';v['ap102_contract']={'authority':['msg_451e29d2c9b9','msg_7eb2cdbf663a','msg_2c7707dd92c8','msg_398ba0ce872e'],'original_proof':{'path':str(R/'ap102-observer-original-proof-v1.json'),'sha256':sha(R/'ap102-observer-original-proof-v1.json')},'baseline':str(base),'baseline_SHA256':sha(base),'device_protocols_Backup_pixel_math_native_file_unchanged':True,'adapter_serialization_change':'bounded wait up to500ms per msg_398ba0ce872e','observer_hash_after_raster_unlock':True,'new_passive_observers':replacements,'no_new_protocol_responses':True,'no_direct_flush':True,'stages':['native language change then standby idle >=60 seconds','if no file language save native date same-value confirmation']}
v['scope']='AP102-r2 approved by msg_398ba0ce872e: same original AP101-r4 native Backup seed and all device protocol/Backup/date/pixel backend models. GPE adapter command_lock now waits bounded <=500ms, logs elapsed time, rejects ontimeout; original FIFO order and pixel math unchanged. Original raster/lifecycle guards only hold bounded copies of source and destination before/after; SHA256/histograms read private observer copies after raster unlock. No new device reply, allocator, direct flush, setter or parameter writes. StageA native language change and standby idle>=60s; StageB same-value native date reconfirmation if necessary. QEMU TCG original kernel probes and full GPE/OSD/texture evidence retained.'
(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n')
from cpio_audit import parse,audit
_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);assert set(bm)==set(am);diff=[n for n in bm if bm[n]!=am[n]];assert diff==changed;assert hashlib.sha256(am['setting/Backup.bin']).hexdigest()==v['native_Backup_seed']['sha256'];ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');(D/'init-reviewed.sh').write_bytes(am['init']);subprocess.run(['/bin/sh','-n',str(D/'init-reviewed.sh')],check=True)
(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base),'changed_member_bodies':diff,'all_other_members_unchanged':True,'DTB_only_initrd_end':True,'native_Backup_seed_unchanged':True,'device_protocols_and_pixel_backend_unchanged':True,'approved_adapter_lock_wait':'msg_398ba0ce872e','backend_v8_source_SHA256':sha(H/'fx3-gpe-backend-v8.c'),'passive_sha_hist_host_ASan_UBSan':sha(H/'check-texture102-v1.log')},indent=2)+'\n');print(D/'candidate.json')
