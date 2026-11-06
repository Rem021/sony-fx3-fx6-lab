#!/usr/bin/env python3

import plistlib, subprocess
assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
from pathlib import Path
import json,tarfile,hashlib
HERE=Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if p.name=='Mac')
def main():
 archive=ROOT/'work/sony-firmware-20261024/stage65-windows-cache-and-runtime-readiness/work/vendor-source-reference/range-resume-20261026/linux-kernel.complete.tar.gz'
 assert hashlib.sha256(archive.read_bytes()).hexdigest()=='bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f'
 selected=json.loads((HERE/'GPL-SELECTION.json').read_text());expected={x['member']:x for x in selected};found=[]
 with tarfile.open(archive,'r:gz') as t:
  for m in t:
   if m.name not in expected:continue
   assert m.isfile();data=t.extractfile(m).read();e=expected[m.name];assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256']
   p=HERE/'gpl-reference'/m.name.removeprefix('linux-kernel/');assert p.resolve().is_relative_to(HERE/'gpl-reference');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);found.append(m.name)
 assert len(found)==len(expected);print('reused official FX3 7.00 archive members',len(found),'as reference, not exact 7.02 whole-build proof')
if __name__=='__main__':main()
