"""Create one cold-start candidate from a fixed guest O_RDONLY generation-4 copy.
Run only after lifecycle-v1 QEMU exit, API16 restoration, both locks released, and full review.
"""
from pathlib import Path
import hashlib, importlib.util, json, plistlib, struct, subprocess, sys
D=Path(__file__).resolve().parent
R=D.parents[3]/'menu-repair-01/runtime'
sys.path.insert(0,str(R))
from cpio_audit import parse,audit
BASE=D/'vmopt-20261103-lifecycle-v1/candidate.json'
SOURCE=D/'runs/vmopt-20261103-lifecycle-guest18-1da10e34/Backup-native-file-date-closed-idle60.bin'
OUT=D/'vmopt-20261103-reload-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists()
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert sha(SOURCE)=='92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f'
receipt=json.loads((D/'runs/vmopt-20261103-lifecycle-guest18-1da10e34/receipt.json').read_text())
assert receipt['process_reaped'] and receipt['qemu_exit']==0 and receipt['inputs_unchanged'] and not receipt['host_observer_error'] and not receipt['guest_exception_markers']
assert receipt['restore103']['passed']
state=json.loads((D/'vmopt-20261103-STATE.json').read_text())
assert state['phase']=='RUN_COMPLETE_REVIEW_PENDING' and all(lock['status']=='released' for lock in state['locks'])
source=SOURCE.read_bytes()
assert len(source)==2229740 and source[0x8dd85]==0 and source[0x9100c]==0
bank_checks=[]
for off in (0,0xd2000):
 a,b=struct.unpack_from('<II',source,off+24);n=a+b
 c=(sum(source[off:off+n])-sum(source[off+32:off+36]))&0xffffffff
 expected=struct.unpack_from('<I',source,off+32)[0]
 assert c==expected
 bank_checks.append({'offset':off,'bytes':n,'checksum':expected,'checksum_valid':True})
manifest=json.loads(BASE.read_text())
old=Path(manifest['initrd']['path'])
assert sha(old)==manifest['initrd']['sha256']
data=old.read_bytes();off=0;entries=[];changed=[]
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)]
 name=data[off+110:off+110+f[11]-1].decode()
 off=(off+110+f[11]+3)&~3
 body=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='setting/Backup.bin':
  assert hashlib.sha256(body).hexdigest()==manifest['native_Backup_seed']['sha256']
  body=source;changed.append(name)
 entries.append((name,f,body))
assert changed==['setting/Backup.bin']
OUT.mkdir()
copy=OUT/'Backup-generation4-fixed.bin';copy.write_bytes(source);assert sha(copy)==sha(SOURCE)
out=bytearray()
def add(name,f,body,ino):
 f=f.copy();n=name.encode()+b'\0';f[0],f[6],f[11]=ino,len(body),len(n)
 out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+n);out.extend(b'\0'*(-len(out)%4))
 out.extend(body);out.extend(b'\0'*(-len(out)%4))
for ino,(name,f,body) in enumerate(entries,1):add(name,f,body,ino)
add('TRAILER!!!',[0]*13,b'',len(entries)+1)
cpio=OUT/'guest.cpio';cpio.write_bytes(out)
spec=importlib.util.spec_from_file_location('fdt',D.parents[3]/'fx3-audit/prepare_virt_dtb.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
tree,_,res,meta=module.parse(Path(manifest['dtb']['path']).read_bytes())
chosen=next(node for kind,node in tree['items'] if kind=='node' and node['name']=='chosen')
chosen['items']=[(kind,(prop[0],struct.pack('>Q',0x440000000+len(out)))) if kind=='prop' and prop[0]=='linux,initrd-end' else (kind,prop) for kind,prop in chosen['items']]
dtb=OUT/'guest.dtb';dtb.write_bytes(module.encode(tree,res,meta))
manifest['native_Backup_seed']={'path':str(copy),'sha256':sha(copy),'bytes':len(source),'native_bank_checks':bank_checks}
manifest['initrd']={'path':str(cpio),'sha256':sha(cpio)}
manifest['dtb']={'path':str(dtb),'sha256':sha(dtb)}
manifest['scope']='vmopt-20261103-reload-v1: controlled cold restart with exact O_RDONLY generation-4 Backup copy from lifecycle-v1; no host RAM replay; original seed untouched; all other AP105/lifecycle observer bytes unchanged.'
manifest['cold_reload_contract']={'base':str(BASE),'base_sha256':sha(BASE),'source_run':str(SOURCE.parent),'source_O_RDONLY_copy':str(SOURCE),'source_sha256':sha(SOURCE),'fixed_copy':str(copy),'fixed_sha256':sha(copy),'generation':4,'only_changed_CPIO_member':changed,'original_seed_untouched':True,'no_host_RAM_replay':True,'prior_run_exited_reaped_restored_locks_released':True}
(OUT/'candidate.json').write_text(json.dumps(manifest,indent=2)+'\n')
_,before=parse(old);_,after=parse(cpio)
assert set(before)==set(after)
actual=[name for name in before if before[name]!=after[name]]
assert actual==changed and before['init']==after['init']
report=audit(cpio,D.parents[5]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio')
assert report['safe_to_unpack']
(OUT/'cpio-audit.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'build-receipt.json').write_text(json.dumps({'source_run':str(SOURCE.parent),'source_O_RDONLY_copy':str(SOURCE),'source_sha256':sha(SOURCE),'source_generation':4,'bank_checks':bank_checks,'fixed_copy_sha256':sha(copy),'changed_members':actual,'all_other_CPIO_members_identical':True,'init_identical':True,'dtb_only_initrd_end':True,'new_candidate_sha256':sha(OUT/'candidate.json'),'guest_not_started':True},indent=2)+'\n')
print(OUT/'candidate.json')
