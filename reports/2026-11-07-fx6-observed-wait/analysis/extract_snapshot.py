#!/usr/bin/env python3
"""Extract recorded, single-run snapshot addresses; never connect to a VM."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def extract(text):
    blocks = re.findall(r'^FX6_WAIT_SNAPSHOT_MAPS_BEGIN tid=(\d+)\s*\n(.*?)^FX6_WAIT_SNAPSHOT_MAPS_END[^\n]*$',
                        text, re.M|re.S)
    if len(blocks) != 1:
        raise ValueError('expected exactly one recorded maps snapshot')
    maps = blocks[0][1]
    addresses, threads = [], {}
    for line in text.splitlines():
        reg = re.match(r'^FX6_WAIT_SNAPSHOT_REG tid=(\d+) (.*)',line)
        if reg:
            tid = int(reg[1]);fields=dict(re.findall(r'(\w+)=(0x[0-9a-f]+)',reg[2]))
            if tid in threads:raise ValueError('duplicate register snapshot')
            threads[tid]={'registers':fields,'frame_records':[]}
            for role in ('pc','lr'):
                addresses.append({'tid':tid,'role':role,'address':fields[role]})
        frame = re.match(r'^FX6_WAIT_SNAPSHOT_FRAME tid=(\d+) index=(\d+) (.*)',line)
        if frame:
            tid,index=int(frame[1]),int(frame[2]);fields=dict(re.findall(r'(\w+)=(0x[0-9a-f]+)',frame[3]))
            if tid not in threads:raise ValueError('frame precedes registers')
            if index != len(threads[tid]['frame_records']):raise ValueError('frame index discontinuity')
            threads[tid]['frame_records'].append(fields)
            addresses.append({'tid':tid,'role':'frame_saved_lr','frame_index':index,'address':fields['saved_lr']})
    for label in ('COMM','SYSCALL'):
        for tid,body in re.findall(r'^FX6_WAIT_SNAPSHOT_'+label+r'_BEGIN tid=(\d+)\s*\n(.*?)^FX6_WAIT_SNAPSHOT_'+label+r'_END[^\n]*$',text,re.M|re.S):
            if int(tid) in threads:threads[int(tid)][label.lower()]=body.strip()
    if not threads:raise ValueError('no successful register snapshots')
    return {'maps':maps,'addresses':addresses,'threads':threads,
            'scope':'Only register PC/LR and recorded FP saved LR; no full-unwind claim'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('serial',type=Path);args=p.parse_args()
    data=args.serial.read_bytes();result=extract(data.decode('utf-8','replace'))
    result.update(serial=str(args.serial.resolve()),serial_sha256=hashlib.sha256(data).hexdigest())
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
