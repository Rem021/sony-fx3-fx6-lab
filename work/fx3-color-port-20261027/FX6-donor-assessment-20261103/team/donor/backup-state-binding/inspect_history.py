#!/usr/bin/env python3
"""Read two pinned old VM RAM snapshots without executing or modifying a VM."""
import hashlib
import json
from pathlib import Path

from parse_bk4 import ROOT, read_record

BASE = ROOT / "work/fx3-vm-20261101/menu-repair-01/runtime/runs"
SOURCES = {
    "AP88_shutdown_RAM": (BASE / "ap88cpr4-e71668cb/backup-after-shutdown.bin", "38cf44637c44d3f47d7b8541dddf7ecc443e262f40dec3aec59f7b94d5b8b38f"),
    "AP89_replay_RAM": (BASE / "ap89replay-b736403b/backup-reserved-ram.bin", "ece9dbb93d3856705fdf1169c9730043e2e03fba5f3a3f0dd3cbcd20659d6d3f"),
}


def main():
    out = {"scope":"historical FX3 VM guest RAM snapshots only; AP89 is replay from AP88 RAM and not an independent natural camera sample; invalid checksum is preserved, not repaired", "sources":{}}
    for name,(path,expected) in SOURCES.items():
        data=path.read_bytes()
        actual=hashlib.sha256(data).hexdigest()
        if actual!=expected:raise ValueError("history SHA mismatch")
        first,end=read_record(data,0,require_checksum=False)
        second,end2=read_record(data,(end+4095)&~4095,require_checksum=False)
        if end2>len(data) or any(data[end2:]):raise ValueError("snapshot tail invalid")
        out["sources"][name]={"path":str(path),"sha256":actual,"size":len(data),"zero_tail_bytes":len(data)-end2,"records":[first,second]}
    print(json.dumps(out,indent=2))


if __name__=="__main__":main()
