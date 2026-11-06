#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,subprocess,plistlib
O=Path(__file__).resolve().parent
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
allpins={};sets={}
for name in ['INPUTS-BEFORE.json','BUILD-INPUTS-BEFORE.json','SUPPLEMENT-INPUTS-BEFORE.json']:
 j=json.loads((O/name).read_text());rows=j if isinstance(j,list) else j['files'];sets[name]=len(rows)
 for r in rows:
  if r['path'] in allpins:assert allpins[r['path']]['sha256']==r['sha256']
  allpins[r['path']]=r
rows=[];bad=[]
for path,r in sorted(allpins.items()):
 p=Path(path);b=p.read_bytes();h=hashlib.sha256(b).hexdigest();same=len(b)==r['bytes'] and h==r['sha256'];entry={'path':path,'bytes_before':r['bytes'],'bytes_after':len(b),'sha256_before':r['sha256'],'sha256_after':h,'match':same};rows.append(entry)
 if not same:bad.append(entry)
result={'input_sets':sets,'unique_technical_inputs':len(rows),'matched':len(rows)-len(bad),'mismatches':bad,'files':rows,'shared_project_README_excluded':True};(O/'INPUTS-AFTER.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='files'}));assert not bad
