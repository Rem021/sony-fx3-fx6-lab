#!/usr/bin/env python3

import plistlib, subprocess
assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if p.name=='Mac')
P=HERE.parent/'r16-fixed-slot-guests/guest-N64/guest.cpio'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 assert digest(P)=='aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9'
 inv={x['path']:x for x in json.loads((HERE.parent/'r33-causal-observation-candidate/ACTUAL-MEMBERS.json').read_text())}
 selected={'usr/lib/libObj.so':True,'usr/kmod/dmm.ko':True,'usr/kmod/grm_ma.ko':False,'setting/DmmCfg.bin':False};found=[];count=0
 with P.open('rb') as f:
  while True:
   header_at=f.tell();h=f.read(110);assert h[:6]==b'070701'
   fields=[int(h[6+i*8:14+i*8],16) for i in range(13)];name=f.read(fields[11]);assert name[-1]==0
   f.read((-f.tell())%4);at=f.tell();name=name[:-1].decode()
   if name=='TRAILER!!!':break
   count+=1
   if name in selected:
    data=f.read(fields[6]);e=inv[name];sha=hashlib.sha256(data).hexdigest();assert e['data_offset']==at and e['bytes']==len(data) and e['sha256']==sha
    if selected[name]:(HERE/Path(name).name).write_bytes(data)
    else:
     base=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection';q=base/('full-v4/regular-files' if name.endswith('.ko') else 'regular-files')/name;assert q.read_bytes()==data
    found.append(dict(member=name,header_offset=header_at,data_offset=at,bytes=len(data),sha256=sha,extracted=selected[name]))
   else:f.seek(fields[6],1)
   f.read((-f.tell())%4)
 assert len(found)==4 and count==1140
 result=dict(cpio_sha256=digest(P),member_count=count,selected=found,scope='Only libObj.so and dmm.ko extracted; config and MA compared in-place without guest execution')
 (HERE/'MEMBER-BINDING.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
