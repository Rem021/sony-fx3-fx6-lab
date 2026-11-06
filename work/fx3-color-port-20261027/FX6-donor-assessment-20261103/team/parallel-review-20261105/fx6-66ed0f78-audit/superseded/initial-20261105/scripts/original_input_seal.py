#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'
P=[TEAM/'donor/nflasha15-files/lib/appFw.so',TEAM/'donor/nflasha15-files/kmod/upm.ko',TEAM/'donor/nflasha15-files/kmod/backup.ko',TEAM/'donor/nested-files/nflasha1-initrd/usr/kmod/backup.ko',
 CP/'grm-fbinit/appFw-future-skip.so',CP/'grm-fbinit/backup-bug-skip.ko',CP/'grm-fbinit/upm-callsite-skip.ko',CP/'fx6-cp-backup-sync100-agnostic-g0.ko',
 TEAM/'donor/hybrid-ap-candidate/guest-three-entry.cpio',CP/'guest-hybrid-fx6kernel.cpio',CP/'guest-cp-helper-agnostic.cpio',CP/'guest-hybrid-fx6kernel-capid-grmreal21.cpio',CP/'guest-hybrid-fx6kernel-capid-grmreal41.cpio']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 rows=[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P]
 v={'schema':'fx6-r50-original-input-seal-v1','phase':phase,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','inputs':rows,'count':len(rows),'note':'provenance inputs read-only'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-original-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(rows)}))
if __name__=='__main__':main(sys.argv[1])
