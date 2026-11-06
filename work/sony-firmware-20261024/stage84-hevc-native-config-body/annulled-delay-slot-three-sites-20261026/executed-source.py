#!/usr/bin/env python3
"""Retain CODE observations of original BEQL/BREAK with execution controls."""
from pathlib import Path
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import native_body as a


def run(blob,divisor,entry,dividend_register,divisor_register,break_offset):
    u,r=a.u,a.reg
    uc=u.Uc(u.UC_ARCH_MIPS,u.UC_MODE_MIPS32|u.UC_MODE_LITTLE_ENDIAN)
    uc.ctl_set_cpu_model(r.UC_CPU_MIPS32_24KC)
    uc.mem_map(0,(len(blob)+4095)&-4096,u.UC_PROT_READ|u.UC_PROT_EXEC)
    uc.mem_write(0,blob);uc.mem_map(a.STOP_PA,4096,u.UC_PROT_READ|u.UC_PROT_EXEC)
    for reg,value in ((getattr(r,'UC_MIPS_REG_'+dividend_register),10),(getattr(r,'UC_MIPS_REG_'+divisor_register),divisor),
                      (r.UC_MIPS_REG_SP,a.SP),(r.UC_MIPS_REG_RA,a.STOP)):
        uc.reg_write(reg,value)
    state={'pcs':[],'interrupts':[],'stop':None,'error':None}
    def code(uc,pc,size,user):
        state['pcs'].append(hex(pc))
        if pc==a.STOP:state['stop']='returned';uc.emu_stop()
    def intr(uc,number,user):
        state['interrupts'].append(number);state['stop']='native_interrupt';uc.emu_stop()
    uc.hook_add(u.UC_HOOK_CODE,code);uc.hook_add(u.UC_HOOK_INTR,intr)
    try:uc.emu_start(a.IMAGE+entry,0,timeout=1000000,count=0)
    except u.UcError as e:state['error']=str(e);state['stop']='native_engine_exception'
    state.update({'entry':hex(a.IMAGE+entry),'break_PC':hex(a.IMAGE+break_offset),
                  'declared_dividend':10,'declared_divisor':divisor,
                  'result_v0':uc.reg_read(r.UC_MIPS_REG_V0),
                  'SP_after':hex(uc.reg_read(r.UC_MIPS_REG_SP)),
                  'PC_after':hex(uc.reg_read(r.UC_MIPS_REG_PC)),
                  'actual_source_words_hex':blob[entry:entry+24].hex(),
                  'memory_read_write_hooks_installed':False,
                  'original_image_unchanged':bytes(uc.mem_read(0,len(blob)))==blob,
                  'no_instruction_NOP_replacement_PC_write_or_fake_return':True})
    assert hex(a.IMAGE+break_offset) in state['pcs']
    assert state['original_image_unchanged'] and state['SP_after']==hex(a.SP)
    if divisor:
        assert state['stop']=='returned' and state['result_v0']==10//divisor
        assert not state['interrupts'] and state['error'] is None
    else:
        assert state['stop'] in ('native_interrupt','native_engine_exception')
    return state


def main():
    a.im.volume();out=STAGE/'annulled-delay-slot-three-sites-20261026';assert not out.exists()
    blob=a.prev.p.a.v.VCD_PATH.read_bytes()
    assert a.im.sha(blob)==a.im.PINS[str(a.prev.p.a.v.VCD_PATH.relative_to(a.BASE))]
    cases=[run(blob,d,*site) for site in ((0x19854c,'V0','V1',0x198554),
                                        (0x1984e8,'A0','T0',0x1984f0),
                                        (0x198500,'V1','T0',0x198508)) for d in (1,2,0)]
    result={'status':'PASS_CODE_CALLBACK_CAN_OBSERVE_ANNULLED_BEQL_DELAY_BREAK',
            'source_image_sha256':a.im.sha(blob),'source_script_sha256':a.im.sha(Path(__file__).read_bytes()),
            'cases':cases,'scope':'Local Unicorn2.1.4 MIPS32_24KC original DIVU/BEQL/BREAK sequence. '
                                    'CODE observation is not proof of architectural execution of an annulled delay slot. '
                                    'Positive division returns; zero control traps. No universal claim about other instructions or engines.'}
    out.mkdir();a.im.write_json(out/'probe-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
