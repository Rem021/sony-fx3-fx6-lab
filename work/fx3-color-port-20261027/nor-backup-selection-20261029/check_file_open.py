#!/usr/bin/env python3
"""Verify this NOR build's ordinary file-open returns, without file-result stubs."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from backup_state_guest import Guest,inputs,old,R
HERE=Path(__file__).resolve().parent
HEAP=0x500000000;DIAG=0xfe20c000;FILE_CONTEXT=0xfe062678
class FileGuest(Guest):
    def __init__(self,raw,record):
        super().__init__(raw,record)
        self.u.mem_map(HEAP,0x10000);self.u.mem_write(HEAP,b'\xcc'*0x10000)
        self.u.mem_map(DIAG,0x1000,old.UC_PROT_READ);self.u.mem_write(DIAG,b'\0'*8)
        # Explicit model inputs, not recovered live BSS or original boot setup:
        # an empty file context, a bounded ordinary allocator free list, and two
        # diagnostic thresholds0. Allocation/free and diagnostics execute their
        # original instructions; no function return is supplied by a hook.
        ctype=0xfe06147d
        assert all(raw[ctype-old.BASE+c]&8 for c in range(ord('a'),ord('z')+1))
        assert all(not(raw[ctype-old.BASE+c]&8) for c in range(ord('A'),ord('Z')+1))
        for address,data in [(FILE_CONTEXT,bytes(0x20)),(0xfe061e00,struct.pack('<Q',HEAP)),
            (0xfe061e18,struct.pack('<Q',ctype))]:
            self.u.mem_write(address,data);self.initialized[address-old.BASE:address-old.BASE+len(data)]=b'\1'*len(data)
        self.u.mem_write(HEAP,struct.pack('<2Q',0,HEAP+0x100))
        self.u.mem_write(HEAP+0x100,struct.pack('<2Q',0xff00,0))
        self.original_calls=[]
    def read(self,u,access,at,size,value,user):
        if HEAP<=at and at+size<=HEAP+0x10000:return
        if DIAG<=at and at+size<=DIAG+8:return
        super().read(u,access,at,size,value,user)
    def write(self,u,access,at,size,value,user):
        if HEAP<=at and at+size<=HEAP+0x10000:self.writes+=1;return
        if FILE_CONTEXT<=at and at+size<=FILE_CONTEXT+0x20:
            self.initialized[at-old.BASE:at-old.BASE+size]=b'\1'*size;self.writes+=1;return
        super().write(u,access,at,size,value,user)
    def code(self,u,pc,size,user):
        if pc in [0xfe04a3b0,0xfe04a490,0xfe0561b4,0xfe058178,0xfe057fa0]:self.original_calls.append(hex(pc))
        super().code(u,pc,size,user)
def main():
    out=HERE/'file-open-original-results.json';assert not out.exists()
    raw,record,source,bank=inputs();cases=[]
    paths=['\\DmmCfg.bin','\\NoSuch.bin','\\updater\\mode']
    for path in paths:
        g=FileGuest(raw,record);at=old.OUT+0x100;g.u.mem_write(at,path.encode()+b'\0')
        result=g.call(0xfe057fa0,[at])
        assert result['boundary']['reason']=='returned' and result['registers'][0]=='0xfffffe68'
        assert '0xfe058178' not in g.original_calls
        cases.append(dict(path=path,result=result,original_function_entries=g.original_calls,
            file_query_or_block_data_reply_supplied=False,original_byte_stream_reader_entered=False))
    result=dict(NOR_sha256=old.PIN,entry='0xfe057fa0',cases=cases,
        declared_environment_inputs=dict(file_context='Empty32B at0xfe062678',heap='64KiB model RAM and a free-list context',
            ctype='Explicit pointer0xfe06147d into the unchanged original character-classification bytes; not a recovered live locale pointer.',
            diagnostic_thresholds='Two explicit zero words; original diagnostic gating runs without emitting output.'),
        scope='No original function is replaced or supplied a successful return. Original file-open/allocator/name-conversion/diagnostic instructions run in a declared software environment. No filesystem is mounted, no FAT sector/file reply supplied, no source instruction modified, and no native/device action. Ordinary return -408 belongs to this pinned NOR build, not every Sony loader or all camera boot routes.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(path=x['path'],R0=x['result']['registers'][0],instructions=x['result']['original_instructions']) for x in cases]))
if __name__=='__main__':main()
