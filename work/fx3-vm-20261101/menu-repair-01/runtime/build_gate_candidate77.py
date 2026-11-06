from pathlib import Path
import json,hashlib,struct,subprocess,plistlib,importlib.util,re
R=Path(__file__).resolve().parent;D=R/'ap77-ui-gate-observe';assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';assert not D.exists();D.mkdir();base=R/'ap76-adf-file-icdt-r3/candidate76.json';v=json.loads(base.read_text());sha=lambda b:hashlib.sha256(b).hexdigest();b=Path(v['initrd']['path']).read_bytes();assert sha(b)==v['initrd']['sha256'];entries=[];o=0
while True:
 assert b[o:o+6]==b'070701';f=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];name=b[o+110:o+110+f[11]-1].decode();o=(o+110+f[11]+3)&~3;data=b[o:o+f[6]];o=(o+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='simulation/fx3-timer-observe-v1.so':entries.append(('simulation/fx3-ui-gate-v1.so',f,(R/'helpers/fx3-ui-gate-v1.so').read_bytes()))
 if name=='init':
  init=data.decode();assert init.count(':/usr/lib/libInfraCrypt.so')==1;init=init.replace(':/usr/lib/libInfraCrypt.so',':/simulation/fx3-ui-gate-v1.so:/usr/lib/libInfraCrypt.so');init=init.replace('echo FX3_AP_SNAPSHOT_${turn}_BEGIN','echo FX3_AP_SNAPSHOT_${turn}_BEGIN\n  echo FX3_GUEST_UPTIME_SNAPSHOT; /bin/busybox cat /proc/uptime');data=init.encode()
 entries.append((name,f,data))
out=bytearray()
def add(name,f,data,ino):
 f=f.copy();raw=name.encode()+b'\0';f[0]=ino;f[6]=len(data);f[11]=len(raw);out.extend(b'070701'+''.join(f'{n:08x}' for n in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(data);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,data) in enumerate(entries,1):add(n,f,data,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cpio=D/'guest.cpio';cpio.write_bytes(out)
spec=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);b=Path(v['dtb']['path']).read_bytes();assert sha(b)==v['dtb']['sha256'];tree,props,res,meta=m.parse(b);chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');phys=0x41dc00000;extent=0x10000;oldres=[struct.unpack_from('>QQ',res,i) for i in range(0,len(res)-16,16)];boot=next(p[1].rstrip(b'\0').decode() for k,p in chosen['items'] if k=='prop' and p[0]=='bootargs');ranges=oldres+[(int(a,16),int(n,16)) for n,a in re.findall(r'memrsv=(0x[0-9a-fA-F]+)@(0x[0-9a-fA-F]+)',boot)];assert all(phys+extent<=a or a+n<=phys for a,n in ranges);assert 0x400000000<=phys<phys+extent<=0x540000000
res=res[:-16]+struct.pack('>QQ',phys,extent)+b'\0'*16
chosen['items']=[(k,(p[0],struct.pack('>Q',0x440000000+len(out))) if k=='prop' and p[0]=='linux,initrd-end' else (p[0],(boot+' memrsv=0x00010000@0x41dc00000:uc').encode()+b'\0') if k=='prop' and p[0]=='bootargs' else p) for k,p in chosen['items']]
dtb=D/'guest.dtb';dtb.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dtb),'sha256':sha(dtb.read_bytes())};v['initrd']={'path':str(cpio),'sha256':sha(out)};v['scope']+=' AP77 passive UI gate and boot-barrier counters, exact-word single-instruction near islands after full-register synthetic selftest; observer-only41dc00000/64KiB.';v['required_markers']+=['FX3_UI_GATE_SELFTEST_PASS','FX3_UI_GATE_BOUND'];(D/'candidate77.json').write_text(json.dumps(v,indent=2)+'\n');(D/'init-reviewed.sh').write_text(init);(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base.read_bytes()),'changes':['append observer preload; preserve all existing helper bytes','private FDT+memrsv observer counter RAM','read /proc/uptime inside existing proc snapshot; no added sleeps'],'reservation':{'physical':hex(phys),'bytes':extent,'checked':[[hex(a),hex(n)] for a,n in ranges],'nonoverlap':True},'initrd':v['initrd'],'dtb':v['dtb']},indent=2)+'\n');print(D/'candidate77.json')
