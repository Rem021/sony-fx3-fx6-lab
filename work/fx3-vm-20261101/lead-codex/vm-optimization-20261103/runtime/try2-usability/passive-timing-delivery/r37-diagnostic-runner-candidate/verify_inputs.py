#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,subprocess,plistlib
O=Path(__file__).resolve().parent
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
pins={}
for name in ['INPUTS-BEFORE.json','DEPENDENCY-INPUTS-BEFORE.json','CPIO-AUDIT-INPUTS-BEFORE.json']:
 j=json.loads((O/name).read_text());rows=j if isinstance(j,list) else j['files']
 for r in rows:
  if r['path'] in pins:assert pins[r['path']]['sha256']==r['sha256']
  pins[r['path']]=r
rows=[]
for p,r in sorted(pins.items()):
 path=Path(p)
 with path.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 rows.append({'path':p,'before_sha256':r['sha256'],'after_sha256':h,'bytes_before':r['bytes'],'bytes_after':path.stat().st_size,'match':h==r['sha256'] and path.stat().st_size==r['bytes']})
bad=[r for r in rows if not r['match']];result={'technical_inputs':len(rows),'matched':len(rows)-len(bad),'mismatches':bad,'files':rows,'shared_project_README_excluded':True};(O/'INPUTS-AFTER.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='files'}));assert not bad
