#!/usr/bin/env python3
"""Read SKD candidates through original WBI page tables and cross-check metadata."""
from hashlib import sha256
import json,io
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from wbi_page_table_candidates import Snapshot,HERE


def main():
    mapping=json.loads((HERE/'wbi-page-table-candidates.json').read_bytes())
    chains=[c for c in mapping['chains'] if c['header_roundtrip_matches']];assert len(chains)==1
    chain=chains[0];root=int(chain['root_physical_address'],16);base=int(chain['userspace_va_candidate'],16)
    snapshot=Snapshot();lib=(HERE/'libraries/libInfraSKD.so').read_bytes();metadata=[]
    elf=ELFFile(io.BytesIO(lib));dynsym=elf.get_section_by_name('.dynsym');dynstr=elf.get_section_by_name('.dynstr').data()
    # Protection moved/extended the on-disk dynamic tables. The snapshot has the
    # original 144-entry prefix at 0x198 and original strings at 0xf18. Do not
    # assume that the protected relocated table pages remain mapped in memory.
    tests=[('ELF_header',0,lib[:0x150]),('GNU_hash',0x158,lib[0x158:0x194]),
           ('original_144_dynamic_symbols',0x198,dynsym.data()[:144*24]),
           ('original_dynamic_string_prefix',0xf18,dynstr[:1024]),
           ('original_SONAME',0xf18+0x5c4,b'libInfraSKD.so\0')]
    for name,offset,expected in tests:
        size=len(expected)
        try:
            got=snapshot.virtual(root,base+offset,size);match=got==expected
            row=dict(name=name,relative_va=hex(offset),bytes=size,match=match,sha256=sha256(got).hexdigest())
        except ValueError as error:row=dict(name=name,relative_va=hex(offset),bytes=size,match=False,error=str(error))
        metadata.append(row)
    (HERE/'skd-snapshot-identity-checks.json').write_text(json.dumps(metadata,indent=2)+'\n')
    assert all(row['match'] for row in metadata),'Additional ELF identity checks failed; do not label function bytes as SKD'
    symbols=json.loads((HERE/'skd-library-inventory.json').read_bytes())['symbols'];rows=[]
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);md.skipdata=True
    out=HERE/'snapshot-fragments';out.mkdir(exist_ok=True)
    for symbol in symbols:
        if symbol['type']!='STT_FUNC' or symbol['section']=='SHN_UNDEF' or not symbol['bytes']:continue
        va=int(symbol['va'],16);size=symbol['bytes']
        matched=[(i,s) for i,s in enumerate(dynsym.iter_symbols()) if s.name==symbol['name']]
        assert len(matched)==1
        index,record=matched[0];assert index<144
        actual_record=snapshot.virtual(root,base+0x198+index*24,24)
        assert actual_record==dynsym.data()[index*24:(index+1)*24]
        actual_name=snapshot.virtual(root,base+0xf18+record['st_name'],len(symbol['name'])+1)
        assert actual_name==symbol['name'].encode()+b'\0'
        try:
            data=snapshot.virtual(root,base+va,size)
            dest=out/(symbol['name']+'.bin');assert not dest.exists();dest.write_bytes(data)
            instructions=list(md.disasm(data,va))
            text='\n'.join(f'{ins.address:08x} {ins.mnemonic:9} {ins.op_str}' for ins in instructions)+'\n'
            asm=HERE/'disassembly'/('snapshot-'+symbol['name']+'.txt');asm.write_text(text)
            rows.append(dict(symbol=symbol,read_success=True,sha256=sha256(data).hexdigest(),
                same_as_original_file=data==lib[va:va+size],same_entry_stub=data[:8]==lib[va:va+8],symbol_record_and_name_match=True,
                decoded_instructions=sum(i.mnemonic!='.byte' for i in instructions),data_bytes=sum(i.size for i in instructions if i.mnemonic=='.byte'),
                output=str(dest.relative_to(HERE)),disassembly=str(asm.relative_to(HERE))))
        except ValueError as error:rows.append(dict(symbol=symbol,read_success=False,error=str(error)))
    result=dict(status='PASS_SNAPSHOT_SAME_ELF_METADATA_CROSSCHECK',source_sha256=snapshot.meta['source_sha256'],
        original_library_sha256=sha256(lib).hexdigest(),root_physical_address=hex(root),library_base_candidate=hex(base),
        metadata=metadata,functions=rows,
        scope='Original offline WBI snapshot only. ELF header, GNU hash, 144 complete original symbol records, 1024 string bytes, SONAME, and each selected symbol name/value/size agree through one 39-bit page-table chain. This supports snapshot library identity and function locations, not live process identity, current FX3 state, function execution or update admission. Function changes and instruction decoding are recorded separately.')
    (HERE/'skd-snapshot-code-results.json').write_text(json.dumps(result,indent=2)+'\n');snapshot.close()
    for row in rows:print(row['symbol']['name'],{k:v for k,v in row.items() if k not in ('symbol','sha256','output','disassembly')})


if __name__=='__main__':main()
