#!/usr/bin/env python3
"""Exact Thumb/ARM MOVW+MOVT candidates in pinned CP/AV images, read-only."""
import hashlib,json,struct
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_ARM
from find_lens_service import HERE,FS,TARGETS

def imm_thumb(h1,h2):return ((h1&15)<<12)|(((h1>>10)&1)<<11)|(((h2>>12)&7)<<8)|(h2&255)
def regnum(name):return int(name[1:]) if name.startswith('r') and name[1:].isdigit() else {'ip':12,'sp':13,'lr':14,'pc':15}.get(name)

def main():
    rows=[];counts=[]
    specs=[('files/nflasha8/cpapp-b.bin','c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',0x108000),
           ('files/nflasha3/av-cam.bin','0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf',None)]
    for relative,pin,known_base in specs:
        path=FS/relative;raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
        for mode_name,mode,step in [('thumb',CS_MODE_THUMB,2),('arm',CS_MODE_ARM,4)]:
            md=Cs(CS_ARCH_ARM,mode);md.detail=True;high_count=0;before=len(rows)
            for at in range(0,len(raw)-3,step):
                if mode_name=='thumb':
                    h1,h2=struct.unpack_from('<HH',raw,at)
                    if h1&0xfbf0!=0xf2c0:continue
                    upper=imm_thumb(h1,h2);rd=(h2>>8)&15
                else:
                    word=struct.unpack_from('<I',raw,at)[0]
                    if word&0x0ff00000!=0x03400000:continue
                    upper=((word>>4)&0xf000)|(word&0xfff);rd=(word>>12)&15
                if upper not in [0x9125,0x8092]:continue
                ins=list(md.disasm(raw[at:at+4],at));
                if len(ins)!=1 or ins[0].mnemonic!='movt' or len(ins[0].operands)<2 or ins[0].operands[1].imm!=upper:continue
                high_count+=1
                for other in range(max(0,at-48),min(len(raw)-3,at+52),step):
                    if other==at:continue
                    if mode_name=='thumb':
                        a,b=struct.unpack_from('<HH',raw,other)
                        if a&0xfbf0!=0xf240 or (b>>8)&15!=rd:continue
                        lower=imm_thumb(a,b)
                    else:
                        word=struct.unpack_from('<I',raw,other)[0]
                        if word&0x0ff00000!=0x03000000 or (word>>12)&15!=rd:continue
                        lower=((word>>4)&0xf000)|(word&0xfff)
                    value=(upper<<16)|lower
                    if value not in TARGETS:continue
                    low_ins=list(md.disasm(raw[other:other+4],other))
                    if len(low_ins)!=1 or low_ins[0].mnemonic!='movw' or low_ins[0].operands[1].imm!=lower:continue
                    start,end=sorted([at,other]);middle=list(md.disasm(raw[start+4:end],start+4))
                    if any(i.mnemonic in ['bl','blx'] or any(regnum(i.reg_name(r))==rd for r in i.regs_access()[1]) for i in middle):continue
                    lo=max(0,start-16);hi=min(len(raw),end+64);span=raw[lo:hi]
                    rows.append(dict(path=str(path),source_sha256=pin,mode=mode_name,target=hex(value),register=rd,file_offset=hex(start),cp_va=hex(known_base+start) if known_base is not None else None,
                                     span_file_offset=hex(lo),span_bytes=len(span),span_sha256=hashlib.sha256(span).hexdigest(),listing=[f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(span,lo)]))
            counts.append(dict(path=str(path),source_sha256=pin,mode=mode_name,target_high_movt_candidates=high_count,matches=len(rows)-before))
    output=dict(scans=counts,matches=rows,scope='Bounded exact MOVW/MOVT pairs cross-checked with Capstone ARM/Thumb and no intervening destination writes/calls. CP addresses use the previously recovered base; AV is file-offset only. A matching constant is not a receiver or valid function boundary. No live code, service dispatch, replies, native target execution or device access.')
    (HERE/'peer-constant-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(matches=len(rows),scans=counts)))

if __name__=='__main__':main()
