#!/usr/bin/env python3
"""Pinned caller candidates and reviewed resource/MLUT implementation slices."""
from hashlib import sha256
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_ARM
import json,struct
from vfx_resource_guest import HERE,image,BASE,PIN,SPANS
from cp_look_route import branch_target


def main():
    b=image();cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    targets={BASE+0x3259bc:'AcquireVfx',0xa14d86:'core_set_look',0xa1f2f2:'core_queue',0xa4f8ba:'SDK_set_builtin'}
    refs={hex(t):[] for t in targets};slots=[]
    for o in range(0,0x9c0000,2):
        a,z=struct.unpack_from('<HH',b,o)
        target=branch_target(a,z,BASE+o)
        if o<0x9b0000 and target in targets:refs[hex(target)].append(hex(o))
        if a&0xfbf0==0xf240 and not z&0x8000:
            v=((a&15)<<12)|((a&0x400)<<1)|((z&0x7000)>>4)|(z&255)
            if v==0x10d0:slots.append(hex(o))
    (HERE/'resource-call-candidates.json').write_text(json.dumps(refs,indent=2)+'\n')
    (HERE/'resource-offset-candidates.json').write_text(json.dumps(slots,indent=2)+'\n')
    spans=SPANS+[(0x3259bc,0x325a8c),(0x2fc330,0x2fc344),(0x8cb474,0x8cb484),
                 (0x8cc688,0x8cc6c6),(0x8cf4f6,0x8cf536),(0x8cf63e,0x8cf658),
                 (0x94671e,0x9467b4),(0x368ec0,0x369114),(0x916d26,0x916dec),
                 (0x90e1b6,0x90e1c2),(0x9113ea,0x911434),(0x90c11e,0x90c134),
                 (0x911448,0x911462),(0x9115fc,0x911650)]
    out=HERE/'disassembly';out.mkdir(exist_ok=True);sources=[]
    for a,z in sorted(set(spans)):
        mode=CS_MODE_ARM if a==0x450af4 else CS_MODE_THUMB
        cs=Cs(CS_ARCH_ARM,mode);name=f'cp-{a:08x}-{z:08x}.txt'
        (out/name).write_text('\n'.join(f'{i.address-BASE:08x}: {i.mnemonic} {i.op_str}' for i in cs.disasm(b[a:z],BASE+a))+'\n')
        sources.append(dict(file_start=hex(a),end_exclusive=hex(z),sha256=sha256(b[a:z]).hexdigest(),disassembly='disassembly/'+name))
    result=dict(status='PASS_PINNED_RESOURCE_AND_DMA_SOURCE_INVENTORY',cp_sha256=PIN,
                call_candidates=refs,resource_slot_candidates=len(slots),source_spans=sources,
                lookup_tables={'VFX_group_to_MLUT_type':{'VA':'0xd09228','pairs':list(struct.iter_unpack('<II',b[0xd09228-BASE:0xd09228-BASE+56]))},
                               'MLUT_register_table':{'VA':'0xd00ddc','entries':[hex(x) for x in struct.unpack_from('<7I',b,0xd00ddc-BASE)]}},
                reviewed_exclusion={'file':'0x94678e','reason':'Same +0x10d0 offset belongs to another base derived from VA 0xd091f0 and packs 14-bit input pairs. It is not established as the VFX software object acquire-ID setter.'},
                unresolved='The VFX software object +0x10d0 owner producer and its runtime MAIN/monitor allocation are not established by these source slices.',
                scope='Halfword and MOVW scans produce candidates; same offsets or constants do not establish object identity or a live owner.')
    (HERE/'static-inventory-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'source slices',len(sources),'slot candidates',len(slots))


if __name__=='__main__':main()
