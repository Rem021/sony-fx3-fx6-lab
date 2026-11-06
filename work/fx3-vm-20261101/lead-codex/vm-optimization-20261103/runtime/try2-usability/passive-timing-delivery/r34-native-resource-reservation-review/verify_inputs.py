#!/usr/bin/env python3

import plistlib, subprocess
assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
from pathlib import Path
import hashlib,json,datetime
HERE=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 before={}
 for p in HERE.glob('*BEFORE.json'):
  for r in json.loads(p.read_text())['files']:
   if r['path'] in before:assert before[r['path']]['sha256']==r['sha256']
   before[r['path']]=r
 after=[]
 for name,e in sorted(before.items()):
  p=Path(name);a=sha(p);n=p.stat().st_size;after.append(dict(path=name,expected_sha256=e['sha256'],actual_sha256=a,expected_bytes=e['bytes'],actual_bytes=n,matched=a==e['sha256'] and n==e['bytes']))
 r33=HERE.parent/'r33-causal-observation-candidate';manifest=r33/'SHA256SUMS';assert sha(manifest)=='b16584e9f19853663eab579a8d040a787e606f24289a7748ee75f9bc3958c894'
 frozen=[]
 for line in manifest.read_text().splitlines():
  e,n=line.split('  ',1);assert sha(r33/n)==e;frozen.append(n)
 d=dict(captured_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Necessary technical inputs only; shared project README intentionally not treated as runtime freeze',count=len(after),unchanged=sum(x['matched'] for x in after),files=after,r33_frozen_manifest_items=len(frozen),r33_mismatches=[])
 (HERE/'INPUTS-AFTER.json').write_text(json.dumps(d,indent=2)+'\n');assert all(x['matched'] for x in after);print(json.dumps({'technical_inputs':len(after),'unchanged':d['unchanged'],'r33_frozen_items':len(frozen)}))
if __name__=='__main__':main()
