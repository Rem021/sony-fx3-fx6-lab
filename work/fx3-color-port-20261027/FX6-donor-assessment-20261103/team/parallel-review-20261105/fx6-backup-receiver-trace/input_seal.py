#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; OLD=TEAM/'parallel-review-20261105/fx6-backup-read-contract'; W=OLD/'work'; N=Path(__file__).resolve().parent/'work'
P=[TEAM/'fx6-backup-reader-coordinator-review.json',CP/'runs/cp-bind-66ed0f78/serial.log',CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',CP/'guest-hybrid-fx6kernel-capid-grmreal45.cpio',W/'libbackup.so',W/'libosal_uipc.so',W/'backup.ko',W/'im.elf',W/'bootin.elf',W/'appFw.so',W/'ioctl-trace.so',W/'fx3-backup-return-v1.so',N/'libbkdmn.so',N/'fx3-cp-backup-reset-v1.ko',N/'fx3-sync100-unbind-v1.ko']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 v={'schema':'fx6-receiver-trace-input-seal-v1','phase':phase,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','inputs':[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P],'count':len(P),'note':'read-only frozen inputs; old audit read-only'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(P)}))
if __name__=='__main__':main(sys.argv[1])
