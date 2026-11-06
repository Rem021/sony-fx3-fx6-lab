#!/usr/bin/env python3
"""Original descriptor consumer up to FAT mount/open gates, without I/O replies."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from nor_descriptor_guest import Guest,BASE,BACKUP,OUT,PIN,R
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
class PrefixGuest(Guest):
    def code(self,u,pc,size,user):
        if pc in [0xfe057f0c,0xfe057fa0]:
            self.stop('before_original_FAT_mount' if pc==0xfe057f0c else 'before_original_file_open',
                arguments=[hex(u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))) for i in range(4)],
                file_or_device_reply_supplied=False)
            return
        super().code(u,pc,size,user)
def main():
    out=HERE/'NOR-load-prefix-results.json';assert not out.exists()
    raw=(HERE/'original-files/loader_nor.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
    source=json.loads((HERE/'load-descriptor-sources.json').read_text())
    bank=next(x for x in source['templates'] if x['member']==source['canonical_template'])['banks'][1]
    record=(TASK/'dmm-backup-20261029/original-records/canonical-bank1.bin').read_bytes()
    assert hashlib.sha256(record).hexdigest()==bank['record_sha256']
    g=PrefixGuest(raw,record)
    init=g.call(0xfe04d63c,[BACKUP]);assert init['boundary']['reason']=='returned'
    query=g.call(0xfe04c7b4,[0xfa0080,OUT]);assert query['registers'][0]=='0x2400'
    descriptor=OUT+3*144;entry=bytes(g.u.mem_read(descriptor,144))
    original=(HERE/'original-files/bank1-fa0080.bin').read_bytes()[3*144:4*144];assert entry==original
    start,end,partition,mode=struct.unpack_from('<2Q2I',entry)
    path=entry[24:].split(b'\0',1)[0].decode();assert path=='\\DmmCfg.bin'
    g.u.reg_write(R.UC_ARM64_REG_X27,descriptor)
    prefix=g.call(0xfe054794)
    assert prefix['boundary']['reason']=='before_original_FAT_mount' and prefix['registers'][0]=='0x8'
    loaded_registers=dict(start_X26=hex(g.u.reg_read(R.UC_ARM64_REG_X26)),end_X25=hex(g.u.reg_read(R.UC_ARM64_REG_X25)))
    assert loaded_registers==dict(start_X26=hex(start),end_X25=hex(end))
    # A separate original wrapper call with the exact observed descriptor inputs.
    # It does not imply the preceding FAT mount succeeded.
    wrapper=g.call(0xfe057e98,[descriptor+24,start])
    assert wrapper['boundary']['reason']=='before_original_file_open'
    dest=hex(g.u.reg_read(R.UC_ARM64_REG_X21));assert dest==hex(start)
    result=dict(NOR_source_sha256=PIN,original_initializer=init,original_descriptor_query=query,
        descriptor_index=3,descriptor_sha256=hashlib.sha256(entry).hexdigest(),original_path=path,
        descriptor_values=dict(start=hex(start),end=hex(end),partition=partition,mode=hex(mode),inclusive_capacity=end-start+1),
        original_consumer_fragment=prefix,original_loaded_registers=loaded_registers,
        separate_original_file_wrapper=wrapper,destination_preserved_in_X21=dest,
        scope='The descriptor is copied by the original NOR query from an explicit official BK4 record. The original consumer fragment stops before FAT mount; a separate original wrapper call stops before file open. No mount success, file result, block data or native/device action is supplied. No configuration bytes are written to the physical/CP candidate.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(descriptor=result['descriptor_values'],path=path,prefix=prefix['boundary'],wrapper=wrapper['boundary'],destination=dest)))
if __name__=='__main__':main()
