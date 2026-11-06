#!/usr/bin/env python3
"""Original NOR low-level argument gates, without providing controller state."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from probe_bulk_load import old
HERE=Path(__file__).resolve().parent
def main():
    out=HERE/'NOR-reader-guard-results.json';assert not out.exists()
    raw,record,source,bank=old.inputs();cases=[]
    for name,offset,size in [('offset_outside_64MiB',0x4000000,4),('length_above_64MiB',0,0x4000001),
        ('zero_length',0,0),('valid_range_without_controller_state',0,4)]:
        g=old.Guest(raw,record);r=g.call(0xfe04fab0,[0x10000000,offset,size])
        if name in ['offset_outside_64MiB','length_above_64MiB']:
            assert r['boundary']['reason']=='returned' and r['registers'][0]=='0x3'
        elif name=='zero_length':assert r['boundary']['reason']=='returned' and r['registers'][0]=='0x0'
        else:assert r['boundary']['reason']=='before_unknown_RAM_read' and r['boundary']['address']=='0xfe061eea'
        assert r['nonstack_RAM_writes']==0
        cases.append(dict(name=name,result=r,controller_or_flash_data_supplied=False,physical_destination_written=False))
    record=dict(NOR_sha256=hashlib.sha256(raw).hexdigest(),entry='0xfe04fab0',cases=cases,
        scope='Original argument-validation and zero-length paths only; valid nonzero request stops at unknown controller context. Return0 for zero bytes is not a completed flash copy. No registers, storage contents, native Sony program or actual camera action.')
    out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps([dict(name=x['name'],boundary=x['result']['boundary'],R0=x['result']['registers'][0]) for x in cases]))
if __name__=='__main__':main()
