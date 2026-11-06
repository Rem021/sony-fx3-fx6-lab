from pathlib import Path
import json,hashlib,struct,importlib.util,sys,subprocess,plistlib
R=Path(__file__).resolve().parent;D=R/sys.argv[1];base=R/sys.argv[2];remove=sys.argv[3:];assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';D.mkdir();v=json.loads(base.read_text());b=Path(v['initrd']['path']).read_bytes();entries=[];o=0;sha=lambda b:hashlib.sha256(b).hexdigest()
while True:
 f=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];name=b[o+110:o+110+f[11]-1].decode();o=(o+110+f[11]+3)&~3;data=b[o:o+f[6]];o=(o+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='init':
  s=data.decode()
  for member in remove:
   needle='/simulation/'+member+':';assert needle in s;s=s.replace(needle,'')
  if 'FX3_AP_EARLY_MAPS_' not in s:
   needle=' for turn in 1 2 3; do';assert needle in s;s=s.replace(needle,''' for early in 1 2 3 4 5; do
  /bin/busybox sleep 1
  for im_pid in $(/bin/busybox pidof im.elf); do
   echo FX3_AP_EARLY_MAPS_${im_pid}_${early}_BEGIN
   /bin/busybox cat /proc/uptime /proc/$im_pid/maps
   echo FX3_AP_EARLY_MAPS_${im_pid}_${early}_END
  done
 done
'''+needle)
  data=s.encode();(D/'init-reviewed.sh').write_text(s)
 entries.append((name,f,data))
out=bytearray()
def add(n,f,b,i):
 f=f.copy();z=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(z);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+z);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);t,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());c=next(n for k,n in t['items'] if k=='node' and n['name']=='chosen');c['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in c['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(t,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt.read_bytes())};v['initrd']={'path':str(cp),'sha256':sha(out)}
if any('display-observe' in x for x in remove):v['required_markers']=[x for x in v['required_markers'] if not x.startswith('FX3_DISPLAY_')]
if any('lifetime' in x for x in remove):v['required_markers']=[x for x in v['required_markers'] if not x.startswith('FX3_OSD_LIFE_')]
v['required_markers']+=['FX3_AP_EARLY_MAPS_'];v['scope']+=' Isolation authorized by Lead ask5679: remove only preload '+','.join(remove)+'; helper bytes and protocol contracts unchanged, earlier1s read-only maps samples.';(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n');(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'init_only_change':True,'preload_removed':remove,'all_helper_bytes_unchanged':True,'DTB_only_initrd_end':True,'earlier_maps_samples':True},indent=2)+'\n');print(D/'candidate.json')
