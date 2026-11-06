"""Read-only final-source check against r37 lineage/delta; no launch or mutation."""
from pathlib import Path
import hashlib,json
O=Path(__file__).resolve().parent;S=O.parent/'r37-diagnostic-runner-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,v in json.loads((O/'SOURCE-LINEAGE.json').read_text()).items():
 assert sha(O/n)==v['after']
 if v['before']:assert sha(S/n)==v['before']
print('final source lineage hashes PASS; source delta is r37-to-r39.diff')
