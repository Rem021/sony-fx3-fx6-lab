#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,subprocess,plistlib
HERE=Path(__file__).resolve().parent
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 vol=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']));assert vol['VolumeUUID']==UUID
 before={}
 for p in sorted(HERE.glob('*BEFORE.json')):
  for row in json.loads(p.read_text())['files']:
   k=row['path']
   if k in before:assert before[k]['sha256']==row['sha256'],k
   before[k]=row
 rows=[]
 for path,e in before.items():
  p=Path(path);a=sha(p);n=p.stat().st_size
  rows.append(dict(path=path,expected_sha256=e['sha256'],actual_sha256=a,expected_bytes=e['bytes'],actual_bytes=n,matched=a==e['sha256'] and n==e['bytes']))
 # Verify frozen manifests against their owning dirs; no imports or runner calls.
 checks={}
 for d,m in [('r32-zero-ring-causal-review','SHA256SUMS'),('r30-startup-observation-candidate','SOURCE-FREEZE.json')]:
  root=HERE.parent/d;p=root/m
  entries=json.loads(p.read_text()) if m.endswith('.json') else {line.split(None,1)[1].strip().lstrip('*'):line.split(None,1)[0] for line in p.read_text().splitlines() if line}
  bad=[]
  for name,expected in entries.items():
   q=root/name
   if not q.is_file() or sha(q)!=expected:bad.append(name)
  checks[d]=dict(manifest=m,entries=len(entries),mismatches=bad)
 report=dict(captured_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),volume_uuid=vol['VolumeUUID'],unique_original_inputs=len(rows),unchanged=sum(r['matched'] for r in rows),files=rows,frozen_checks=checks)
 (HERE/'INPUTS-AFTER.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(unique_inputs=len(rows),unchanged=report['unchanged'],frozen_checks=checks),indent=2))
 assert all(x['matched'] for x in rows) and all(not x['mismatches'] for x in checks.values())
if __name__=='__main__':main()
