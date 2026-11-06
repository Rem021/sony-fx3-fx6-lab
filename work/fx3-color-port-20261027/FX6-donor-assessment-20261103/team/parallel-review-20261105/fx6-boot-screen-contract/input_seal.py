#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; AUD=TEAM/'parallel-review-20261105/fx6-66ed0f78-audit'
P=[TEAM/'fx6-66ed0f78-coordinator-final-review.json',AUD/'REPORT.md',AUD/'RESULT.json',AUD/'SHA256SUMS',AUD/'receipts/serial-evidence.json',AUD/'receipts/hash-audit.json',AUD/'receipts/backup-section-audit.json',
 CP/'runs/cp-bind-66ed0f78/serial.log',CP/'runs/cp-bind-84db17c2/serial.log',CP/'runs/cp-bind-9d22099a/serial.log',
 CP/'grm-fbinit/appFw-future-skip.so',TEAM/'donor/nflasha15-files/lib/appFw.so',CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',CP/'vm-candidate-upmcallsite180.json',
 CP/'guest-hybrid-fx6kernel-capid-grmreal45.cpio',CP/'vm-candidate-upmthofsskip.json']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 rows=[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P]
 v={'schema':'fx6-r50-boot-screen-input-seal-v1','phase':phase,'task':'task_97919f2e6f0f','dispatch':'ctx_a9695459fefe','volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','inputs':rows,'count':len(rows),'note':'frozen logs/donor/appFw/analysis read-only; only contract dir written'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(rows)}))
if __name__=='__main__':main(sys.argv[1])
