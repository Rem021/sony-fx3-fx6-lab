#!/usr/bin/env python3
"""Freeze only production files used by r30; no process launch or old-file mutation."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parent;B=R.parent/'r28-first-observation-candidate'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
names=list(json.loads((B/'CORE-SOURCE-FREEZE.json').read_text()))+['startup_observation.py','trial_ring_cached.py','trial_log_v4_mss.py']
core={f:sha(R/f) for f in names}
(R/'CORE-SOURCE-FREEZE.json').write_text(json.dumps(core,indent=2)+'\n')
p=R/'return-tools/return_adapter.py';s=p.read_text();s,n=re.subn(r"CORE_FREEZE_SHA='[0-9a-f]{64}'","CORE_FREEZE_SHA='"+sha(R/'CORE-SOURCE-FREEZE.json')+"'",s);assert n==1;p.write_text(s)
full={**core,**{'return-tools/'+p.name:sha(p) for p in sorted((R/'return-tools').glob('*.*'))},'CORE-SOURCE-FREEZE.json':sha(R/'CORE-SOURCE-FREEZE.json')}
(R/'SOURCE-FREEZE.json').write_text(json.dumps(full,indent=2)+'\n')
print(json.dumps({'core_files':len(core),'production_files':len(full),'core_sha':sha(R/'CORE-SOURCE-FREEZE.json'),'source_sha':sha(R/'SOURCE-FREEZE.json')}))
