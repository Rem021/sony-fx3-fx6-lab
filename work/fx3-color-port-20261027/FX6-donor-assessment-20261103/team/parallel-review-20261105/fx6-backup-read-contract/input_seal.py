#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; AUD=TEAM/'parallel-review-20261105/fx6-boot-screen-contract'
P=[TEAM/'fx6-boot-screen-coordinator-review.json',AUD/'REPORT.md',AUD/'RESULT.json',AUD/'SHA256SUMS',AUD/'receipts/boot-screen-contract.json',
 CP/'runs/cp-bind-66ed0f78/serial.log',CP/'grm-fbinit/appFw-future-skip.so',CP/'grm-fbinit/backup-bug-skip.ko',CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',CP/'guest-hybrid-fx6kernel-capid-grmreal45.cpio',CP/'guest-cp-helper-agnostic.cpio',TEAM/'donor/hybrid-ap-candidate/guest-three-entry.cpio',
 Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/lifecycle-repair/vmopt-20261103-reload-v1/Backup-generation4-fixed.bin'),
 Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin'),
 CP/'build_appfwfuture_cpio.py',CP/'build_upmcallsite_cpio.py',CP/'build_backupbug_cpio.py',CP/'build_cpio.py']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 v={'schema':'fx6-r50-backup-read-input-seal-v1','phase':phase,'task':'task_c325ed9e8329','dispatch':'ctx_e375bfccafeb','volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','inputs':[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P],'count':len(P),'note':'read-only target/frozen inputs; only contract dir written'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(P)}))
if __name__=='__main__':main(sys.argv[1])
