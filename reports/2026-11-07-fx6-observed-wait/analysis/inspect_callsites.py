#!/usr/bin/env python3
"""Bounded offline instruction facts for the observed AppFw frame records."""
import hashlib
import io
import json
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from resolve_snapshot import member

ARCHIVE=Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-wait-snapshot-20261107/guest-wait-snapshot295.cpio')
PIN='a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067'

def main():
    data=member(ARCHIVE,'usr/lib/appFw.so')
    if hashlib.sha256(data).hexdigest()!=PIN:raise ValueError('wrong AppFw')
    elf=ELFFile(io.BytesIO(data));disassembly={}
    ranges=((0xc09da0,0xc4),(0x12d9dc0,0x30),(0x12d9fc8,0x80),(0x1acd974,0x20))
    for va,n in ranges:
        segs=[s for s in elf.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']]
        if len(segs)!=1:raise ValueError('ambiguous file-backed PT_LOAD')
        s=segs[0];offset=s['p_offset']+va-s['p_vaddr']
        disassembly[hex(va)]={hex(i.address):i.mnemonic+' '+i.op_str for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(data[offset:offset+n],va)}
    checks={0xc09de4:'bl #0x12d9fc8',0x12da020:'bl #0x12d8174',0x12d9de8:'bl #0x1acd874',0x1acd984:'bl #0xb19e30',0xc09e0c:'bl #0xde31ac'}
    instructions={a:t for r in disassembly.values() for a,t in r.items()}
    for a,t in checks.items():
        if instructions[hex(a)]!=t:raise ValueError('instruction identity mismatch')
    plt=elf.get_section_by_name('.plt');rel=elf.get_section_by_name('.rela.plt');sym=elf.get_section(rel['sh_link'])
    names={plt['sh_addr']+32+16*i:sym.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
    result={'source':{'archive':str(ARCHIVE),'member':'usr/lib/appFw.so','sha256':PIN,'bytes':len(data)},
            'scope':'ELF VA translated through PT_LOAD; these instruction facts do not independently prove execution',
            'verified_calls':{hex(k):v for k,v in checks.items()},'plt_at_observed_wait':names[0xb19e30],
            'disassembly':disassembly}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
