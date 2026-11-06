#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team');N=TEAM/'parallel-review-20261105/fx6-map-snapshot-producer-candidate';CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'
P=[TEAM/'parallel-review-20261105/runs/r6-stop-only-20261106T2005Z/run/serial.log',CP/'runs/cp-bind-66ed0f78/serial.log',N.parent/'fx6-backup-map-parser-candidate/work/cpio/init',CP/'grm-fbinit/appFw-future-skip.so',CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 v={'schema':'fx6-map-snapshot-input-seal-v2','phase':phase,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','inputs':[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P],'count':len(P)};(N/'receipts'/(phase+'-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(P)}))
if __name__=='__main__':main(sys.argv[1])
