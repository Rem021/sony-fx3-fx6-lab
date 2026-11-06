from pathlib import Path
import json,hashlib,struct,subprocess,plistlib,importlib.util
R=Path(__file__).resolve().parent;D=R/'ap78a-timecode-capture-r2';assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';assert not D.exists();D.mkdir();base=R/'ap77-ui-gate-observe/candidate77.json';v=json.loads(base.read_text());sha=lambda b:hashlib.sha256(b).hexdigest();b=Path(v['initrd']['path']).read_bytes();assert sha(b)==v['initrd']['sha256'];entries=[];o=0
while True:
 assert b[o:o+6]==b'070701';f=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];name=b[o+110:o+110+f[11]-1].decode();o=(o+110+f[11]+3)&~3;data=b[o:o+f[6]];o=(o+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='simulation/fx3-ui-gate-v1.so':data=(R/'helpers/fx3-ui-gate-v3.so').read_bytes();entries.append(('simulation/fx3-timecode-capture-v1.so',f,(R/'helpers/fx3-timecode-capture-v1.so').read_bytes()))
 if name=='init':init=data.decode().replace('LD_PRELOAD=/simulation/fx3-capid-v1.so:', 'LD_PRELOAD=/simulation/fx3-capid-v1.so:/simulation/fx3-timecode-capture-v1.so:');data=init.encode()
 entries.append((name,f,data))
out=bytearray()
def add(name,f,data,ino):
 f=f.copy();raw=name.encode()+b'\0';f[0]=ino;f[6]=len(data);f[11]=len(raw);out.extend(b'070701'+''.join(f'{n:08x}' for n in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(data);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,data) in enumerate(entries,1):add(n,f,data,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cpio=D/'guest.cpio';cpio.write_bytes(out)
spec=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);b=Path(v['dtb']['path']).read_bytes();assert sha(b)==v['dtb']['sha256'];tree,props,res,meta=m.parse(b);chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(p[0],struct.pack('>Q',0x440000000+len(out))) if k=='prop' and p[0]=='linux,initrd-end' else p) for k,p in chosen['items']];dtb=D/'guest.dtb';dtb.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dtb),'sha256':sha(dtb.read_bytes())};v['initrd']={'path':str(cpio),'sha256':sha(out)};v['scope']+=' AP78a passive9059000e fullpacket/stack capture +timecode wrapper input sample; no reply added.';v['required_markers']+=['FX3_TIMECODE_CAPTURE'];(D/'candidate78a.json').write_text(json.dumps(v,indent=2)+'\n');(D/'init-reviewed.sh').write_text(init);(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base.read_bytes()),'changes':['capture interposer and gate v3 adds32nd point timecode wrapper input x0 (x1 is output)','no response model change; existing v30 preserved','DTB initrd-end updated'],'initrd':v['initrd'],'dtb':v['dtb']},indent=2)+'\n');print(D/'candidate78a.json')
