#!/usr/bin/env python3
"""Source vector construction and exact code-constant references, read-only."""
import hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'route-20261028'))
from cp_look_route import image,BASE,PIN

def immediate(a,z):return ((a&15)<<12)|((a&0x400)<<1)|((z&0x7000)>>4)|(z&255)

def refs(raw,targets):
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);md.detail=True;rows=[]
    lows={v&0xffff for v in targets}
    for at in range(0,0x9c0000,2):
        a,z=struct.unpack_from('<HH',raw,at)
        if a&0xfbf0!=0xf240 or z&0x8000 or immediate(a,z) not in lows:continue
        reg=(z>>8)&15
        for end in range(at+4,at+52,2):
            c,d=struct.unpack_from('<HH',raw,end)
            if c&0xfbf0!=0xf2c0 or d&0x8000 or (d>>8)&15!=reg:continue
            value=immediate(a,z)|(immediate(c,d)<<16)
            if value not in targets:continue
            instructions=list(md.disasm(raw[at:end+4],BASE+at))
            if sum(i.size for i in instructions)!=end+4-at or instructions[0].mnemonic!='movw' or instructions[-1].mnemonic!='movt':continue
            dest=instructions[0].operands[0].reg
            if any(i.mnemonic in ['bl','blx'] or dest in i.regs_access()[1] for i in instructions[1:-1]):continue
            lo=max(0,at-16);hi=end+68
            rows.append(dict(value=hex(value),label=targets[value],file_offset=hex(at),va=hex(BASE+at),register=reg,
                             span_file=hex(lo),span_bytes=hi-lo,span_sha256=hashlib.sha256(raw[lo:hi]).hexdigest(),
                             listing=[f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(raw[lo:hi],BASE+lo)]))
            break
    return rows

def main():
    raw=image();targets={0x118b6c0:'default parameter vector',0x118b788:'alternate parameter vector',
                          BASE+0xce623b:'setImagerDriveInfo diagnostic',BASE+0xce628f:'setCamDriveInfo diagnostic',BASE+0xce62ec:'setCamLvDriveInfo diagnostic'}
    matches=refs(raw,targets)
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);dest=HERE/'source-fragments';dest.mkdir(exist_ok=True);fragments=[]
    for lo,hi,label in [(0x8cdea8,0x8cdecc,'vector-getters'),(0x8cf210,0x8cf320,'vector-constructor'),
                        (0x3004ca,0x3005bc,'sync-context-input'),(0x8ce788,0x8ce7a0,'default-vector-caller'),
                        (0x8c9038,0x8c9442,'drive-info-constructor'),(0x8c9442,0x8c946a,'drive-info-default-wrapper'),
                        (0x8ce7a0,0x8ce7d0,'drive-info-two-copies'),(0x2ffa7c,0x2ffabc,'original-constructor-caller')]:
        body=raw[lo:hi];p=dest/f'{label}.txt';p.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(body,BASE+lo))+'\n')
        fragments.append(dict(label=label,file_offset=hex(lo),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),listing=str(p.relative_to(HERE))))
    calls=[];wanted={0x9d1038,0x9d7210,0x9d1442}
    for at in range(0,0x9c0000,2):
        a,z=struct.unpack_from('<HH',raw,at)
        if a&0xf800!=0xf000 or z&0xd000 not in [0xd000,0x9000]:continue
        s=(a>>10)&1;j1=(z>>13)&1;j2=(z>>11)&1
        immediate=(s<<24)|((1^(j1^s))<<23)|((1^(j2^s))<<22)|((a&0x3ff)<<12)|((z&0x7ff)<<1)
        if s:immediate-=1<<25
        target=BASE+at+4+immediate
        if target not in wanted:continue
        ins=next(md.disasm(raw[at:at+4],BASE+at,count=1),None)
        if ins is None or ins.mnemonic not in ['bl','b.w'] or int(ins.op_str[1:],0)!=target:continue
        lo=max(0,at-96);hi=at+32
        calls.append(dict(file_offset=hex(at),va=hex(BASE+at),target=hex(target),opcode=ins.mnemonic,span_file=hex(lo),span_bytes=hi-lo,span_sha256=hashlib.sha256(raw[lo:hi]).hexdigest(),listing=[f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(raw[lo:hi],BASE+lo)]))
    diagnostics=[]
    for va in [0xdf2538,0xdf2544]:
        at=va-BASE;value=raw[at:raw.index(0,at)]
        diagnostics.append(dict(va=hex(va),file_offset=hex(at),value=value.decode(),sha256=hashlib.sha256(value+b'\0').hexdigest()))
    result=dict(cp_sha256=PIN,constant_references=matches,source_fragments=fragments,direct_call_candidates=calls,diagnostic_source_names=diagnostics,
                scope='Exact MOVW/MOVT constants with destination-clobber and continuous-decoding guards, plus bounded original vector source. Halfword/code-data ambiguity and indirect/other constant construction remain; a reference is not proof of a call, structure identity, normal scene, MAIN pixels, IPC or firmware acceptance.')
    (HERE/'vector-source-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(vector_refs=sum(r['value'] in ['0x118b6c0','0x118b788'] for r in matches),diagnostic_refs=[dict(file=r['file_offset'],label=r['label']) for r in matches if 'diagnostic' in r['label']],fragments=len(fragments),direct_calls=[dict(file=r['file_offset'],target=r['target']) for r in calls])))

if __name__=='__main__':main()
