#!/usr/bin/env python3
"""Exhaustive uint16 inputs to the original pure ImgModeDefaultParam dispatcher."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'route-20261028'))
from cp_look_route import image,BASE,PIN
DATA,STACK,STOP=0x50000000,0x60000000,0x70000000

def main():
    raw=image();u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.mem_map(BASE,(len(raw)+4095)&-4096);u.mem_write(BASE,raw)
    for at in [DATA,STACK,STOP]:u.mem_map(at,4096)
    instructions=[0]
    def code(u,pc,size,user):
        if pc==STOP:u.emu_stop();return
        assert 0x251fa4<=pc<0x25217e,hex(pc)
        instructions[0]+=1;assert instructions[0]<10000000
    def write(u,access,at,size,value,user):assert DATA<=at and at+size<=DATA+16,hex(at)
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
    accepted=[];returns={};field4={};digest=hashlib.sha256()
    for mode in range(65536):
        u.mem_write(DATA,b'\xa7'*16);u.reg_write(R.UC_ARM_REG_R0,mode);u.reg_write(R.UC_ARM_REG_R1,0);u.reg_write(R.UC_ARM_REG_R2,DATA)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf00);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.emu_start(0x251fa5,STOP+4,count=500)
        assert u.reg_read(R.UC_ARM_REG_PC)==STOP and u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf00
        result=u.reg_read(R.UC_ARM_REG_R0);assert result in [0,1]
        output=bytes(u.mem_read(DATA,16));assert output[1:4]==b'\xa7'*3
        value=struct.unpack_from('<I',output,4)[0];field4[value]=field4.get(value,0)+1;returns[result]=returns.get(result,0)+1
        digest.update(struct.pack('<II',mode,result)+output)
        if result==1:accepted.append(dict(input=hex(mode),output_byte0=output[0],output_word4=value,output_word8=struct.unpack_from('<I',output,8)[0],output_wordc=struct.unpack_from('<I',output,12)[0]))
    assert field4=={0:65536}
    assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
    result=dict(cp_sha256=PIN,input_domain=dict(lower=0,upper=65535,count=65536),return_histogram=returns,output_word4_histogram=field4,
                supported_inputs=accepted,ordered_result_sha256=digest.hexdigest(),original_instructions=instructions[0],
                source=dict(va='0x251fa4',bytes=0x1da,sha256=hashlib.sha256(raw[0x149fa4:0x14a17e]).hexdigest()),
                conclusion='For every tested uint16 input the original output word+4 is zero. The reviewed wrapper returns that word, so these inputs do not make its producer select buffer type2.',
                scope='One exhaustive domain check, not 65536 independent full-frame acceptances. Original leaf code only; no import, lookup reply, normal input-mode meaning, values outside uint16, complete pipeline, native target or device action.')
    (HERE/'mode-default-domain-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(input_count=65536,supported_inputs=len(accepted),output_word4=field4,instructions=instructions[0],device_actions=0)))

if __name__=='__main__':main()
