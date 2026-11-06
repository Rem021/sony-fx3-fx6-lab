#!/usr/bin/env python3
"""Locate exact MOV-wide construction of the UFP transport peer service ID."""
from pathlib import Path
import hashlib,io,json,struct,sys
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
from find_ap_service_constructors import HERE,FS,regnumber

def main():
    manifest=json.loads((HERE.parent/'ap-input-20261029/current-consumer-results.json').read_text())
    source=FS/'nflasha15.img'
    with source.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==manifest['partition_sha256']
    sys.path.insert(0,str(FS));from read_filesystems import Ext2
    fs=Ext2(source);md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True;rows=[];files=0
    for entry in fs.walk():
        if entry['type']!=0x8000:continue
        raw=fs.data(entry['inode'])
        if raw[:4]!=b'\x7fELF':continue
        elf=ELFFile(io.BytesIO(raw))
        if elf['e_machine']!='EM_AARCH64':continue
        files+=1
        dyn=elf.get_section_by_name('.dynsym');symbols=list(dyn.iter_symbols()) if dyn else []
        for sec in elf.iter_sections():
            if not sec['sh_flags']&4 or sec['sh_type']=='SHT_NOBITS':continue
            data=sec.data();base=sec['sh_addr']
            for at,(high,) in enumerate(struct.iter_unpack('<I',data[:len(data)//4*4])):
                offset=at*4;opcode=high&0xffe00000
                if opcode not in [0x52a00000,0xd2a00000,0x72a00000,0xf2a00000] or (high>>5)&0xffff!=0xe1:continue
                rd=high&31;last=opcode in [0x72a00000,0xf2a00000]
                candidates=range(max(0,offset-32),offset,4) if last else range(offset+4,min(len(data)-3,offset+36),4)
                for other in candidates:
                    low=struct.unpack_from('<I',data,other)[0];accepted=[0x52800000,0xd2800000] if last else [0x72800000,0xf2800000]
                    if low&0xffe00000 not in accepted or low&31!=rd or (low>>5)&0xffff!=0x8246:continue
                    start,end=sorted([offset,other]);middle=list(md.disasm(data[start+4:end],base+start+4))
                    if any(i.mnemonic in ['bl','blr'] or any(regnumber(i.reg_name(r))==rd for r in i.regs_access()[1]) for i in middle):continue
                    address=base+start
                    enclosing=[s.name for s in symbols if s['st_info']['type']=='STT_FUNC' and s['st_size'] and s['st_value']<=address<s['st_value']+s['st_size']]
                    context=[f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(data[max(0,start-16):min(len(data),end+64)],base+max(0,start-16))]
                    rows.append(dict(path=entry['path'],inode=entry['inode'],source_sha256=hashlib.sha256(raw).hexdigest(),va=hex(address),register=rd,enclosing_symbols=enclosing,listing=context))
    (HERE/'transport-service-constructor-results.json').write_text(json.dumps(dict(target='0x00e18246',partition_sha256=manifest['partition_sha256'],arm64_elf_files=files,matches=rows,scope='Exact MOV-wide constructions only. The service ID is a candidate peer, not a proof of external USB admission or runtime availability. Other constant materialization and processors are outside this search. No device action.'),indent=2)+'\n')
    print(json.dumps(dict(arm64_elf=files,matches=len(rows),paths=sorted({r['path'] for r in rows}))))

if __name__=='__main__':main()
