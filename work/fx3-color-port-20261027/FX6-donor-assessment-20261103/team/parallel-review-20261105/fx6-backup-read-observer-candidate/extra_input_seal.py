#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
C=Path(__file__).resolve().parent;T=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team')
P=[T/'fx6-backup-observer-coordinator-review.json',T/'donor/first-ap-readonly-observer/rsp_stop_audit.py',Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/lifecycle-repair/runs/vmopt-20261103-lifecycle-guest18-1da10e34/observer-source/restore_api103_v2.py'),Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-backup-receiver-trace/work/fx3-cp-backup-reset-v1.ko')]
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 v={'schema':'fx6-observer-extra-input-seal-v1','phase':phase,'inputs':[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P],'count':len(P)};(C/'receipts'/f'{phase}-extra-input-seal.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(P)}))
if __name__=='__main__':main(sys.argv[1])
