#!/usr/bin/env python3
"""Resolve original-file unit extent through original config lookup helpers."""
import hashlib,json,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from config_guest import Guest as ParserGuest,image,BASE,PIN,words

class Guest(ParserGuest):
    def code(self,u,pc,size,user):
        if 0xab8e9a<=pc<0xab8f0a:self.instructions+=1;return
        return super().code(u,pc,size,user)

def main():
    target=HERE/'extent-config-results.json';assert not target.exists()
    source=(HERE/'original-files/DmmCfg.bin').read_bytes();g=Guest(image(),source)
    assert g.call(0xab8b70)['raw_r0']=='0x0' and g.call(0xaba7b6)['raw_r0']=='0x0'
    unit=next(r for r in g.unit_table() if r['key']=='0x4af');extents=[]
    root=g.call(0xab8ea6);base=int(root['raw_r0'],16);assert base==0x1da7968
    for ID in unit['extent_IDs']:
        value=int(ID,16);count_call=g.call(0xab8ef2,[value]);count=int(count_call['raw_r0'],16)
        assert 0<count<=200
        mappings=[]
        for i in range(count):
            lookup=g.call(0xab8eb2,[value,i]);index=int(lookup['raw_r0'],16);assert index<1024
            address=base+index*0x50;header=bytes(g.u.mem_read(address,0x50));ptr=struct.unpack_from('<I',header)[0]
            records=[]
            for j in range(3074):
                b=bytes(g.u.mem_read(ptr+j*0x14,0x14));key=struct.unpack_from('<I',b,8)[0]
                if key==0xffffffff:break
                if key==value:
                    # Raw field meanings are restricted to what original
                    # ab75f6 and later extent-return source actually consume.
                    records.append(dict(address=hex(ptr+j*0x14),bytes_hex=b.hex(),
                        raw_word0=hex(struct.unpack_from('<I',b,0)[0]),raw_u16_4=hex(struct.unpack_from('<H',b,4)[0]),
                        raw_u16_6=hex(struct.unpack_from('<H',b,6)[0]),extent_ID=hex(key),
                        raw_wordC=hex(struct.unpack_from('<I',b,0xc)[0]),raw_word10=hex(struct.unpack_from('<I',b,0x10)[0])))
            else:raise AssertionError('original extent list unbounded')
            assert records
            mappings.append(dict(original_lookup=lookup,region_index=index,region_record_address=hex(address),
                region_record_hex=header.hex(),region_raw_u16_4=hex(struct.unpack_from('<H',header,4)[0]),
                region_raw_u16_6=hex(struct.unpack_from('<H',header,6)[0]),
                region_raw_word8=hex(struct.unpack_from('<I',header,8)[0]),region_raw_wordC=hex(struct.unpack_from('<I',header,0xc)[0]),
                matching_extent_records=records))
        extents.append(dict(extent_ID=ID,original_mapping_count=count_call,mappings=mappings))
    out=dict(cp_sha256=PIN,configuration_file_sha256=hashlib.sha256(source).hexdigest(),original_unit=unit,
        original_region_base_lookup=root,extents=extents,configuration_parse_bytes=g.offset,
        file_read_adapter='Same explicit sequential original-file adapter; normal filename/boot/parameter mapping still unproven.',
        scope='Original lookup count/index/root helpers execute over original parsed configuration. Raw group/extent fields are saved without assuming live memory mapping, allocated buffers, pixels, cache-chip identity or cross-model ABI compatibility. No image allocator, IPC, kernel, native Sony execution or device action.')
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(unit=unit['key'],extents=[dict(ID=e['extent_ID'],mappings=len(e['mappings'])) for e in extents],
        records=[m for e in extents for m in e['mappings']]),indent=2))

if __name__=='__main__':main()
