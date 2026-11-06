#!/usr/bin/env python3
"""Find exact MOV-wide construction of four known AP service IDs, read-only."""
from pathlib import Path
import hashlib,io,json,struct,sys
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
FS=PROJECT/'work/sony-firmware-20261024/stage2/extraction'
TARGETS={0x004b8290,0x004b0233,0x004b024e,0x804b0998}

def regnumber(name):
    if name.startswith(('w','x')) and name[1:].isdigit():return int(name[1:])
    return None

def main():
    HERE.mkdir(exist_ok=True)
    pin=json.loads((HERE.parent/'ap-input-20261029/current-consumer-results.json').read_text())['partition_sha256']
    source=FS/'nflasha15.img'
    with source.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==pin
    sys.path.insert(0,str(FS));from read_filesystems import Ext2
    fs=Ext2(source);md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True
    rows=[];elfcount=0;sectionbytes=0
    for entry in fs.walk():
        if entry['type']!=0x8000:continue
        raw=fs.data(entry['inode'])
        if raw[:4]!=b'\x7fELF':continue
        elf=ELFFile(io.BytesIO(raw))
        if elf['e_machine']!='EM_AARCH64':continue
        elfcount+=1;dyn=elf.get_section_by_name('.dynsym');plt=elf.get_section_by_name('.plt');rel=elf.get_section_by_name('.rela.plt')
        labels={plt['sh_addr']+32+16*i:dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())} if dyn and plt and rel else {}
        for sec in elf.iter_sections():
            if not sec['sh_flags']&4 or sec['sh_type']=='SHT_NOBITS':continue
            data=sec.data();base=sec['sh_addr'];sectionbytes+=len(data)
            for at in range(0,len(data)-3,4):
                high=struct.unpack_from('<I',data,at)[0];opcode=high&0xffe00000
                if opcode not in [0x52a00000,0xd2a00000,0x72a00000,0xf2a00000]:continue
                upper=(high>>5)&0xffff
                if upper not in [0x004b,0x804b]:continue
                rd=high&31;high_is_last=opcode in [0x72a00000,0xf2a00000]
                candidates=range(max(0,at-32),at,4) if high_is_last else range(at+4,min(len(data)-3,at+36),4)
                for other in candidates:
                    low=struct.unpack_from('<I',data,other)[0]
                    accepted=[0x52800000,0xd2800000] if high_is_last else [0x72800000,0xf2800000]
                    if low&0xffe00000 not in accepted or low&31!=rd:continue
                    value=(upper<<16)|((low>>5)&0xffff)
                    if value not in TARGETS:continue
                    start,end=sorted([at,other]);middle=list(md.disasm(data[start+4:end],base+start+4))
                    if any(i.mnemonic in ['bl','blr'] or any(regnumber(i.reg_name(r))==rd for r in i.regs_access()[1]) for i in middle):continue
                    follow=[]
                    for ins in md.disasm(data[end+4:min(len(data),end+52)],base+end+4):
                        if ins.mnemonic in ['bl','b'] and ins.op_str.startswith('#'):
                            target=int(ins.op_str[1:],0);follow.append(dict(site=hex(ins.address),target=hex(target),symbol=labels.get(target)));break
                        if ins.mnemonic=='blr':follow.append(dict(site=hex(ins.address),target=ins.op_str,symbol=None));break
                        if any(regnumber(ins.reg_name(r))==rd for r in ins.regs_access()[1]):break
                    listing=[]
                    for ins in md.disasm(data[max(0,start-8):min(len(data),end+52)],base+max(0,start-8)):listing.append(f'{ins.address:08x} {ins.mnemonic:9} {ins.op_str}')
                    rows.append(dict(path=entry['path'],inode=entry['inode'],source_sha256=hashlib.sha256(raw).hexdigest(),section=sec.name,value=hex(value),register=rd,first_instruction=hex(base+start),last_instruction=hex(base+end),next_call_without_register_overwrite=follow,listing=listing))
    result=dict(source=str(source),source_sha256=pin,arm64_elf_files=elfcount,executable_section_bytes=sectionbytes,matches=rows,
                scope='Exact four MOV-wide ID constructions in executable sections, without intervening same-register writes or calls. The nearby call annotation is a candidate consumer, not complete request dataflow, authentication, whole-system coverage or live dispatch. Does not cover other construction styles or other processors. No binary execution/device access.')
    (HERE/'ap-service-constructor-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'arm64_elf':elfcount,'executable_bytes':sectionbytes,'matches':len(rows),'paths':sorted({r['path'] for r in rows})}))

if __name__=='__main__':main()
