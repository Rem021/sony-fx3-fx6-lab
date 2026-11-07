#!/usr/bin/env python3
"""Read-only binding: actual FX6 ELF + existing checked BK4 parser, four IDs only."""
import hashlib
import importlib.util
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

DONOR = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor')
KEYS = (0xfa0191, 0xfa0192, 0xfa01a3, 0xfa01a4)
PINS = {
 'appFw.so':'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
 'libbackup.so':'e003e2d8a1f42fdf629dda012a01f225940c016b2ab4dbf482a761378e8d286f',
}

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def insns(elf, address, size):
    for segment in elf.iter_segments():
        if segment['p_type']=='PT_LOAD' and segment['p_vaddr'] <= address and address+size <= segment['p_vaddr']+segment['p_filesz']:
            elf.stream.seek(segment['p_offset']+address-segment['p_vaddr'])
            return {i.address:f'{i.mnemonic} {i.op_str}'.rstrip() for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(elf.stream.read(size),address)}
    raise ValueError('VA range outside file-backed segment')

def main():
    receipts={}
    for name,pinned in PINS.items():
        path=DONOR/'nflasha15-files/lib'/name
        actual=digest(path)
        if actual!=pinned: raise ValueError(f'SHA mismatch: {name}')
        receipts[name]={'path':str(path),'sha256':actual,'size':path.stat().st_size}
    path=DONOR/'backup-state-binding/parse_bk4.py'
    spec=importlib.util.spec_from_file_location('checked_bk4',path)
    parser=importlib.util.module_from_spec(spec); spec.loader.exec_module(parser)
    records=[]
    source,sha=parser.SOURCES['fx6_chaplin_ntsc']
    for key in KEYS:
        parsed=parser.parse_file(source,sha,key)
        assert len(parsed['records'])==2
        for index,record in enumerate(parsed['records']):
            selected=record['selected']
            assert selected['present'] and selected['length']==selected['max_length']==8
            raw=bytes.fromhex(selected['raw_hex'])
            records.append({'record_index':index,'id':hex(key),'record_file_offset':record['record_file_offset'],
                'data_file_offset':selected['data_file_offset'],'length':8,'max_length':8,
                'attribute':selected['attribute'],'checksum_matches':record['checksum_matches'],
                'all_entry_bounds_checked':record['all_entry_bounds_checked'],
                'raw_hex':raw.hex(),'u64_le':hex(int.from_bytes(raw,'little')),
                'all_ones_sentinel':raw==b'\xff'*8})
    # Check all five pinned regional templates; these four keys agree per record.
    for name,(regionpath,regionsha) in parser.SOURCES.items():
        if not name.startswith('fx6_'): continue
        for key in KEYS:
            other=parser.parse_file(regionpath,regionsha,key)
            for index,record in enumerate(other['records']):
                baseline=next(x for x in records if x['record_index']==index and x['id']==hex(key))
                assert record['selected']['raw_hex']==baseline['raw_hex']
                assert record['selected']['length']==record['selected']['max_length']==8
    with (DONOR/'nflasha15-files/lib/libbackup.so').open('rb') as handle:
        elf=ELFFile(handle)
        checks={
            0x1e18:'mov w2, #-1', 0x1e1c:'mov x5, x1', 0x1e20:'mov w4, w0',
            0x1e30:'mov w3, #2', 0x1e3c:'mov w2, #3',
            0x1e48:'ldr w0, [x29, #0x1c]',
            0x2534:'sxtw x6, w2',
            0x1b24:'cbnz w0, #0x1b30', 0x1b28:'ldr w0, [x19, #4]',
            0x1b2c:'str w0, [x21]', 0x1b44:'mov w0, #0',
        }
        actual={}
        for address,expected in checks.items():
            actual[address]=insns(elf,address,4)[address]
            assert actual[address]==expected,(hex(address),actual[address],expected)
        symbols={}
        for name in ('Backup_read','Backup_nread','Backup_get_datasize','Backup_read_8Byte','backup_sync_msg'):
            symbol=elf.get_section_by_name('.dynsym').get_symbol_by_name(name)[0]
            symbols[name]={'va':hex(symbol['st_value']),'bytes':symbol['st_size']}
    with (DONOR/'nflasha15-files/lib/appFw.so').open('rb') as handle:
        elf=ELFFile(handle)
        plt=elf.get_section_by_name('.plt');rel=elf.get_section_by_name('.rela.plt')
        symtab=elf.get_section(rel['sh_link'])
        slots={plt['sh_addr']+32+16*i:symtab.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
        assert slots[0xb19370]=='Backup_read_8Byte'
        calls={}
        for addr,key in ((0xc0b294,0xfa0191),(0xc0b2f4,0xfa0192),(0x1395d00,0xfa01a3),(0x1395d18,0xfa01a4)):
            assert insns(elf,addr,4)[addr]=='bl #0xb19370'
            calls[hex(addr)]={'id':hex(key),'target':'Backup_read_8Byte'}
        # Check register construction immediately before 191/1a3 and 192/1a4.
        for addr,expected in ((0xc0b28c,'mov w0, #0x191'),(0xc0b290,'movk w0, #0xfa, lsl #16'),
            (0xc0b2dc,'mov w0, #0x192'),(0xc0b2e4,'movk w0, #0xfa, lsl #16'),
            (0x1395cf8,'mov w0, #0x1a3'),(0x1395cfc,'movk w0, #0xfa, lsl #16'),
            (0x1395d10,'mov w0, #0x1a4'),(0x1395d14,'movk w0, #0xfa, lsl #16')):
            assert insns(elf,addr,4)[addr]==expected
    result={'status':'PASS','scope':'Offline four-ID type/size binding; no native Backup execution or VM',
        'sources':receipts,'template':{'path':str(source),'sha256':sha,'records':records,
        'regional_agreement':'all five pinned FX6 CHAPLIN templates, same four IDs per record'},
        'libbackup_symbols':symbols,'instruction_contract_checks':{hex(k):v for k,v in actual.items()},
        'appFw_calls':calls,'constraints':[
            'Raw template absolute addresses are not current-process allocation capabilities.',
            'record0 is default AP per prior backup.ko analysis, not a live/current camera value.',
            'Private Backup_read result status is not equated to helper status or sync function return.',
            'Physical a3/a4 pair has all-ones template values; mapping remains unproved.'
        ],'external_abi_source':'https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst'}
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
