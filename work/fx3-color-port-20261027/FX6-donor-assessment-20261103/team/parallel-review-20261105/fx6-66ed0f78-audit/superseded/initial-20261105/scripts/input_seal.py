#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team')
CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'
RUN=CP/'runs/cp-bind-66ed0f78'; B1=CP/'runs/cp-bind-6e83a14a'; B2=CP/'runs/cp-bind-9d22099a'
P=[TEAM/'fx6-primary-readonly-refresh-20261105-66ed0f78.json',RUN/'command.json',RUN/'run-receipt.json',RUN/'serial.log',RUN/'host-stdout.log',RUN/'host-stderr.log',
 CP/'vm-candidate-upmcallsite180.json',CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',CP/'UPMCALLSITE-CPIO-BUILD.json',CP/'build_upmcallsite_cpio.py',
 CP/'APPFWFUTURE-CPIO-BUILD.json',CP/'build_appfwfuture_cpio.py',CP/'BACKUPBUG-CPIO-BUILD.json',CP/'build_backupbug_cpio.py',
 CP/'guest-hybrid-fx6kernel-capid-grmreal41.cpio',CP/'guest-hybrid-fx6kernel.cpio',CP/'guest-cp-helper-agnostic.cpio',
 TEAM/'donor/hybrid-ap-candidate/guest-three-entry.cpio',B1/'command.json',B1/'run-receipt.json',B1/'serial.log',B1/'RESULT.json',B1/'RUN-REPORT.md',
 B2/'command.json',B2/'run-receipt.json',B2/'serial.log']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 rows=[]
 for p in P:
  if not p.is_file():raise SystemExit('missing '+str(p))
  rows.append({'path':str(p),'sha256':h(p),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns})
 v={'schema':'fx6-r50-audit-input-seal-v1','phase':phase,'task':'task_a43e50d89605','dispatch':'ctx_732d01695498','volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','inputs':rows,'count':len(rows),'note':'read-only source/platform; only audit dir is written'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n')
 print(json.dumps({'phase':phase,'count':len(rows)}))
if __name__=='__main__':main(sys.argv[1])
