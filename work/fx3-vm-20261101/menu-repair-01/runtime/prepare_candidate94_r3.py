from pathlib import Path
import json,hashlib,struct,importlib.util,subprocess,plistlib
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap94-r3-nearest-v2';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';base=R/'ap94-r2-guard-diagnostics/candidate.json';v=json.loads(base.read_text());sha=lambda b:hashlib.sha256(b).hexdigest();data=Path(v['initrd']['path']).read_bytes();assert sha(data)==v['initrd']['sha256'];off=0;entries=[];changed=[]
replacements={'simulation/fx3-gpe-observe-v7.so':'fx3-gpe-observe-v19r3-nearest-v2.so'}
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];name=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name in replacements:b=(H/replacements[name]).read_bytes();changed.append(name)
 entries.append((name,f,b))
assert set(changed)==set(replacements);D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt.read_bytes())};v['initrd']={'path':str(cp),'sha256':sha(out)};v['required_markers']+=['FX3_OSD_FRAME_TARGET_VALID'];v['scope']='AP94-r3 Lead msg_c030a5a3da12 approved nearest_v2 pixel-center sampler for existing fmt0/selector0/K255/flags0/rotation0/zero-coordinates/fullclip/reg7600 overwrite subset, any positive bounded source/destination dimensions incl anisotropic and downscale. All parent/child/screen/OSD/FIFO/completion/input/RM/compaction guards unchanged; hardware sampling precision unproven. Same manually confirmed English/setup/MENU script, 300s.'
v['required_markers']=list(dict.fromkeys(v['required_markers']+['approx_stretch=nearest_v2']))
(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n');(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base.read_bytes()),'changed_CPIO_members':changed,'init_unchanged':True,'RM_core_and_input_plan_unchanged':True,'originals_unchanged':True,'DTB_only_initrd_end_changed':True,'helpers':{n:sha((H/n).read_bytes()) for n in replacements.values()},'host_checks':str(R/'ap94-r3-nearest-v2-host-check.json'),'authority':['msg_c030a5a3da12']},indent=2)+'\n');print(D/'candidate.json')
