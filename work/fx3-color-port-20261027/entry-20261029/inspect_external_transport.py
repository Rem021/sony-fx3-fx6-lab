#!/usr/bin/env python3
"""Pinned static userspace transport and relocatable kernel module slices."""
from pathlib import Path
import hashlib,io,json
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
from inspect_entry_chain import View,listing,HERE

def main():
    users=[]
    targets={'libInfraExtCmdSvc.so':[0x3eec,0x2c4c,0x2f6c,0x3298,0x292c],
             'libusbcmd.so':[0x3370,0x3308,0x4240,0x437c,0x448c,0x4700,0x41c0,0x42dc,0x36c8,0x37cc]}
    for source in json.loads((HERE/'external-command-sources.json').read_text()):
        view=View(HERE/source['output'],source['sha256'])
        for va in targets[view.path.name]:
            raw=view.function(va);text,literals,calls=listing(view,va,len(raw))
            out=HERE/'entry-fragments'/f'{view.path.name}-{va:x}.txt';out.write_text(text)
            users.append(dict(library=view.path.name,va=hex(va),label=view.labels[va],source_sha256=source['sha256'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),literals=literals,calls=calls,disassembly=str(out.relative_to(HERE))))
    (HERE/'external-command-static-results.json').write_text(json.dumps(dict(fragments=users,scope='Static source-file instructions only. UFP peer service 0x00e18246 is the external-command service; the USB wrapper creates opcode 0x7a with a supplied feature ID and opens /dev/usb/usb_extcmd. External USB mode, command sequencing, current kernel registration, authentication and camera admission are not proven.'),indent=2)+'\n')
    source=json.loads((HERE/'usb-extcmd-source.json').read_text());raw=(HERE/source['output']).read_bytes();assert hashlib.sha256(raw).hexdigest()==source['sha256']
    elf=ELFFile(io.BytesIO(raw));assert elf['e_type']=='ET_REL';sym=elf.get_section_by_name('.symtab');functions=[]
    for name in ['extcmd_ioctl','extcmd_user_access_ok','extcmd_open','list_get_node','extcmd_create_this']:
        symbol=next(s for s in sym.iter_symbols() if s.name==name);section=elf.get_section(symbol['st_shndx'])
        rels=next(s for s in elf.iter_sections() if s['sh_type']=='SHT_RELA' and s['sh_info']==symbol['st_shndx'])
        relmap={r['r_offset']:dict(type=r['r_info_type'],symbol=sym.get_symbol(r['r_info_sym']).name,addend=r['r_addend']) for r in rels.iter_relocations()}
        lo=symbol['st_value'];code=section.data()[lo:lo+symbol['st_size']];lines=[];selected=[]
        for instruction in Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN).disasm(code,lo):
            relocation=relmap.get(instruction.address);note=' ; relocation '+json.dumps(relocation) if relocation else ''
            lines.append(f'{instruction.address:08x} {instruction.mnemonic:10} {instruction.op_str}{note}')
            if relocation:selected.append(dict(offset=hex(instruction.address),**relocation))
        out=HERE/'entry-fragments'/f'usb_extcmd.ko-{name}.txt';out.write_text('\n'.join(lines)+'\n')
        functions.append(dict(function=name,section=section.name,offset=hex(lo),bytes=len(code),sha256=hashlib.sha256(code).hexdigest(),relocations=selected,disassembly=str(out.relative_to(HERE))))
    (HERE/'usb-extcmd-static-results.json').write_text(json.dumps(dict(source_sha256=source['sha256'],elf_type=elf['e_type'],functions=functions,scope='Static ET_REL instructions and relocation annotations only. Section offsets are not live kernel addresses. user_access_ok examines user memory bounds; its name does not imply device or firmware authentication. Native kernel/ioctl/USB calls are never executed.'),indent=2)+'\n')
    print(json.dumps(dict(userspace_fragments=len(users),kernel_fragments=len(functions),native_execution=0,camera_actions=0)))

if __name__=='__main__':main()
