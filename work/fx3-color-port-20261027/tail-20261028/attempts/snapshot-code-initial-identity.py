#!/usr/bin/env python3
"""Read SKD candidates through original WBI page tables and cross-check metadata."""
from hashlib import sha256
import json
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from wbi_page_table_candidates import Snapshot,HERE


def main():
    mapping=json.loads((HERE/'wbi-page-table-candidates.json').read_bytes())
    chains=[c for c in mapping['chains'] if c['header_roundtrip_matches']];assert len(chains)==1
    chain=chains[0];root=int(chain['root_physical_address'],16);base=int(chain['userspace_va_candidate'],16)
    snapshot=Snapshot();lib=(HERE/'libraries/libInfraSKD.so').read_bytes();metadata=[]
    # Independent immutable ELF regions, across widely separated virtual pages.
    for name,offset,size in [('ELF_header_and_phdrs',0,0x150),('GNU_hash',0x158,60),('dynamic_strings',0x2ce9a8,1594)]:
        try:
            got=snapshot.virtual(root,base+offset,size);match=got==lib[offset:offset+size]
            row=dict(name=name,relative_va=hex(offset),bytes=size,match=match,sha256=sha256(got).hexdigest())
        except ValueError as error:row=dict(name=name,relative_va=hex(offset),bytes=size,match=False,error=str(error))
        metadata.append(row)
    assert all(row['match'] for row in metadata),'Additional ELF identity checks failed; do not label function bytes as SKD'
    symbols=json.loads((HERE/'skd-library-inventory.json').read_bytes())['symbols'];rows=[]
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);md.skipdata=True
    out=HERE/'snapshot-fragments';out.mkdir(exist_ok=True)
    for symbol in symbols:
        if symbol['type']!='STT_FUNC' or symbol['section']=='SHN_UNDEF' or not symbol['bytes']:continue
        va=int(symbol['va'],16);size=symbol['bytes']
        try:
            data=snapshot.virtual(root,base+va,size)
            dest=out/(symbol['name']+'.bin');assert not dest.exists();dest.write_bytes(data)
            instructions=list(md.disasm(data,va))
            text='\n'.join(f'{ins.address:08x} {ins.mnemonic:9} {ins.op_str}' for ins in instructions)+'\n'
            asm=HERE/'disassembly'/('snapshot-'+symbol['name']+'.txt');asm.write_text(text)
            rows.append(dict(symbol=symbol,read_success=True,sha256=sha256(data).hexdigest(),
                same_as_original_file=data==lib[va:va+size],same_entry_stub=data[:8]==lib[va:va+8],
                decoded_instructions=sum(i.mnemonic!='.byte' for i in instructions),data_bytes=sum(i.size for i in instructions if i.mnemonic=='.byte'),
                output=str(dest.relative_to(HERE)),disassembly=str(asm.relative_to(HERE))))
        except ValueError as error:rows.append(dict(symbol=symbol,read_success=False,error=str(error)))
    result=dict(status='PASS_SNAPSHOT_SAME_ELF_METADATA_CROSSCHECK',source_sha256=snapshot.meta['source_sha256'],
        original_library_sha256=sha256(lib).hexdigest(),root_physical_address=hex(root),library_base_candidate=hex(base),
        metadata=metadata,functions=rows,
        scope='Original offline WBI snapshot only. Three independent original ELF regions match through a candidate 39-bit page-table chain. This is evidence for candidate library identity, not live process identity, current FX3 state, function execution or update admission. Function changes are reported without assuming successful decryption.')
    (HERE/'skd-snapshot-code-results.json').write_text(json.dumps(result,indent=2)+'\n');snapshot.close()
    for row in rows:print(row['symbol']['name'],{k:v for k,v in row.items() if k not in ('symbol','sha256','output','disassembly')})


if __name__=='__main__':main()
