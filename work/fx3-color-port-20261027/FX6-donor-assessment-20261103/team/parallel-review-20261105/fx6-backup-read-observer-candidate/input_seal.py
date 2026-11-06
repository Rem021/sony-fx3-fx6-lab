#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; OLD=TEAM/'donor/first-ap-readonly-observer'; B=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json')
P=[TEAM/'fx6-backup-receiver-coordinator-review.json',CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',CP/'runs/cp-bind-66ed0f78/serial.log',CP/'grm-fbinit/appFw-future-skip.so',B,OLD/'README.md',OLD/'readonly_probe.py',OLD/'two_phase_identity.py',OLD/'run_once.py',OLD/'test_host.py']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 v={'schema':'fx6-backup-observer-input-seal-v1','phase':phase,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','inputs':[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P],'count':len(P),'note':'read-only frozen inputs; old observer read-only; no execution'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(P)}))
if __name__=='__main__':main(sys.argv[1])
