#!/usr/bin/env python3
"""Finite byte-marker inventory of existing original binaries, read-only."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
APP=Path('/Volumes/KAFU2T/AI/Codex/Worktrees/phayen-venice-firmware/work/venice-firmware-2026-10-23/rawviewer-expanded/rawviewer-flat.pkg/Payload/RAW Viewer.app/Contents')
MARKERS=[b'BinaryPackProperty',b'ProductCodeVersion',b'DATA23213',b'enctype="type4"',b'enctype=\'type4\'']

def main():
    roots=[PROJECT/'work/sony-firmware-20261024/stage2/extraction/files',APP/'MacOS',APP/'Frameworks']
    inventory=[];hits=[]
    for root in roots:
        assert root.is_dir(),root
        files=sorted(p for p in root.rglob('*') if not p.is_symlink() and p.is_file())
        for path in files:
            data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
            inventory.append(dict(root=str(root),relative=str(path.relative_to(root)),bytes=len(data),sha256=digest))
            for marker in MARKERS:
                pos=0;positions=[]
                while True:
                    off=data.find(marker,pos)
                    if off<0:break
                    positions.append(off);pos=off+len(marker)
                if positions:hits.append(dict(path=str(path),sha256=digest,marker=marker.decode(),offsets=positions))
    result=dict(roots=[str(r) for r in roots],markers=[s.decode() for s in MARKERS],files=len(inventory),bytes=sum(r['bytes'] for r in inventory),hits=hits,inventory=inventory,
                scope='Only exact byte markers in these original extracted FX3 files and RAW Viewer executable/framework trees. Absence does not rule out a parser, transformed strings, other files or other firmware versions. No originals modified or vendor code loaded.')
    (HERE/'loader-marker-scan-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['files','bytes','hits']}))

if __name__=='__main__':main()
