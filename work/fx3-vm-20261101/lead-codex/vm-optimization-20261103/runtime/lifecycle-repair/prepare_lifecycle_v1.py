from pathlib import Path
import hashlib, importlib.util, json, plistlib, struct, subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4] / "menu-repair-01/runtime"))
from cpio_audit import parse, audit

D = Path(__file__).resolve().parent
R = D.parents[3] / 'menu-repair-01/runtime'
BASE = R / 'ap105-v1-gpe-perf/candidate.json'
SO = D / 'fx3-osd-lifetime-v3.so'
OUT = D / 'vmopt-20261103-lifecycle-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists()
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert sha(BASE) == '0c4fd429c0c506c285895bdad87fd2bff78babd0db89b597932525b869f7ed7c'
base = json.loads(BASE.read_text())
old = Path(base['initrd']['path'])
assert sha(old) == base['initrd']['sha256']
assert SO.is_file()
data = old.read_bytes()
off = 0
entries = []
changed = []
while True:
    fields = [int(data[off+6+i*8:off+14+i*8],16) for i in range(13)]
    name = data[off+110:off+110+fields[11]-1].decode()
    off = (off+110+fields[11]+3)&~3
    body = data[off:off+fields[6]]
    off = (off+fields[6]+3)&~3
    if name == 'TRAILER!!!': break
    if name == 'simulation/fx3-osd-lifetime-v2.so':
        assert sha(R/'helpers/fx3-osd-lifetime-v2.so') == '1ea2dad0d002ec2cbb8404b5dd1ba03d5a413f4ac7949cd6aafae2f1330d07f5'
        assert hashlib.sha256(body).hexdigest() == '1ea2dad0d002ec2cbb8404b5dd1ba03d5a413f4ac7949cd6aafae2f1330d07f5'
        body = SO.read_bytes()
        changed.append(name)
    entries.append((name,fields,body))
assert changed == ['simulation/fx3-osd-lifetime-v2.so']
OUT.mkdir()
out = bytearray()
def add(name,fields,body,ino):
    fields = fields.copy()
    namebytes = name.encode()+b'\0'
    fields[0],fields[6],fields[11] = ino,len(body),len(namebytes)
    out.extend(b'070701'+''.join(f'{x:08x}' for x in fields).encode()+namebytes)
    out.extend(b'\0'*(-len(out)%4))
    out.extend(body)
    out.extend(b'\0'*(-len(out)%4))
for ino,(name,fields,body) in enumerate(entries,1): add(name,fields,body,ino)
add('TRAILER!!!',[0]*13,b'',len(entries)+1)
cpio = OUT/'guest.cpio'
cpio.write_bytes(out)
spec = importlib.util.spec_from_file_location('fdt',D.parents[3]/'fx3-audit/prepare_virt_dtb.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tree,_,res,meta = module.parse(Path(base['dtb']['path']).read_bytes())
chosen = next(node for kind,node in tree['items'] if kind=='node' and node['name']=='chosen')
chosen['items'] = [(kind,(prop[0],struct.pack('>Q',0x440000000+len(out)))) if kind=='prop' and prop[0]=='linux,initrd-end' else (kind,prop) for kind,prop in chosen['items']]
dtb=OUT/'guest.dtb'
dtb.write_bytes(module.encode(tree,res,meta))
base['initrd']={'path':str(cpio),'sha256':sha(cpio)}
base['dtb']={'path':str(dtb),'sha256':sha(dtb)}
base['scope']='vmopt-20261103-lifecycle-v1: AP105 guest unchanged except passive OSD lifetime observer timer registration moved after its own serial logging and before original allocation; original 5000ms GPE receive, all gates, seed, original firmware and device models unchanged.'
base['ap105_contract']['only_changed_CPIO_member']='simulation/fx3-gpe-observe-v7.so relative to AP103 baseline; lifecycle-v1 additionally changes only simulation/fx3-osd-lifetime-v2.so relative to AP105'
base['lifecycle_v1_contract']={'base':str(BASE),'base_sha256':sha(BASE),'changed_CPIO_member':changed,'old_osd_so_sha256':'1ea2dad0d002ec2cbb8404b5dd1ba03d5a413f4ac7949cd6aafae2f1330d07f5','new_osd_so_sha256':sha(SO),'native_receive_budget_unchanged_ms':5000,'no_new_ack_or_free':True,'original_seed_unchanged':True}
manifest=OUT/'candidate.json'
manifest.write_text(json.dumps(base,indent=2)+'\n')
_,before=parse(old)
_,after=parse(cpio)
assert set(before)==set(after)
actual=[name for name in before if before[name]!=after[name]]
assert actual==changed
assert before['init']==after['init']
report=audit(cpio,D.parents[5]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio')
assert report['safe_to_unpack']
(OUT/'cpio-audit.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'build-receipt.json').write_text(json.dumps({'base':str(BASE),'base_sha256':sha(BASE),'changed_members':actual,'all_other_members_identical':True,'init_identical':True,'dtb_only_initrd_end':True,'old_initrd_sha256':sha(old),'new_initrd_sha256':sha(cpio),'new_dtb_sha256':sha(dtb),'source_sha256':sha(D/'fx3-osd-lifetime-v3.c'),'so_sha256':sha(SO),'guest_not_started':True},indent=2)+'\n')
print(manifest)
