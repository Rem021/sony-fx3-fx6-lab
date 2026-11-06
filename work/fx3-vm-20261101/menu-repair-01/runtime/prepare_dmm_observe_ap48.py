from pathlib import Path
import json,hashlib,struct,subprocess,plistlib,importlib.util
R=Path(__file__).resolve().parent;D=R/'ap48-dmm-observe';assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';assert not D.exists();D.mkdir();base=R/'ap47-hdmi-photo/candidate47.json';v=json.loads(base.read_text());sha=lambda b:hashlib.sha256(b).hexdigest();b=Path(v['initrd']['path']).read_bytes();assert sha(b)==v['initrd']['sha256'];entries=[];o=0
while True:
 assert b[o:o+6]==b'070701';f=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];name=b[o+110:o+110+f[11]-1].decode();o=(o+110+f[11]+3)&~3;data=b[o:o+f[6]];o=(o+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='simulation/fx3-capid-v1.so':data=(R/'helpers/fx3-capid-v8.so').read_bytes()
 if name=='simulation/fx3-hdmi-registration-v1.so':data=(R/'helpers/fx3-hdmi-registration-v3.so').read_bytes()
 if name=='init':
  init=data.decode();data=init.encode()
 entries.append((name,f,data))
out=bytearray()
def add(name,f,data,ino):
 f=f.copy();raw=name.encode()+b'\0';f[0]=ino;f[6]=len(data);f[11]=len(raw);out.extend(b'070701'+''.join(f'{n:08x}' for n in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(data);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,data) in enumerate(entries,1):add(n,f,data,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cpio=D/'guest.cpio';cpio.write_bytes(out)
spec=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);b=Path(v['dtb']['path']).read_bytes();assert sha(b)==v['dtb']['sha256'];tree,props,res,meta=m.parse(b);chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(p[0],struct.pack('>Q',0x440000000+len(out))) if k=='prop' and p[0]=='linux,initrd-end' else p) for k,p in chosen['items']];dtb=D/'guest.dtb';dtb.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dtb),'sha256':sha(dtb.read_bytes())};v['initrd']={'path':str(cpio),'sha256':sha(out)};v['scope']+='  PassiveboundedDMM9061003c request capture, originaldelegation unmodified.';v['required_markers']=[x for x in v['required_markers'] if x!='FX3_BT_ERROR']+['FX3_PROVIDER_REQUEST destination=0x9061003c'];(D/'candidate48.json').write_text(json.dumps(v,indent=2)+'\n');(D/'init-reviewed.sh').write_text(init);(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base.read_bytes()),'changes':['Aggregatev8 passive bounded9061003c request observation; no completion added','DTB actual initrd-end'],'original_assets_unchanged':True,'CPIO':v['initrd'],'DTB':v['dtb']},indent=2)+'\n');print(D/'candidate48.json')
