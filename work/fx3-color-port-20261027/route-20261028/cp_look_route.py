#!/usr/bin/env python3
"""Bounded CP Thumb look selection and static caller audit. No device access."""
from pathlib import Path
from hashlib import sha256
import itertools
import json
import plistlib
import struct
import subprocess
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm_const as R

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IMAGE = ROOT / 'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
PIN = 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
BASE = 0x108000
ENTRY, END = 0x3266ec, 0x3267b4
GLOBAL = 0x1435c83
STACK, STOP, LOG = 0x50000000, 0x60000000, 0x009e6684


def image():
    info = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert info['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    b = IMAGE.read_bytes()
    assert sha256(b).hexdigest() == PIN
    assert struct.unpack_from('<I', b, 12)[0] == BASE + 12
    assert b[ENTRY:ENTRY+2] == bytes.fromhex('80b5')
    return b


def branch_target(a, z, pc):
    if a & 0xf800 != 0xf000 or z & 0xd000 != 0xd000:
        return None
    s, j1, j2 = (a >> 10) & 1, (z >> 13) & 1, (z >> 11) & 1
    i1, i2 = 1 ^ j1 ^ s, 1 ^ j2 ^ s
    imm = (s << 24) | (i1 << 23) | (i2 << 22) | ((a & 1023) << 12) | ((z & 2047) << 1)
    if imm & (1 << 24):
        imm -= 1 << 25
    return pc + 4 + imm


def static(b):
    targets = {BASE+ENTRY:'GetVfxMlutLookname_candidate', BASE+0x3263fc:'SetVfxMlutParam_candidate'}
    refs = []
    for off in range(0, min(len(b)-4, 0xee0000), 2):
        a, z = struct.unpack_from('<HH', b, off)
        target = branch_target(a, z, BASE+off)
        if target in targets:
            refs.append(dict(file_offset=hex(off), target=hex(target), label=targets[target]))
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    ranges = [(ENTRY, END), (0x3263fc,0x326600), (0x326680,0x3266d0)]
    ranges += [(max(0,int(r['file_offset'],16)-128),int(r['file_offset'],16)+128) for r in refs]
    out = HERE/'disassembly'
    out.mkdir(exist_ok=True)
    for a, z in ranges:
        (out/f'cp-{a:08x}-{z:08x}.txt').write_text('\n'.join(
            f'{i.address-BASE:08x}: {i.mnemonic} {i.op_str}' for i in md.disasm(b[a:z],BASE+a))+'\n')
    return refs


def guest(b):
    u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    u.mem_map(BASE, (len(b)+4095)&~4095)
    u.mem_write(BASE,b)
    u.mem_map(GLOBAL&~4095,0x1000)
    u.mem_map(STACK,0x10000)
    u.mem_map(STOP,0x1000)
    u.mem_write(STACK,b'\xa7'*0x10000)
    instructions = [0]
    log_calls=[]
    def code(u,pc,size,unused):
        if pc == STOP:
            u.emu_stop();return
        if pc == LOG:
            log_calls.append(True)
            u.reg_write(R.UC_ARM_REG_PC,u.reg_read(R.UC_ARM_REG_LR));return
        assert BASE+ENTRY <= pc < BASE+END, hex(pc)
        instructions[0]+=1
    def write(u,access,address,size,value,unused):
        assert STACK <= address and address+size <= STACK+0x10000, hex(address)
    u.hook_add(UC_HOOK_CODE,code)
    u.hook_add(UC_HOOK_MEM_WRITE,write)
    def case(args,override=0):
        for reg,val in zip([R.UC_ARM_REG_R0,R.UC_ARM_REG_R1,R.UC_ARM_REG_R2,R.UC_ARM_REG_R3],args):
            u.reg_write(reg,val)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000)
        u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.mem_write(STACK+0xf000,struct.pack('<II',*args[4:]))
        u.mem_write(GLOBAL,bytes([override]))
        before=instructions[0];logs_before=len(log_calls)
        u.emu_start((BASE+ENTRY)|1,STOP+4,count=1000)
        assert u.reg_read(R.UC_ARM_REG_PC)==STOP
        assert u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        return dict(args=list(args),override_fixture=override,look=u.reg_read(R.UC_ARM_REG_R0),
                    instructions=instructions[0]-before,log_calls=len(log_calls)-logs_before)
    cases=[case((a,look,c,d,e,f)) for a in range(4) for look in range(12)
           for c,d,e,f in itertools.product(range(2),repeat=4)]
    overrides=[case((1,2,1,0,0,0),v) for v in [1,22,29,255]]
    assert overrides[1]['look']==22 and overrides[-1]['look']==0
    return dict(cases=cases,override_cases=overrides,
                selected_look_IDs=sorted({c['look'] for c in cases}),
                original_instructions=instructions[0],
                scope='Input domains and global byte are declared fixtures. Function is original Thumb code. No real CP instance, route, sensor, queue, DMA, frame or output is asserted.')


def main():
    b=image();refs=static(b);result=guest(b)
    result.update(image_sha256=PIN,entry_offset=hex(ENTRY),entry_VA=hex(BASE+ENTRY),
                  source_function_sha256=sha256(b[ENTRY:END]).hexdigest(),static_caller_candidates=refs)
    (HERE/'cp-look-route-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['cases']},indent=2))
    print('normal cases',len(result['cases']))


if __name__=='__main__':main()
