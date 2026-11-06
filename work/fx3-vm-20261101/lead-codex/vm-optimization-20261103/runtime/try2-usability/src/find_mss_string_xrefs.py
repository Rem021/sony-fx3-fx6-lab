#!/usr/bin/env python3
"""Read-only AArch64 ADRP+ADD cross references in the original appFw.so."""
import hashlib
import json
import struct
from pathlib import Path

ORIG=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so')
OUT=Path(__file__).resolve().parents[1]/'original-appfw-mss-string-xrefs.json'
NEEDLES=[b'sequence_mss_reload',b'Send UPM::mss_start()',b'Send UPM::mss_stop()',b'Send MSS_fakey_start(display)']

def sx(x,bits):
    return x-(1<<bits) if x&(1<<(bits-1)) else x

def main():
    data=ORIG.read_bytes()
    # The original ELF first PT_LOAD maps file offset to VMA without a delta.
    text_start=0x1594680
    text_end=0x2f88bc8
    assert data[text_start:text_start+4]==bytes.fromhex('ff4301d1') or len(data)>text_end
    results=[]
    for needle in NEEDLES:
        starts=[];at=0
        while True:
            at=data.find(needle,at)
            if at<0:break
            starts.append(at);at+=1
        for target in starts:
            refs=[]
            page=target&~0xfff
            for pc in range(text_start,text_end,4):
                w=struct.unpack_from('<I',data,pc)[0]
                if w&0x9f000000!=0x90000000:continue
                imm=sx((((w>>5)&0x7ffff)<<2)|((w>>29)&3),21)
                if ((pc&~0xfff)+(imm<<12))!=page:continue
                rd=w&31
                for later in range(pc+4,min(pc+0x60,text_end),4):
                    a=struct.unpack_from('<I',data,later)[0]
                    if a&0xff000000!=0x91000000:continue
                    rn=(a>>5)&31
                    if rn!=rd:continue
                    imm12=(a>>10)&0xfff
                    shift=(a>>22)&1
                    if page+(imm12<<(12 if shift else 0))==target:
                        refs.append({'adrp_vma':hex(pc),'add_vma':hex(later),'register':rd,'adrp_word':hex(w),'add_word':hex(a)})
            results.append({'string':needle.decode(),'vma':hex(target),'file_offset':target,'references':refs})
    OUT.write_text(json.dumps({'source':str(ORIG),'sha256':hashlib.sha256(data).hexdigest(),'method':'original ELF first PT_LOAD offset==VMA, AArch64 ADRP+ADD exact target','strings':results},indent=2)+'\n')
    print(OUT)
    for r in results:print(r['string'],r['vma'],r['references'][:8])

if __name__=='__main__':main()
