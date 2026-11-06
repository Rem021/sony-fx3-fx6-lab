"""Static ET_REL sections/functions and explicit relocation evidence only."""
from pathlib import Path
from hashlib import sha256
import json
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent
src=H/'originals/current-p3-initrd/kmod/emmc.ko'
assert sha256(src.read_bytes()).hexdigest()=='14d17ea8065e3bc751a699dc644f00d247225640175d2957fb2a44bea39e5e4d'
with src.open('rb') as f:
    e=ELFFile(f); rels=[]
    for sec in e.iter_sections():
        if sec['sh_type']=='SHT_RELA':
            sy=e.get_section(sec['sh_link']);target=e.get_section(sec['sh_info']).name
            for r in sec.iter_relocations():
                s=sy.get_symbol(r['r_info_sym']);ix=s['st_shndx']
                rels.append(dict(section=target,offset=r['r_offset'],type=r['r_info_type'],symbol=s.name,
                    symbol_section=e.get_section(ix).name if isinstance(ix,int) else str(ix),
                    symbol_value=s['st_value'],addend=r['r_addend']))
    (H/'driver-relocations-detailed.json').open('x').write(json.dumps(rels,indent=2)+'\n')
    cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM); lookup={(r['section'],r['offset']):r for r in rels}
    for name,lo,hi in [('.init.text',0,0x1f20),('.text',0x7e80,0x8040)]:
        sec=e.get_section_by_name(name);raw=sec.data()[lo:hi];lines=[]
        for i in range(0,len(raw),4):
            a=lo+i;data=raw[i:i+4];ins=list(cs.disasm(data,a,count=1))
            line=f'{a:08x}: {data.hex()} '+(ins[0].mnemonic+' '+ins[0].op_str if ins else '.word')
            if (name,a) in lookup:line+=' ; '+str(lookup[(name,a)])
            lines.append(line)
        dest=H/(name.strip('.')+'-'+hex(lo)+'-locator.txt')
        dest.open('x').write('\n'.join(lines)+'\n')
    relevant=[r for r in rels if r['symbol'] in ['emmc_seq_read','emmc_seq_write','emmc_seq_get_boot_capacity',
        'emmc_seq_switch_partition','va_emmc_do_decrypt','va_emmc_do_encrypt']]
    print(json.dumps(relevant))
