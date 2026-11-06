"""Read-only original input recheck; outputs are confined to this r39 directory."""
from pathlib import Path
import hashlib,json,plistlib,subprocess,time
O=Path(__file__).resolve().parent;S=O.parent/'r37-diagnostic-runner-candidate'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
expected=json.loads((O/'INPUTS-BEFORE.json').read_text())
for name in ('INPUTS-BEFORE.json','DEPENDENCY-INPUTS-BEFORE.json','CPIO-AUDIT-INPUTS-BEFORE.json'):
 rows=json.loads((S/name).read_text());rows=rows['files'] if isinstance(rows,dict) else rows
 for row in rows:
  p=row['path'];v={'sha256':row['sha256'],'bytes':row['bytes']}
  if p in expected:assert expected[p]==v,(p,'conflicting pinned inputs')
  expected[p]=v
# Shared project README is context, not a frozen runtime dependency.
assert '/Volumes/KAFU2T/AI/Projects/Mac/README.md' not in expected
(O/'TECHNICAL-INPUTS-BEFORE.json').write_text(json.dumps({'basis':'r39 observed inputs plus accepted r37 technical-input pins; shared project README excluded','files':expected},indent=2)+'\n')
rows=[]
for name,v in sorted(expected.items()):
 p=Path(name);actual={'sha256':sha(p),'bytes':p.stat().st_size};rows.append({'path':name,'expected':v,'actual':actual,'match':v==actual})
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
result={'files':rows,'counts':{'checked':len(rows),'matched':sum(r['match'] for r in rows)},'mismatches':[r for r in rows if not r['match']],'verified_wall_ns':time.time_ns()}
(O/'INPUTS-AFTER.json').write_text(json.dumps(result,indent=2)+'\n');assert not result['mismatches'],result['mismatches'];print('original technical input hashes unchanged',len(rows))
