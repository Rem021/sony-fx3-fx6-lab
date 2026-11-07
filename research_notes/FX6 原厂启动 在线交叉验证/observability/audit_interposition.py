#!/usr/bin/env python3
"""Audit cold ELF inputs and our observer; never contacts a guest or socket."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN


def inspect(path, expected):
    data=path.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if digest!=expected:
        raise ValueError(f'SHA mismatch: {path}')
    f=path.open('rb')
    return data,f,ELFFile(f),{'path':str(path),'bytes':len(data),'sha256':digest}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--donor',type=Path,default=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib'))
    ap.add_argument('--observer',type=Path,default=Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/parallel-research-20261107/online-observability/libfx6-queue-observer.so'))
    args=ap.parse_args()
    b,fa,app,app_fp=inspect(args.donor/'appFw.so','a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067')
    _,fl,lib,lib_fp=inspect(args.donor/'libosal_uipc.so','fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a')
    with fa,fl,args.observer.open('rb') as fo:
        sy=app.get_section_by_name('.dynsym')
        symbol=next(s for s in sy.iter_symbols() if s.name=='osal_rcv_msg_tmo')
        rp=app.get_section_by_name('.rela.plt');plt=app.get_section_by_name('.plt')
        slots=[(i,r) for i,r in enumerate(rp.iter_relocations()) if sy.get_symbol(r['r_info_sym']).name=='osal_rcv_msg_tmo']
        if len(slots)!=1 or slots[0][1]['r_info_type']!=1026:
            raise ValueError('expected one R_AARCH64_JUMP_SLOT')
        i,r=slots[0];target=plt['sh_addr']+32+i*16
        if target!=0xb19ec0 or symbol['st_shndx']!='SHN_UNDEF' or symbol['st_other']['visibility']!='STV_DEFAULT':
            raise ValueError('app import/PLT binding mismatch')
        text=app.get_section_by_name('.text');tb=text.data();start=text['sh_addr'];callers=[]
        for pos in range(0,len(tb)-3,4):
            w=struct.unpack_from('<I',tb,pos)[0]
            if w&0xfc000000!=0x94000000:
                continue
            imm=w&0x3ffffff
            if imm&0x2000000:
                imm-=0x4000000
            pc=start+pos
            if pc+imm*4==target:
                callers.append({'bl_vma':hex(pc),'expected_lr_vma':hex(pc+4)})
        expected={0x20efbbc,0x20f80f8,0x20ef7cc,0x20ef554,0xc0a20c}
        actual={int(c['expected_lr_vma'],16) for c in callers}
        if not expected.issubset(actual):
            raise ValueError('named observer classifier sites missing from pinned app')
        real=next(s for s in lib.get_section_by_name('.dynsym').iter_symbols() if s.name=='osal_rcv_msg_tmo')
        if real['st_shndx']=='SHN_UNDEF' or real['st_other']['visibility']!='STV_DEFAULT':
            raise ValueError('real receive is not exported/default visible')
        obs=ELFFile(fo);entry=next(s for s in obs.get_section_by_name('.dynsym').iter_symbols() if s.name=='osal_rcv_msg_tmo')
        a=entry['st_value'];segment=next(p for p in obs.iter_segments() if p['p_type']=='PT_LOAD' and p['p_vaddr']<=a<p['p_vaddr']+p['p_filesz'])
        fo.seek(segment['p_offset']+a-segment['p_vaddr']);code=fo.read(entry['st_size'])
        cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
        instructions=list(cs.disasm(code,a));first_bl=next(i.address for i in instructions if i.mnemonic=='bl')
        saved=[i for i in instructions if i.address<first_bl and i.mnemonic=='mov' and i.op_str.endswith(', x30')]
        if len(saved)!=1:
            raise ValueError('entry LR save before helper calls not proved')
        result={'app':app_fp,'libosal':lib_fp,'import_visibility':symbol['st_other']['visibility'],
            'receive_plt_vma':hex(target),'receive_got_relocation_vma':hex(r['r_offset']),
            'relocation':'R_AARCH64_JUMP_SLOT','cold_app_direct_bl_callers':callers,
            'named_classifier_sites':[hex(a) for a in sorted(expected)],
            'additional_other_appfw_sites':[hex(a) for a in sorted(actual-expected)],
            'real_receive_vma':hex(real['st_value']),
            'observer_entry_lr_save':{'vma':hex(saved[0].address),'instruction':saved[0].mnemonic+' '+saved[0].op_str,'before_first_bl':True},
            'limits':'Static eligibility for interposition only. Actual loader scope, RTLD_NEXT target, guest TID and runtime GOT value require a separately authorized same-run observation.'}
        print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':
    main()
