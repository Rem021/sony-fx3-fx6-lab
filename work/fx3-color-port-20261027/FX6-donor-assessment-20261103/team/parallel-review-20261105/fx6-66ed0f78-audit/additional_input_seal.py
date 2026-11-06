#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; B=CP/'runs/cp-bind-84db17c2'
P=[B/'command.json',B/'run-receipt.json',B/'serial.log',CP/'vm-candidate-upmthofsskip.json',CP/'guest-hybrid-fx6kernel-capid-grmreal45.cpio',Path('/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin')]
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 v={'schema':'fx6-r50-additional-input-seal-v1','phase':phase,'run':'cp-bind-84db17c2','inputs':[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P],'count':len(P),'note':'one appended completed baseline; read-only'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-additional-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(P)}))
if __name__=='__main__':main(sys.argv[1])
