#!/usr/bin/env python3
"""Read-only native FX3 resource evidence; never imports/executes guest code."""

import plistlib, subprocess
assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
from pathlib import Path
import json,struct,hashlib,subprocess
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if p.name=='Mac')
PROJ=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection'
BASE=0x41dc00000;END=BASE+0x10000

def cfg(raw):
 at=0;out={}
 def take(n):
  nonlocal at
  o=at;at+=n;assert at<=len(raw);return o,raw[o:at]
 for phase in ['roots','rules']:
  groups=[]
  while True:
   o,h=take(80);typ,sel=struct.unpack_from('<II',h,8)
   if typ==0xffffffff:break
   rows=[]
   while True:
    r,d=take(20);w=list(struct.unpack('<5I',d))
    if w[2]==0xffffffff:break
    rows.append(dict(offset=hex(r),words=w))
   groups.append(dict(offset=hex(o),type=typ,selector=sel,header_hex=h.hex(),rows=rows))
  out[phase]=groups
 units=[]
 while True:
  o,d=take(8);u,a=struct.unpack('<II',d)
  if u==0xffffffff:break
  refs=[]
  while True:
   _,d=take(4);v=int.from_bytes(d,'little')
   if v==0xffffffff:break
   refs.append(v)
  units.append(dict(offset=hex(o),unit=u,attribute=a,extents=refs))
 _,v=take(44);assert at==len(raw);out.update(units=units,version=v.decode(),consumed_bytes=at);return out

def main():
 cpio=HERE.parent/'r16-fixed-slot-guests/guest-N64/guest.cpio'
 inv={x['path']:x for x in json.loads((HERE.parent/'r33-causal-observation-candidate/ACTUAL-MEMBERS.json').read_text())}
 name='setting/DmmCfg.bin';e=inv[name]
 with cpio.open('rb') as f:f.seek(e['data_offset']);raw=f.read(e['bytes'])
 assert hashlib.sha256(raw).hexdigest()==e['sha256']=='48c90ca08ae8174d376bf8cbb454a5544e3d024c317e5136fb31d4fb78572bb1'
 assert raw==(PROJ/'regular-files'/name).read_bytes()
 d=cfg(raw);selected=[x for x in d['units'] if x['unit']==0x403];refs={y for x in selected for y in x['extents']}
 rules=[dict(g,rows=[r for r in g['rows'] if r['words'][2] in refs]) for g in d['rules'] if any(r['words'][2] in refs for r in g['rows'])]
 ranges=[]
 for g in d['roots']:
  for r in g['rows']:
   a,f,t,n,attr=r['words'];hi=(f>>16)&0xffff;phys=a+(hi<<32)
   ranges.append(dict(group_type=g['type'],group_selector=g['selector'],file_offset=r['offset'],raw_words=r['words'],physical=hex(phys),bytes=hex(n),end_exclusive=hex(phys+n),overlaps_UI=phys<END and BASE<phys+n,interpretation='AP dmm.ko GetExtentAreaInfo low32 + u16@+6<<32; root table semantics require native-code binding'))
 result=dict(source_member=e,version=d['version'],parsed_bytes=d['consumed_bytes'],unit_403=selected,unit_403_rules=rules,root_rows=ranges,unit_403_root_rows=[r for r in ranges if r['raw_words'][2] in {x['type'] for x in rules}],root_overlap_count=sum(x['overlaps_UI'] for x in ranges),limits='Static config geometry only; not runtime-selected mode, allocator proof, or complete native ABI reachability')
 (HERE/'CONFIG-403.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
