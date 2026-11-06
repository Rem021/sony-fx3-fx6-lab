from pathlib import Path
import json,hashlib,struct,subprocess,plistlib,importlib.util
R=Path(__file__).resolve().parent;D=R/'ap41-capid-storage';assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';assert not D.exists();D.mkdir();base=R/'ap40-kikilog/candidate40.json';v=json.loads(base.read_text());sha=lambda b:hashlib.sha256(b).hexdigest();b=Path(v['initrd']['path']).read_bytes();assert sha(b)==v['initrd']['sha256'];entries=[];o=0
while True:
 assert b[o:o+6]==b'070701';f=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];name=b[o+110:o+110+f[11]-1].decode();o=(o+110+f[11]+3)&~3;data=b[o:o+f[6]];o=(o+f[6]+3)&~3
 if name=='TRAILER!!!':break

 if name=='init':
  init=data.decode().replace('FX3_HDMI_REGISTRATION=software-v1 ','FX3_CAPID_STORAGE=reserved-v1 FX3_HDMI_REGISTRATION=software-v1 ').replace('LD_PRELOAD=','LD_PRELOAD=/simulation/fx3-capid-v1.so:').replace(' echo FX3_AP_NATURAL_BOOTIN_BEGIN',' /bin/busybox cat /proc/iomem\n echo FX3_AP_NATURAL_BOOTIN_BEGIN');data=init.encode()
 entries.append((name,f,data))
entries.append(('simulation/fx3-capid-v1.so',[0,0o100755,0,0,1,0,0,0,0,0,0,0,0],(R/'helpers/fx3-capid-v1.so').read_bytes()));out=bytearray()
def add(name,f,data,ino):
 f=f.copy();raw=name.encode()+b'\0';f[0]=ino;f[6]=len(data);f[11]=len(raw);out.extend(b'070701'+''.join(f'{n:08x}' for n in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(data);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,data) in enumerate(entries,1):add(n,f,data,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cpio=D/'guest.cpio';cpio.write_bytes(out)
spec=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);b=Path(v['dtb']['path']).read_bytes();assert sha(b)==v['dtb']['sha256'];tree,props,res,meta=m.parse(b);chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(p[0],struct.pack('>Q',0x440000000+len(out))) if k=='prop' and p[0]=='linux,initrd-end' else p) for k,p in chosen['items']];# Reserve a private gap outside all original memrsv and current FDT extents.
phys=0x41d800000;extent=0x10000;oldres=[struct.unpack_from('>QQ',res,i) for i in range(0,len(res)-16,16)];boot=next(p[1].rstrip(b'\0').decode() for k,p in chosen['items'] if k=='prop' and p[0]=='bootargs')
import re
ranges=oldres+[(int(a,16),int(n,16)) for n,a in re.findall(r'memrsv=(0x[0-9a-fA-F]+)@(0x[0-9a-fA-F]+)',boot)]
assert all(phys+extent<=a or a+n<=phys for a,n in ranges),(hex(phys),ranges)
assert 0x400000000<=phys and phys+extent<=0x540000000
res=res[:-16]+struct.pack('>QQ',phys,extent)+b'\0'*16
chosen['items']=[(k,(p[0],(boot+' memrsv=0x00010000@0x41d800000:uc').encode()+b'\0') if k=='prop' and p[0]=='bootargs' else p) for k,p in chosen['items']]
(D/'exclusive-reservation.json').write_text(json.dumps({'physical':hex(phys),'bytes':extent,'original_ranges_checked':[[hex(a),hex(n)] for a,n in ranges],'nonoverlap':True,'policy':'dedicated virtual CAPID backing; original DMM and kernel allocation excluded by FDT+native memrsv. No CP execution.'},indent=2)+'\n')
dtb=D/'guest.dtb';dtb.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dtb),'sha256':sha(dtb.read_bytes())};v['initrd']={'path':str(cpio),'sha256':sha(out)};v['scope']='Original FX3 natural boot with original UIPC/Backup/timer/DMM/UPM/date/GPIO5/nativeBusPower/Kikilog. Explicit virtual HDMI registration, empty Bluetooth records, CP control unsupported, GPE request-capture diagnostics. CAPID storage-only profile with exclusive41d800000/64KiB reservation, native messages/leases and rollback. No originalCP/capture/realdevices or UI acceptance.';v['required_markers']=[x for x in v['required_markers'] if x!='FX3_BT_ERROR']+['FX3_CAPID_BIND','FX3_CAPID_COMMIT'];(D/'candidate41.json').write_text(json.dumps(v,indent=2)+'\n');(D/'init-reviewed.sh').write_text(init);(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base.read_bytes()),'changes':['add explicit CAPID native interposer','lazy exclusive guest claim and mapped storage, native transport','DTB initrd-end and exclusive physical reservation'],'original_assets_unchanged':True,'CPIO':v['initrd'],'DTB':v['dtb']},indent=2)+'\n');print(D/'candidate41.json')
