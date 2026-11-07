#!/usr/bin/env python3
"""Feed SHA/checksum/bounds-verified real four-key metadata to the C helper."""
import ctypes as C
import json
from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent

class Item(C.Structure):
    _fields_=[('id',C.c_uint32),('length',C.c_size_t),('bytes',C.c_ubyte*8)]
class Record(C.Structure):
    _fields_=[('record_index',C.c_size_t),('item_count',C.c_size_t),('items',Item*4)]

def main():
    receipt=json.loads(subprocess.check_output(['python3','-B',str(HERE/'inspect_contract.py')]))
    lib=C.CDLL(str(HERE/'libtyped_backup_reader.dylib'))
    read=lib.fx6_template_read_u64
    read.argtypes=[C.POINTER(Record),C.c_uint32,C.c_void_p,C.c_size_t]
    read.restype=C.c_int
    checks=0
    for index in range(2):
        r=Record();r.record_index=index;r.item_count=4
        facts=[x for x in receipt['template']['records'] if x['record_index']==index]
        assert len(facts)==4
        for i,fact in enumerate(facts):
            r.items[i].id=int(fact['id'],16);r.items[i].length=fact['length']
            r.items[i].bytes[:]=bytes.fromhex(fact['raw_hex'])
        for fact in facts:
            guard=(C.c_ubyte*32)(*([0xa5]*32));out=C.byref(guard,7)
            assert read(C.byref(r),int(fact['id'],16),out,8)==0
            value=int.from_bytes(bytes(guard)[7:15],__import__('sys').byteorder)
            assert value==int(fact['u64_le'],16)
            assert bytes(guard)[:7]==b'\xa5'*7 and bytes(guard)[15:]==b'\xa5'*17
            checks+=3
            for size in (0,1,4,7,9,16,0x77ffd4e0):
                before=bytes(guard)
                assert read(C.byref(r),int(fact['id'],16),out,size)==2
                assert bytes(guard)==before;checks+=2
        guard=(C.c_ubyte*32)(*([0xa5]*32))
        assert read(C.byref(r),0xdeadbeef,C.byref(guard,7),8)==1
        assert bytes(guard)==b'\xa5'*32;checks+=2
    print(json.dumps({'status':'PASS','checks':checks,'real_records':2,'real_keys_per_record':4,
        'scope':'host C helper fed from pinned BYOF metadata; no native Backup execution'}))
if __name__=='__main__': main()
