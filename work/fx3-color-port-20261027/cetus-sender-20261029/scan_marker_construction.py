#!/usr/bin/env python3
"""Find bounded A64 MOVZ/MOVN + MOVK constructions, not arbitrary marker text."""
import hashlib,io,json,re,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
FSROOT=TASK.parent/'sony-firmware-20261024/stage2/extraction'
sys.path.insert(0,str(FSROOT));from read_filesystems import Ext2,FAT16
MARKERS={0x454e524b:'CP_APP_B',0x50435345:'CP_ESCAPE'}
CS=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);CS.detail=True
def sha(b):return hashlib.sha256(b).hexdigest()
def register_number(name):
    return int(name[1:]) if len(name)>1 and name[0] in 'xw' and name[1:].isdigit() else None
def candidates(data,file_offset,VA):
    hits=[];seen=set()
    for target,label in MARKERS.items():
        for half in [0,1]:
            imm=(target>>(half*16))&0xffff
            word=0x72800000|(half<<21)|(imm<<5)
            fixed=struct.pack('<I',word);low=fixed[0]
            pattern=re.compile(b'['+re.escape(bytes([low]))+b'-'+re.escape(bytes([low+31]))+b']'+re.escape(fixed[1:3])+b'[\x72\xf2]')
            for m in pattern.finditer(data):
                at=m.start()
                if at%4:continue
                last=struct.unpack_from('<I',data,at)[0];rd=last&31
                for n in range(1,9):
                    start=at-n*4
                    if start<0:break
                    first=struct.unpack_from('<I',data,start)[0];kind=first&0x7f800000
                    if kind not in [0x52800000,0x12800000] or first&31!=rd:continue
                    width=64 if first>>31 else 32;shift=((first>>21)&3)*16
                    value=((first>>5)&0xffff)<<shift
                    if kind==0x12800000:value=~value
                    value&=(1<<width)-1
                    mask=0xffff<<(half*16);value=(value&~mask)|(imm<<(half*16))
                    if value&0xffffffff!=target:continue
                    decoded=list(CS.disasm(data[start:at+4],VA+start))
                    if len(decoded)!=n+1 or any(x.size!=4 for x in decoded):continue
                    valid=True
                    for x in decoded[1:-1]:
                        if x.mnemonic in ['b','bl','br','blr','ret','cbz','cbnz','tbz','tbnz'] or x.mnemonic.startswith('b.'):
                            valid=False;break
                        try:written=x.regs_access()[1]
                        except Exception:valid=False;break
                        if rd in [register_number(x.reg_name(r)) for r in written]:valid=False;break
                    if not valid or (at,target) in seen:continue
                    seen.add((at,target))
                    context_start=max(0,start-16);context_end=min(len(data),at+24)
                    hits.append(dict(marker=label,value=hex(target),first_file_offset=hex(file_offset+start),
                        final_file_offset=hex(file_offset+at),final_VA=hex(VA+at),register=rd,
                        construction=[dict(VA=hex(x.address),bytes=x.bytes.hex(),instruction=x.mnemonic+' '+x.op_str) for x in decoded],
                        bounded_context=[dict(VA=hex(x.address),instruction=x.mnemonic+' '+x.op_str) for x in CS.disasm(data[context_start:context_end],VA+context_start)]))
    return hits
def main():
    out=HERE/'marker-construction-scan.json';assert not out.exists()
    scan=json.loads((HERE/'handoff-marker-scan.json').read_text());images=[]
    for part in [15,7]:
        inputrow=next(x for x in scan['images'] if x['image'].endswith(f'nflasha{part}.img'))
        image=Path(inputrow['image']);assert sha(image.read_bytes())==inputrow['image_sha256']
        fs=Ext2(image);files={x['path']:x for x in inputrow['files']};rows=[]
        for e in fs.walk():
            if e['type']!=0x8000:continue
            b=fs.data(e['inode'])
            if b[:4]!=b'\x7fELF':continue
            assert sha(b)==files[e['path']]['sha256']
            elf=ELFFile(io.BytesIO(b))
            if elf.header['e_machine']!='EM_AARCH64':continue
            sections=[];hits=[]
            for sec in elf.iter_sections():
                if int(sec['sh_flags'])&4 and sec['sh_type']=='SHT_PROGBITS':
                    data=sec.data();sections.append(dict(name=sec.name,bytes=len(data),file_offset=hex(sec['sh_offset']),VA=hex(sec['sh_addr'])))
                    hits.extend(dict(section=sec.name,**x) for x in candidates(data,sec['sh_offset'],sec['sh_addr']))
            rows.append(dict(path=e['path'],sha256=sha(b),executable_sections=sections,hits=hits))
        images.append(dict(image=str(image),image_sha256=inputrow['image_sha256'],A64_ELF_files=len(rows),
            executable_bytes=sum(s['bytes'] for r in rows for s in r['executable_sections']),files=rows))
    image=FSROOT/'nflasha3.img';assert sha(image.read_bytes())=='ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568'
    fs=FAT16(image);entry=next(x for x in fs.walk() if x['path']=='/vmlinux.bin');kernel=fs.data(entry['cluster'],entry['size'])
    assert sha(kernel)=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
    kbase=0xffffff8008080000
    kernel_hits=candidates(kernel,0,kbase)
    nor=TASK/'config-producer-20261029/original-files/loader_nor.bin';b=nor.read_bytes()
    assert sha(b)=='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
    controls=candidates(b,0,0xfe049000)
    assert {x['final_VA'] for x in controls}>={'0xfe052e8c','0xfe052e08'}
    result=dict(markers={hex(k):v for k,v in MARKERS.items()},images=images,
        original_kernel=dict(image=str(image),file='/vmlinux.bin',bytes=len(kernel),sha256=sha(kernel),
            provisional_VA_base=hex(kbase),base_scope='Read-only navigation from prior original symbol recovery; raw kernel hits require manual code/data verification.',hits=kernel_hits),
        original_NOR_positive_controls=controls,
        scope='Only bounded A64 MOVZ/MOVN plus MOVK constructions within8 instructions, excluding intervening branch/call or destination writes. ELF searches are executable sections; raw kernel data can yield candidates. Missing matches are not absence of a sender using a different ISA/constant construction, a different stage, DMA or external boot source. No native/device execution.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(images=[dict(image=x['image'],ELFs=x['A64_ELF_files'],executable_bytes=x['executable_bytes'],
        hits=[dict(path=r['path'],hits=r['hits']) for r in x['files'] if r['hits']]) for x in images],kernel_hits=kernel_hits,NOR_controls=controls)))
if __name__=='__main__':main()
