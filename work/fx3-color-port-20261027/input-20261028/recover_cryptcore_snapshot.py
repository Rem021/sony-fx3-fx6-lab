#!/usr/bin/env python3
"""Recover two original protected CryptoCore exports from the original offline snapshot."""
from pathlib import Path
from hashlib import sha256
import io,json,sys
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from elftools.elf.elffile import ELFFile

HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'tail-20261028'
sys.path.insert(0,str(PREV))
from wbi_page_table_candidates import Snapshot


def main():
    source=HERE.parent/'package-20261028/libraries/libInfraCryptCore.so';raw=source.read_bytes()
    previous=json.loads((source.parents[1]/'final-receipt.json').read_bytes())
    old=next(row for row in previous['files'] if row['path']=='libraries/libInfraCryptCore.so');assert sha256(raw).hexdigest()==old['sha256']
    identity=json.loads((PREV/'skd-snapshot-code-results.json').read_bytes());root=int(identity['root_physical_address'],16)
    modules=json.loads((PREV/'snapshot-link-map-inventory.json').read_bytes())['modules']
    module=next(m for m in modules if m['name']=='/usr/lib/libInfraCryptCore.so');base=int(module['base'],16)
    elf=ELFFile(io.BytesIO(raw));symbols=elf.get_section_by_name('.dynsym');strings=elf.get_section_by_name('.dynstr').data()
    assert symbols.num_symbols()==186
    original_count=174;symbol_va=0x198;string_va=symbol_va+original_count*24
    soname=next(tag.entry.d_val for tag in elf.get_section_by_name('.dynamic').iter_tags() if tag.entry.d_tag=='DT_SONAME')
    expected_name=strings[soname:].split(b'\0')[0]+b'\0';assert expected_name==b'libInfraCryptCore.so\0'
    hashsec=elf.get_section_by_name('.gnu.hash');snapshot=Snapshot();checks=[]
    for name,va,expected in [('ELF_header',0,raw[:0x150]),('GNU_hash',hashsec['sh_addr'],hashsec.data()),
            ('original_174_dynamic_records',symbol_va,symbols.data()[:original_count*24]),
            ('original_string_prefix',string_va,strings[:1024]),('original_SONAME',string_va+soname,expected_name)]:
        got=snapshot.virtual(root,base+va,len(expected));match=got==expected
        checks.append(dict(name=name,va=hex(va),bytes=len(expected),match=match,sha256=sha256(got).hexdigest()))
    (HERE/'cryptcore-snapshot-identity.json').write_text(json.dumps(checks,indent=2)+'\n');assert all(c['match'] for c in checks)
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);md.skipdata=True;out=HERE/'snapshot-fragments';out.mkdir(exist_ok=True)
    asm=HERE/'disassembly';asm.mkdir(exist_ok=True);functions=[]
    for index,sym in enumerate(symbols.iter_symbols()):
        if sym.name not in ('iCryptCore_main','icc_verifyDataCore'):continue
        assert index<original_count
        name=snapshot.virtual(root,base+string_va+sym['st_name'],len(sym.name)+1);assert name==sym.name.encode()+b'\0'
        va=sym['st_value'];size=sym['st_size'];data=snapshot.virtual(root,base+va,size)
        instructions=list(md.disasm(data,va));dest=out/(sym.name+'.bin');assert not dest.exists();dest.write_bytes(data)
        text='\n'.join(f'{i.address:08x} {i.mnemonic:9} {i.op_str}' for i in instructions)+'\n';(asm/(sym.name+'.txt')).write_text(text)
        functions.append(dict(name=sym.name,va=hex(va),bytes=size,sha256=sha256(data).hexdigest(),output=str(dest.relative_to(HERE)),
            same_as_protected_file=data==raw[va:va+size],decoded_instructions=sum(i.mnemonic!='.byte' for i in instructions),
            undecoded_bytes=sum(i.size for i in instructions if i.mnemonic=='.byte')))
    assert len(functions)==2
    result=dict(status='PASS_ORIGINAL_CRYPTCORE_SNAPSHOT_EXPORTS_RECOVERED',source=str(source),source_sha256=sha256(raw).hexdigest(),
        snapshot_source_sha256=snapshot.meta['source_sha256'],root_physical_address=hex(root),module=module,identity=checks,functions=functions,
        scope='Static original snapshot reads only. Five independent metadata spans and original symbol names/values/sizes agree. No CryptoCore, SKD, ROM/MMIO, signing, updater, camera or device execution; connection to FDAT tail still requires actual caller evidence.')
    (HERE/'cryptcore-snapshot-results.json').write_text(json.dumps(result,indent=2)+'\n');snapshot.close()
    for function in functions:print(function['name'],function['bytes'],'bytes','decoded_instructions',function['decoded_instructions'],'undecoded_bytes',function['undecoded_bytes'],flush=True)


if __name__=='__main__':main()
