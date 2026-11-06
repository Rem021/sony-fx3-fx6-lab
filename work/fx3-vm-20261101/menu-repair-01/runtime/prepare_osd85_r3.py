from pathlib import Path
import json,hashlib,struct,importlib.util,subprocess,plistlib
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap85-osd-software-ring-r3';assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';assert not D.exists();D.mkdir();base=R/'ap85-osd-software-ring-r2/candidate85-r2.json';v=json.loads(base.read_text());b=Path(v['initrd']['path']).read_bytes();entries=[];o=0;changed=[];sha=lambda b:hashlib.sha256(b).hexdigest()
while True:
 f=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];name=b[o+110:o+110+f[11]-1].decode();o=(o+110+f[11]+3)&~3;data=b[o:o+f[6]];o=(o+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='simulation/fx3-osd-headless-v1.so':name='simulation/fx3-osd-headless-v2.so';data=(H/'fx3-osd-headless-v2.so').read_bytes();changed.append(name)
 if name=='init':data=data.replace(b'fx3-osd-headless-v1.so',b'fx3-osd-headless-v2.so');(D/'init-reviewed.sh').write_bytes(data);changed.append(name)
 entries.append((name,f,data))
out=bytearray()
def add(n,f,b,i):
 f=f.copy();z=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(z);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+z);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);t,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());c=next(n for k,n in t['items'] if k=='node' and n['name']=='chosen');c['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in c['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(t,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt.read_bytes())};v['initrd']={'path':str(cp),'sha256':sha(out)};v['scope']+=' AP85r3 headlessv2 corrects original bitmap enum1/7->GPE0,2/8->GPE1 from original1e220c/ef074 tables; native bitmap enum separately recorded, unknown enums rejected, byte capacity/extent/token gates unchanged.';(D/'candidate85-r3.json').write_text(json.dumps(v,indent=2)+'\n');(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base.read_bytes()),'CPIO_changed':changed,'headless_v2_sha256':sha((H/'fx3-osd-headless-v2.so').read_bytes()),'DTB_only_initrd_end_changed':True,'all_other_helpers_unchanged':True,'format_proof':str(R/'ap85-format-domain-proof.json')},indent=2)+'\n');print(D/'candidate85-r3.json')
