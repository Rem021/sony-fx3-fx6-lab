#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'
P=[CP/'runs/cp-bind-66ed0f78/serial.log',CP/'runs/cp-bind-66ed0f78/run-receipt.json',CP/'runs/cp-bind-84db17c2/serial.log',CP/'runs/cp-bind-84db17c2/run-receipt.json',TEAM/'parallel-review-20261105/fx6-66ed0f78-audit/REPORT.md',CP.parent/'fixed_runner.py']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 v={'schema':'fx6-serial-fault-detector-input-seal-v1','phase':phase,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','inputs':[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P],'count':len(P)};(Path(__file__).resolve().parent/'receipts'/(phase+'-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(P)}))
if __name__=='__main__':main(sys.argv[1])
