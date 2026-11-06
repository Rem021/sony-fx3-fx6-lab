#!/usr/bin/env python3
"""Reproducible CP reference candidates with explicitly reviewed source slices."""
import json,struct
from hashlib import sha256
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
from ec_mode_guest import image,BASE,PIN,HERE


def main():
    b=image();cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    fields=[];pairs=[]
    def mov(o,kind):
        a,z=struct.unpack_from('<HH',b,o)
        if a&0xfbf0!=kind or z&0x8000:return None
        return (z>>8)&15,((a&15)<<12)|((a&0x400)<<1)|((z&0x7000)>>4)|(z&255)
    for o in range(0,min(len(b)-4,0xee0000),2):
        a,z=struct.unpack_from('<HH',b,o)
        if a&0xfff0 in (0xf8d0,0xf8c0) and z&0xfff in [0x794,0x798,0x79c,0x7a0,0x7a4,0x7b0]:
            ins=next(cs.disasm(b[o:o+4],BASE+o,count=1),None)
            if ins:fields.append(dict(file=hex(o),va=hex(BASE+o),instruction=ins.mnemonic+' '+ins.op_str,field=hex(z&0xfff)))
        if o>=0x9c0000:continue
        m=mov(o,0xf240)
        if not m:continue
        for t in range(o+4,o+44,2):
            n=mov(t,0xf2c0)
            if n and n[0]==m[0]:
                value=m[1]|n[1]<<16
                if value in [0x1a17bb0,0x1a168d8,0x1a17bb8,0x1a168e0]:
                    pairs.append(dict(start=hex(o),end=hex(t),reg=m[0],value=hex(value)))
                break
    (HERE/'field-reference-candidates.json').write_text(json.dumps(fields,indent=2)+'\n')
    (HERE/'capture-global-xref-candidates.json').write_text(json.dumps(pairs,indent=2)+'\n')
    spans=[(0x1c1fac,0x1c1fda),(0x1c36ae,0x1c36ec),(0x1cb8a8,0x1cb934),
           (0x1cd5d0,0x1cd5e4),(0x1cdbb2,0x1cdc5a),(0x1ce148,0x1ce1b4),
           (0x1cfbf4,0x1cfc5c),(0x66b256,0x66b2b4),(0x1d6ca4,0x1d6cc2),
           (0x1f605c,0x1f60f8),(0x689c38,0x689c42),(0x689f9c,0x68a002),
           (0x6593b8,0x6593e8),(0x665b50,0x665b6c),(0x65cc14,0x65cc22),
           (0x6721a0,0x6721f4),(0x1d560c,0x1d565a),(0x672004,0x672062)]
    out=HERE/'disassembly';out.mkdir(exist_ok=True);sources=[]
    for a,z in spans:
        name=f'cp-{a:08x}-{z:08x}.txt'
        (out/name).write_text('\n'.join(f'{i.address-BASE:08x}: {i.mnemonic} {i.op_str}'
                                       for i in cs.disasm(b[a:z],BASE+a))+'\n')
        sources.append(dict(file_start=hex(a),file_end_exclusive=hex(z),sha256=sha256(b[a:z]).hexdigest(),disassembly='disassembly/'+name))
    bindings=[dict(source_field='capture +0x794',consumer='MonitoringBaseCurveMeta',
                   load='0x1cdbca',call='0x1cdbde',output='+0x234',named_log='0x1ce158',classification='metadata'),
              dict(source_field='capture +0x794',consumer='MonitoringCharacteristicsMeta',
                   load='0x1cdc34',call='0x1cdc48',output='+0x23c',named_log='0x1ce1a4',classification='metadata'),
              dict(source_field='capture +0x794',consumer='EC_Ref conditional base 10 path',
                   load='0x1d6ca4',source_string='EC_Ref.cpp @ file0x1d6e10',classification='exposure reference')]
    result=dict(status='PASS_PINNED_STATIC_CANDIDATE_INVENTORY',cp_sha256=PIN,
                field_candidates=len(fields),global_candidates=len(pairs),reviewed_bindings=bindings,source_spans=sources,
                limitations=['Halfword scanning is candidate generation and does not establish instruction boundaries in all code/data.',
                             'MOVW/MOVT pairing can include intervening register clobbers; pairs require local review.',
                             'Matching an immediate structure offset alone does not establish object identity.',
                             'Selected metadata/EC reference consumers do not enumerate all image-processing consumers.'])
    (HERE/'static-inventory-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'field/global candidates',len(fields),len(pairs),'reviewed slices',len(spans))


if __name__=='__main__':main()
