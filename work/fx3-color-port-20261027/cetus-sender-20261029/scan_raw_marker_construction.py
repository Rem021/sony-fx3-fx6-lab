#!/usr/bin/env python3
"""Extend marker construction search to raw AV/CP images; preserve ISA controls."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM,CS_MODE_THUMB
from scan_marker_construction import candidates,MARKERS,FSROOT,sha
HERE=Path(__file__).resolve().parent
def pair_rows(data,base,target,thumb):
    cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB if thumb else CS_MODE_ARM);cs.detail=True;hits=[]
    for rd in range(15):
        high=target>>16;low=target&0xffff
        if thumb:
            def encoding(imm,top):
                h1=(0xf2c0 if top else 0xf240)|((imm>>12)&15)|(((imm>>11)&1)<<10)
                h2=(((imm>>8)&7)<<12)|(rd<<8)|(imm&255)
                return struct.pack('<2H',h1,h2)
            endings=[encoding(high,True)];beginning=encoding(low,False);step=2
        else:
            def encoding(imm,top,cond=14):return struct.pack('<I',(cond<<28)|(0x03400000 if top else 0x03000000)|((imm&0xf000)<<4)|(rd<<12)|(imm&0xfff))
            endings=[encoding(high,True,cond) for cond in range(15)];beginning=None;step=4
        seen=set()
        for ending in endings:
            at=0
            while (at:=data.find(ending,at))>=0:
                final=at;at+=1
                if final%step:continue
                for n in range(1,17 if thumb else 9):
                    start=final-n*step
                    if start<0:break
                    if thumb and data[start:start+4]!=beginning:continue
                    if not thumb and data[start:start+4] not in [encoding(low,False,c) for c in range(15)]:continue
                    decoded=list(cs.disasm(data[start:final+4],base+start))
                    if not decoded or sum(x.size for x in decoded)!=final+4-start:continue
                    if decoded[0].mnemonic!='movw' or decoded[-1].mnemonic!='movt':continue
                    # Register names may be aliases (sb/sl/fp/ip); compare ids.
                    register=decoded[0].operands[0].reg
                    if decoded[-1].operands[0].reg!=register:continue
                    valid=True
                    for x in decoded[1:-1]:
                        if x.mnemonic.startswith('b') or x.mnemonic in ['cbz','cbnz','pop']:
                            valid=False;break
                        if register in x.regs_access()[1]:valid=False;break
                    if valid and (start,final) not in seen:
                        seen.add((start,final));hits.append(dict(value=hex(target),ISA='Thumb2' if thumb else 'ARM',first_file_offset=hex(start),
                            final_file_offset=hex(final),construction=[dict(VA=hex(x.address),instruction=x.mnemonic+' '+x.op_str,bytes=x.bytes.hex()) for x in decoded]))
    return hits
def main():
    out=HERE/'raw-marker-construction-scan.json';assert not out.exists()
    avpath=FSROOT/'files/nflasha3/av-cam.bin';av=avpath.read_bytes()
    cppath=FSROOT/'files/nflasha8/cpapp-b.bin';cp=cppath.read_bytes()
    assert sha(av)=='0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf'
    assert sha(cp)=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
    avbase=0xffffffc001000000;assert av[8:12]==b'ORIL' and struct.unpack_from('<Q',av)[0]==avbase+0x58
    cp_hits=[]
    for target in MARKERS:
        for thumb in [True,False]:cp_hits.extend(pair_rows(cp,0x108000,target,thumb))
    thumb_controls=pair_rows(cp,0x108000,0x2000b015,True)
    arm_controls=pair_rows(cp,0x108000,0x128000,False)
    assert any(0x7bc08<=int(x['first_file_offset'],16)<0x7bc20 for x in thumb_controls)
    assert any(0x553d48<=int(x['construction'][0]['VA'],16)<0x553d70 for x in arm_controls)
    result=dict(AV=dict(source=str(avpath),sha256=sha(av),bytes=len(av),candidate_base=hex(avbase),A64_hits=candidates(av,0,avbase),
        scope='Raw ORIL image and existing static address model, not observed loader/MMU executable sections.'),
        CP=dict(source=str(cppath),sha256=sha(cp),bytes=len(cp),ARM_Thumb_marker_hits=cp_hits),
        positive_controls=dict(Thumb2=thumb_controls,ARM=arm_controls),
        scope='Bounded MOVW/MOVT and MOVZ/MOVN/MOVK patterns only. Raw data may produce candidates; manual reachability review required. No match does not exclude another construction, image, mode, stage or processor. No original native/device execution.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(AV_hits=result['AV']['A64_hits'],CP_hits=cp_hits,Thumb_controls=len(thumb_controls),ARM_controls=len(arm_controls))))
if __name__=='__main__':main()
