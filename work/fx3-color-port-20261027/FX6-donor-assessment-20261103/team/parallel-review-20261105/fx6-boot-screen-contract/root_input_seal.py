#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team')
P=[Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/lifecycle-repair/vmopt-20261103-reload-v1/Backup-generation4-fixed.bin'),
 TEAM/'donor/backup-state-binding/parse_bk4.py',TEAM/'donor/backup-state-binding/bk4-receipt.json',TEAM/'donor/backup-state-binding/README.md',TEAM/'donor/backup-state-binding/static-receipt.json']
for d in ('CHAPLIN/CX95898_NTSC.bin','CHAPLIN/CX95898_J.bin','CHAPLIN/CX95898_UC.bin','CHAPLIN/CX95899_CEE.bin','CHAPLIN/CX95899_CN1.bin'):
 P.append(TEAM/'donor/tree/0110_backup/SYSIPSX-DSLR'/d)
P.append(Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin'))
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 rows=[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P]
 v={'schema':'fx6-r50-boot-screen-root-input-seal-v1','phase':phase,'inputs':rows,'count':len(rows),'note':'backup image/templates/parser read-only'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-root-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(rows)}))
if __name__=='__main__':main(sys.argv[1])
