#!/usr/bin/env python3
"""Pin original source windows, table records and produced software descriptors."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM
from tomco_request_guest import AttrGuest,old
HERE=Path(__file__).resolve().parent
def main():
    out=HERE/'source-review.json';assert not out.exists()
    raw=old.SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==old.PIN
    original=HERE/'original-files';original.mkdir(exist_ok=True)
    chunks=HERE/'source-fragments';chunks.mkdir(exist_ok=True)
    cs=Cs(CS_ARCH_ARM,CS_MODE_ARM);cs.skipdata=True
    records=[]
    for lo,hi in [(0x553d48,0x553fb8),(0x553fe8,0x554244),
        (0x54ad18,0x54aec8),(0x54aecc,0x54b230),(0x54b230,0x54b3b4),
        (0x54a828,0x54a9d0),(0x569f74,0x569f9c),(0x546984,0x546d04),
        (0x54b4b8,0x54b528),(0x555010,0x555174),(0x555174,0x555390),
        (0x556204,0x556218),(0x554610,0x554954)]:
        data=raw[lo-old.BASE:hi-old.BASE]
        f=chunks/f'{lo:08x}-{hi:08x}.txt';assert not f.exists()
        f.write_text('\n'.join(f'{i.address:08x} {i.bytes.hex():12s} {i.mnemonic} {i.op_str}'
            for i in cs.disasm(data,lo))+'\n')
        records.append(dict(VA=hex(lo),end_exclusive=hex(hi),bytes=len(data),
            original_bytes_sha256=hashlib.sha256(data).hexdigest(),listing=str(f.relative_to(HERE)),
            scope='Linear bounded original-byte listing; embedded words/.byte are not independently reachable instructions.'))
    table=raw[0xd22a84-old.BASE:0xd22a84-old.BASE+19*20]
    f=original/'CP-region-table.bin';assert not f.exists();f.write_bytes(table)
    rows=[]
    for i in range(19):
        words=struct.unpack_from('<5I',table,i*20);at=words[3]-old.BASE
        assert 0<=at<len(raw)
        end=raw.index(b'\0',at,at+200)
        rows.append(dict(index=i,words=list(map(hex,words)),original_name=raw[at:end].decode('ascii')))
    class CaptureGuest(AttrGuest):
        def __init__(self,raw):
            self.region_calls=[]
            super().__init__(raw)
        def code(self,u,pc,size,user):
            if pc==0x554610:
                sp=u.reg_read(old.R.UC_ARM_REG_SP)
                self.region_calls.append(dict(PC=hex(pc),register_arguments=[hex(u.reg_read(getattr(old.R,f'UC_ARM_REG_R{i}'))) for i in range(4)],
                    stack_arguments=list(map(hex,struct.unpack('<3I',bytes(u.mem_read(sp,12)))))))
            super().code(u,pc,size,user)
    def entries(g,label):
        return dict(stage=label,entries=[dict(index=hex(i),VA=hex(i<<20),descriptor=hex(g.words(0x14e8000+i*4,1)[0]))
            for i in [0,1,0x8f,0x90,0x9a,0xff,0x100]])
    g=CaptureGuest(raw)
    boot=g.call(0x1083a4,stops={0x108728:'before_CPU_setup_call'});assert boot['boundary']['PC']=='0x108728'
    states=[entries(g,'original_bootstrap_before_CPU_setup')]
    init=g.call(0x553d48,[old.ROOT]);assert init['boundary']['reason']=='returned'
    states.append(entries(g,'software_initializer_returned_RAM_only'))
    assert g.call(0x54ad3c,stops={0x54ae54:'before_original_mutex_initializer_call'})['boundary']['PC']=='0x54ae54'
    assert g.call(0x54ae5c,stops={0x54b3b4:'before_following_cache_helper'})['boundary']['PC']=='0x54b3b4'
    states.append(entries(g,'original_region_fragment_RAM_only'))
    assert g.call(0x54b4b8,[0x9000000,0x7000000,0x20000020])['boundary']['reason']=='returned'
    states.append(entries(g,'CPU_disabled_attribute_projection_only'))
    record=dict(CP_sha256=old.PIN,source_fragments=records,
        original_region_table=dict(VA='0xd22a84',record_stride=20,record_count=19,
            provider='0x569f74',stride_instruction='0x54b21c: add r7,r0,#0x14',
            bytes=len(table),sha256=hashlib.sha256(table).hexdigest(),records=rows),
        following_optional_table_provider=dict(VA='0x569f8c',original_return_pointer=0,original_return_count=0),
        original_region_mapping_calls=g.region_calls,software_L1_snapshots=states,
        scope='Source records are original file bytes; software snapshots are model output only. The original CPU-maintenance-disabled call is an explicit different argument, not the TOMCO call. No full boot, physical mapping, DmmCfg candidate load, buffer or RAW pixels is proved.')
    out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(fragments=len(records),region_records=len(rows),original_region_map_calls=len(g.region_calls),snapshots=states)))
if __name__=='__main__':main()
