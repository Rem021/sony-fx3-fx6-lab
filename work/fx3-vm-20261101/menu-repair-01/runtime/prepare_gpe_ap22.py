"""Minimal AP19 derivative; exact existing newc fields retained except ino/size."""
from pathlib import Path
import hashlib,json,struct,subprocess,plistlib,importlib.util
R=Path(__file__).resolve().parent;D=R/'ap22-gpe-setup'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not D.exists();D.mkdir()
base=R/'ap19-utimer/candidate19.json';v=json.loads(base.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
p=Path(v['initrd']['path']);b=p.read_bytes();assert sha(b)==v['initrd']['sha256'];entries=[];o=0
while True:
 assert b[o:o+6]==b'070701';fields=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];name=b[o+110:o+110+fields[11]-1].decode();o=(o+110+fields[11]+3)&~3;data=b[o:o+fields[6]];o=(o+fields[6]+3)&~3
 if name=='TRAILER!!!':break
 entries.append([name,fields,data])
helper=R/'helpers/fx3-gpe-observe-v3.so';add=['simulation/fx3-gpe-observe-v3.so',[0,0o100755,0,0,1,0,0,0,0,0,0,0,0],helper.read_bytes()];entries.append(add)
for name,f,data in entries:
 if name=='init':
  init=data.decode();assert 'LD_PRELOAD=/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so' in init
  init=init.replace('LD_PRELOAD=/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so','LD_PRELOAD=/simulation/fx3-gpe-observe-v3.so:/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so')
  init=init.replace('  echo FX3_AP_SNAPSHOT_${turn}_END', '  /bin/busybox cat /proc/udm/dmm_units /proc/udm/dmm_extents\n  echo FX3_AP_SNAPSHOT_${turn}_END')
  init=init.replace(' echo FX3_AP_NATURAL_BOOTIN_BEGIN',' echo FX3_DMM_PROC_BEGIN\n /bin/busybox ls -l /proc/osal /proc/udm/dmm_info\n /bin/busybox cat /proc/udm/dmm_info /proc/udm/dmm_units /proc/udm/dmm_extents /proc/udm/dmm_reserve\n echo FX3_DMM_PROC_END\n echo FX3_AP_NATURAL_BOOTIN_BEGIN')
  data=init.encode()
  entries[next(i for i,e in enumerate(entries) if e[0]=='init')][2]=data
out=bytearray()
def append(name,fields,data,ino):
 fields=fields.copy();raw=name.encode()+b'\0';fields[0]=ino;fields[6]=len(data);fields[11]=len(raw)
 out.extend(b'070701'+''.join(f'{n:08x}' for n in fields).encode()+raw);out.extend(b'\0'*((-len(out))%4));out.extend(data);out.extend(b'\0'*((-len(out))%4))
for ino,(name,f,data) in enumerate(entries,1):append(name,f,data,ino)
append('TRAILER!!!',[0]*13,b'',len(entries)+1);archive=D/'guest.cpio';archive.write_bytes(out)
spec=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);p=Path(v['dtb']['path']);b=p.read_bytes();assert sha(b)==v['dtb']['sha256'];tree,props,res,meta=m.parse(b);chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(p[0],struct.pack('>Q',0x440000000+len(out))) if k=='prop' and p[0]=='linux,initrd-end' else p) for k,p in chosen['items']];dtb=D/'guest.dtb';dtb.write_bytes(m.encode(tree,res,meta))
v['dtb']={'path':str(dtb),'sha256':sha(dtb.read_bytes())};v['initrd']={'path':str(archive),'sha256':sha(out)};v['scope']+=' FX3 GPE diagnostic binding only: original command FIFO, five symbol-derived slots, unsupported workers return5 without writes/callbacks. No software raster acceptance.';v['required_markers']+=['FX3_GPE_BOUND count=5'];(D/'candidate22.json').write_text(json.dumps(v,indent=2)+'\n');(D/'init-reviewed.sh').write_text(init)
(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base.read_bytes()),'helper_sha256':sha(helper.read_bytes()),'helper_source_sha256':sha(helper.with_suffix('.c').read_bytes()),'entries':len(entries),'changes':['init preloads diagnostic GPE','original DMM proc read','one helper added','DTB chosen initrd-end only'],'cpio':v['initrd'],'dtb':v['dtb']},indent=2)+'\n');print(D/'candidate22.json')
