#!/usr/bin/env python3
"""Bounded original LIRO .text+0xc28 wrapper with explicit external call stubs."""
from hashlib import sha256
import json
import struct

from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R

from analyze_binding import FILES, HERE, pinned

TEXT_GUEST=0x10000000
STUBS={'liro_disable_hook':0x11000000,
       'osal_rcv_msg_tmo':0x11000010,
       'liro_enable_hook':0x11000020}
STACK=0x30000000
OUT=0x20000000
STOP=0x60000000
ENTRY=0xc28
END=0xc74


def reg(uc,name):return uc.reg_read(getattr(R,'UC_ARM64_REG_'+name))


def encode_bl(pc,target):
    delta=target-pc
    assert delta%4==0 and -(1<<27)<=delta<(1<<27)
    return struct.pack('<I',0x94000000|((delta//4)&0x3ffffff))


def run(data,status):
    # ELF .text sh_offset is 0x68. Original code only is mapped at section VA.
    text=data[0x68:0x68+0x9b2c]
    uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    uc.mem_map(TEXT_GUEST,0xa000);uc.mem_write(TEXT_GUEST,text)
    patches=[]
    for off,name in [(0xc44,'liro_disable_hook'),(0xc54,'osal_rcv_msg_tmo'),
                     (0xc5c,'liro_enable_hook')]:
        original=text[off:off+4]
        patch=encode_bl(TEXT_GUEST+off,STUBS[name])
        uc.mem_write(TEXT_GUEST+off,patch)
        patches.append({'original_section_offset':hex(off),'original_file_offset':hex(0x68+off),
                        'original_bytes':original.hex(),'guest_relocation_bytes':patch.hex(),
                        'relocation_symbol':name,'guest_target':hex(STUBS[name])})
    uc.mem_map(0x11000000,0x1000)
    for addr in STUBS.values():uc.mem_write(addr,bytes.fromhex('c0035fd6'))
    uc.mem_map(STACK,0x10000);uc.mem_write(STACK,b'\xc7'*0x10000)
    uc.mem_map(OUT,0x1000);uc.mem_write(OUT,b'\xa5'*0x1000)
    uc.mem_map(STOP,0x1000)
    uc.reg_write(R.UC_ARM64_REG_X0,0x2ae085a)
    uc.reg_write(R.UC_ARM64_REG_X1,OUT+0x100)
    uc.reg_write(R.UC_ARM64_REG_X2,0xffffffff)
    uc.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000)
    uc.reg_write(R.UC_ARM64_REG_LR,STOP)
    saved={f'X{i}':0x77770000+i for i in range(19,30)}
    for name,value in saved.items():uc.reg_write(getattr(R,'UC_ARM64_REG_'+name),value)
    state={'provider_entry_request':'0x2ae085a','provider_entry_out_ptr':hex(OUT+0x100),
           'provider_entry_timeout':'0xffffffff','external_status_fixture':status,
           'guest_patches':patches,'stub_calls':[],'original_pcs':[],'writes':[],'violations':[]}
    reverse={addr:name for name,addr in STUBS.items()}

    def code(machine,pc,size,user):
        if pc in reverse:
            name=reverse[pc]
            state['stub_calls'].append({'symbol':name,'pc':hex(pc),'x0':hex(reg(machine,'X0')),
                                        'x1':hex(reg(machine,'X1')),'w2':hex(reg(machine,'W2')),
                                        'lr':hex(reg(machine,'LR'))})
            machine.reg_write(R.UC_ARM64_REG_X0,status if name=='osal_rcv_msg_tmo' else 0)
            return
        if not TEXT_GUEST+ENTRY<=pc<TEXT_GUEST+END:
            state['violations'].append({'kind':'outside_original_wrapper','pc':hex(pc)})
            machine.emu_stop();return
        state['original_pcs'].append(hex(pc-TEXT_GUEST))

    def write(machine,access,address,size,value,user):
        if not (STACK<=address and address+size<=STACK+0x10000):
            state['violations'].append({'kind':'outside_stack_write','address':hex(address),'size':size})
            machine.emu_stop()
        state['writes'].append({'pc':hex(reg(machine,'PC')),'address':hex(address),
                                'size':size,'value':hex(value)})

    uc.hook_add(UC_HOOK_CODE,code);uc.hook_add(UC_HOOK_MEM_WRITE,write)
    uc.emu_start(TEXT_GUEST+ENTRY,STOP,count=200)
    assert not state['violations'] and reg(uc,'PC')==STOP and reg(uc,'SP')==STACK+0xf000
    assert len(state['original_pcs'])<200
    assert [c['symbol'] for c in state['stub_calls']]==list(STUBS)
    received=state['stub_calls'][1]
    assert (received['x0'],received['x1'],received['w2'])==('0x2ae085a',hex(OUT+0x100),'0xffffffff')
    assert reg(uc,'W0')==(status&0xffffffff)
    assert all(reg(uc,name)==value for name,value in saved.items())
    assert bytes(uc.mem_read(OUT+0x100,16))==b'\xa5'*16
    assert bytes(uc.mem_read(STACK+0xef00,16))==b'\xc7'*16
    state['return_pc']=hex(reg(uc,'PC'))
    state['return_w0']=hex(reg(uc,'W0'))
    state['sp_and_callee_saved_preserved']=True
    state['output_fixture_untouched']=True
    return state


def main():
    data=pinned('liro')
    results=[run(data,status) for status in (-7,0)]
    output={'liro_sha256':FILES['liro'][1],
            'original_wrapper_section_offset':'0xc28',
            'original_wrapper_file_offset':'0xc90',
            'original_wrapper_sha256':sha256(data[0x68+ENTRY:0x68+END]).hexdigest(),
            'budget_per_case':200,
            'guest_code_patches':'three original R_AARCH64_CALL26 sites retargeted to named external-call stubs; original wrapper instructions otherwise unchanged',
            'external_stubs':'liro_disable_hook and liro_enable_hook return 0; osal_rcv_msg_tmo returns declared status without producing an event; no original external implementation executed',
            'cases':results,'natural_event_observed':False,'kernel_loaded':False,
            'scope':'original LIRO wrapper argument forwarding and status return only'}
    (HERE/'wrapper-replay.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'status':'PASS','original_wrapper_cases':len(results),
                      'forwarded_request':'0x2ae085a','natural_event_observed':False}))


if __name__=='__main__':main()
