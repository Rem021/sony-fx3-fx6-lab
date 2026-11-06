#!/usr/bin/env python3
"""Legacy filename: Camera::EC capture/exposure parameter gate, NOT an encoder.

The original function and one-value guard extension run only in a CPU guest.
"""
import json
import struct
from hashlib import sha256
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm_const as R
from cp_look_route import image,BASE,HERE,branch_target
from ap_cp_message import PARAM,STACK,DATA,STOP

ENTRY,END=0x1cb8a8,0x1cb934
PATCH=0x1cb8b8


def machine(blob,extended=False):
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
    u.mem_map(BASE,(len(blob)+4095)&~4095);u.mem_write(BASE,blob)
    for a,n in [(PARAM&~4095,0x3000),(0x143c000,0x1000),(STACK,0x10000),(DATA,0x2000),(STOP,0x1000)]:u.mem_map(a,n)
    assert blob[PATCH:PATCH+2]==bytes.fromhex('0c29')
    if extended:u.mem_write(BASE+PATCH,bytes.fromhex('0d29'))
    count=[0];logs=[]
    def code(u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        if pc==0x9e6684:
            logs.append(u.reg_read(R.UC_ARM_REG_R1));u.reg_write(R.UC_ARM_REG_PC,u.reg_read(R.UC_ARM_REG_LR));return
        assert BASE+ENTRY<=pc<BASE+END,hex(pc);count[0]+=1
    def write(u,access,address,size,value,unused):
        assert (STACK<=address and address+size<=STACK+0x10000
                or any(DATA+0x100+f<=address and address+size<=DATA+0x100+f+4 for f in [0x794,0x798,0x79c,0x7a0,0x7a4,0x7b0])),hex(address)
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(value,shooting=1,gamut=0):
        u.mem_write(DATA,struct.pack('<I',PARAM));u.mem_write(DATA+0x100,b'\x5a'*0x800)
        for off,val in [(0xba0,value),(0xba4,shooting),(0xba8,1),(0xbac,gamut),(0xbb0,0),(0x76c,18)]:u.mem_write(PARAM+off,struct.pack('<I',val))
        u.reg_write(R.UC_ARM_REG_R0,DATA);u.reg_write(R.UC_ARM_REG_R1,DATA+0x100)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        before=len(logs)
        u.emu_start((BASE+ENTRY)|1,STOP+4,count=500)
        assert u.reg_read(R.UC_ARM_REG_PC)==STOP and u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        out=bytes(u.mem_read(DATA+0x100,0x800))
        fields=[struct.unpack_from('<I',out,x)[0] for x in [0x794,0x798,0x79c,0x7a0,0x7a4,0x7b0]]
        expected=[value if value<(13 if extended else 12) else 0,gamut,shooting,1,0,18]
        assert fields==expected
        assert out[:0x794]==b'\x5a'*0x794 and out[0x7b4:]==b'\x5a'*(0x800-0x7b4)
        return dict(input_base_look=value,output_fields=fields,invalid_value_logs=len(logs)-before)
    return run,count


def main():
    b=image();original,a=machine(b);candidate,z=machine(b,True)
    old=[original(i) for i in range(256)];new=[candidate(i) for i in range(256)]
    changes=[i for i in range(256) if old[i]!=new[i]]
    assert changes==[12]
    assert old[12]['output_fields'][0]==0 and old[12]['invalid_value_logs']==1
    assert new[12]['output_fields'][0]==12 and new[12]['invalid_value_logs']==0
    refs=[]
    for off in range(0,min(len(b)-4,0xee0000),2):
        x,y=struct.unpack_from('<HH',b,off)
        if branch_target(x,y,BASE+off)==BASE+ENTRY:refs.append(hex(off))
    result=dict(status='PASS_ORIGINAL_EC_GATE_AND_ONE_VALUE_EXTENSION',
                original_cases=old,candidate_cases=new,only_changed_input=12,
                original_instructions=a[0],candidate_instructions=z[0],
                source_function_sha256=sha256(b[ENTRY:END]).hexdigest(),
                caller_candidates=refs,
                patch_recipe={'file_offset':hex(PATCH),'original':'0c29','candidate':'0d29',
                              'instruction':'cmp r1,#12 -> cmp r1,#13','applied_to':'isolated guest memory only'},
                domain_evidence=['Camera::EC::EC_StateMachine::Execute()', 'EC_GetExtInfo.cpp',
                                 'EC_SetExtInfo.cpp', 'EC_CaptureRaw_CalcAe.cpp'],
                legacy_filename_is_not_encoder_evidence=True,
                scope='Camera::EC capture/exposure parameter builder only. Preserving the value here does not prove downstream image-processing acceptance or any MAIN pixel changes.')
    (HERE/'capture-parameter-gate-results.json').write_text(json.dumps(result,indent=2)+'\n')
    (HERE/'encoder-parameter-gate-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'original/candidate inputs',len(old),len(new),'changed',changes,'callers',refs)


if __name__=='__main__':main()
