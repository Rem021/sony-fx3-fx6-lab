#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
C=Path(__file__).resolve().parent; W=C/'work'
P=[W/'appFw.so',W/'im.elf',W/'bootin.elf',W/'libbackup.so',W/'libBackupManager.so',W/'libInfraExtBackupCommunicator.so',W/'libosal_uipc.so',W/'backup.ko',W/'fx3-backup-return-v1.so',W/'ioctl-trace.so',W/'fx3-icrypt-observe-v1.so']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 v={'schema':'fx6-provider-input-seal-v1','phase':phase,'inputs':[{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size} for p in P],'count':len(P),'note':'extracted from frozen target CPIO; read-only'}
 (C/'receipts'/(phase+'-provider-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'phase':phase,'count':len(P)}))
if __name__=='__main__':main(sys.argv[1])
