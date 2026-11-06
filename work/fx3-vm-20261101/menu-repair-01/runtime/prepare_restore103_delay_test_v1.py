"""Test-only fixture: delay the frozen shutdown script, change no device model."""
from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
from cpio_audit import parse,audit
R=Path(__file__).resolve().parent;D=R/'ap103-restore-delay-test-v1';assert not D.exists()
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();base=R/'ap103-r2-soft-ldec/candidate.json';v=json.loads(base.read_text());assert sha(base)==json.loads((R/'runs/ap103restore60a-f0a4d75c/receipt.json').read_text())['candidate_sha256'];assert sha(Path(v['initrd']['path']))==v['initrd']['sha256']
data=Path(v['initrd']['path']).read_bytes();off=0;entries=[];old_script=None;member='simulation/fx3-sync100-shutdown.sh'
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16)for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n==member:
  old_script=b;assert b.startswith(b'#!/bin/sh\n');b=b'#!/bin/sh\necho FX3_RESTORE103_TEST_DELAY seconds=5 test_only=1\n/bin/busybox sleep 5\n'+b.split(b'\n',1)[1]
 entries.append((n,f,b))
assert old_script is not None;D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();s=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(s);out.extend(b'070701'+''.join(f'{x:08x}'for x in f).encode()+s);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b)in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out)
sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,_,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items']if k=='node'and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out))))if k=='prop'and q[0]=='linux,initrd-end'else(k,q)for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)}
v['scope']='AP103 cleanup test ONLY: original AP103-r2 candidate, no UI keys, no GPE/device/Backup/model changes; sole CPIO delta adds5s guest delay before original unchanged shutdown script. Validate bounded guest acknowledgment AND exact API16, not fixed3s. Do not promote as UI candidate.'
v['restore103_test_only']={'authority':'msg_45f1419f7e5e','delay_guest_seconds':5,'changed_member':member,'original_script_SHA256':hashlib.sha256(old_script).hexdigest(),'base_manifest':str(base),'base_manifest_SHA256':sha(base),'no_device_or_Backup_model_changes':True}
(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n');_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);assert set(bm)==set(am);diff=[n for n in bm if bm[n]!=am[n]];assert diff==[member];ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');(D/'shutdown-test-reviewed.sh').write_bytes(am[member]);subprocess.run(['/bin/sh','-n',str(D/'shutdown-test-reviewed.sh')],check=True);(D/'build-receipt.json').write_text(json.dumps({'changed_existing_member_bodies':diff,'all_other_members_identical':True,'DTB_only_initrd_end':True,'native_Backup_and_device_models_unchanged':True,'test_only':True},indent=2)+'\n');print(D/'candidate.json')
