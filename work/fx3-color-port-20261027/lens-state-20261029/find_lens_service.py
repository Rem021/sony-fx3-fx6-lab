#!/usr/bin/env python3
"""Read-only exact AP service constructions plus CP/AV literal candidates."""
from pathlib import Path
import hashlib,io,json,struct,sys
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
PROJECT=TASK.parents[1]
FS=PROJECT/'work/sony-firmware-20261024/stage2/extraction'
sys.path.insert(0,str(TASK/'entry-20261029'))
from find_ap_service_constructors import regnumber
TARGETS={0x912503d0,0x80920871,0x809244ab}

def main():
    image=FS/'nflasha15.img';ap_pin='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    with image.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==ap_pin
    sys.path.insert(0,str(FS));from read_filesystems import Ext2
    fs=Ext2(image);md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True
    matches=[];elf_count=0;literal_rows=[]
    for entry in fs.walk():
        if entry['type']!=0x8000:continue
        raw=fs.data(entry['inode'])
        if raw[:4]!=b'\x7fELF':continue
        elf=ELFFile(io.BytesIO(raw))
        if elf['e_machine']!='EM_AARCH64':continue
        elf_count+=1;dyn=elf.get_section_by_name('.dynsym');symbols=list(dyn.iter_symbols()) if dyn else []
        for target in TARGETS:
            token=struct.pack('<I',target);at=0;positions=[]
            while True:
                at=raw.find(token,at)
                if at<0:break
                if at%4==0:positions.append(hex(at))
                at+=1
            if positions:literal_rows.append(dict(path=entry['path'],target=hex(target),file_offsets=positions,source_sha256=hashlib.sha256(raw).hexdigest()))
        for section in elf.iter_sections():
            if not section['sh_flags']&4 or section['sh_type']=='SHT_NOBITS':continue
            data=section.data();base=section['sh_addr']
            for index,(word,) in enumerate(struct.iter_unpack('<I',data[:len(data)//4*4])):
                opcode=word&0xffe00000;upper=(word>>5)&0xffff
                if opcode not in [0x52a00000,0xd2a00000,0x72a00000,0xf2a00000] or upper not in [0x9125,0x8092]:continue
                at=index*4;rd=word&31;high_last=opcode in [0x72a00000,0xf2a00000]
                candidates=range(max(0,at-32),at,4) if high_last else range(at+4,min(len(data)-3,at+36),4)
                accepted=[0x52800000,0xd2800000] if high_last else [0x72800000,0xf2800000]
                for other in candidates:
                    low=struct.unpack_from('<I',data,other)[0]
                    if low&0xffe00000 not in accepted or low&31!=rd:continue
                    target=(upper<<16)|((low>>5)&0xffff)
                    if target not in TARGETS:continue
                    start,end=sorted([at,other]);middle=list(md.disasm(data[start+4:end],base+start+4))
                    if any(ins.mnemonic in ['bl','blr'] or any(regnumber(ins.reg_name(r))==rd for r in ins.regs_access()[1]) for ins in middle):continue
                    va=base+start;enclosing=[s.name for s in symbols if s['st_info']['type']=='STT_FUNC' and s['st_size'] and s['st_value']<=va<s['st_value']+s['st_size']]
                    context=[f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(data[max(0,start-16):min(len(data),end+64)],base+max(0,start-16))]
                    relocatable=elf['e_type']=='ET_REL'
                    matches.append(dict(path=entry['path'],inode=entry['inode'],source_sha256=hashlib.sha256(raw).hexdigest(),target=hex(target),section=section.name,address_kind='section-relative' if relocatable else 'ELF virtual',address=hex(va),va=None if relocatable else hex(va),file_offset=hex(section['sh_offset']+start),register=rd,enclosing_symbols=enclosing,listing=context))
    firmware=[]
    for relative,pin in [('files/nflasha8/cpapp-b.bin','c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'),('files/nflasha3/av-cam.bin','0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf')]:
        p=FS/relative;raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
        for target in TARGETS:
            token=struct.pack('<I',target);positions=[];at=0
            while True:
                at=raw.find(token,at)
                if at<0:break
                positions.append(hex(at));at+=1
            firmware.append(dict(path=str(p),source_sha256=pin,bytes=len(raw),target=hex(target),literal_file_offsets=positions,scope='Exact bytes only, not code or service registration proof.'))
    result=dict(ap_partition_sha256=ap_pin,arm64_elf_files=elf_count,targets=[hex(v) for v in sorted(TARGETS)],ap_mov_wide_matches=matches,ap_aligned_literal_candidates=literal_rows,cp_av_literal_candidates=firmware,
                scope='Read-only 532-ELF AP scan of exact MOV-wide constructions without intervening clobber/calls, plus raw aligned AP and exact CP/AV literal byte searches. Does not cover all constant materialization, dynamic service resolution or all processors; candidates are not live receivers, authentication, model agreement or real replies. No device action.')
    (HERE/'service-location-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(arm64_elf=elf_count,mov_matches=len(matches),mov_paths=sorted({r['path'] for r in matches}),cp_av_literal_counts=[dict(path=Path(r['path']).name,target=r['target'],matches=len(r['literal_file_offsets'])) for r in firmware])))

if __name__=='__main__':main()
