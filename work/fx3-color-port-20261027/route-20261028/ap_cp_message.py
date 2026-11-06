#!/usr/bin/env python3
"""Original AP message builder -> CP setter -> CP look selectors, CPU-only.

This composes independently invoked original functions, not an actual IPC session.
"""
from pathlib import Path
from hashlib import sha256
import itertools
import json
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_ARCH_ARM64, UC_MODE_THUMB, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm_const as A, arm64_const as X
from cp_look_route import image, BASE, HERE, ENTRY, END, GLOBAL

AP = HERE.parents[2] / 'work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so'
AP_PIN = '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
STACK, DATA, STOP = 0x50000000, 0x51000000, 0x60000000
PARAM = 0x10a8de0
FIELDS = ['base_look','shooting_mode','input_gamut','color_gamut','target_display']


def ap_machine(blob):
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    for start, size in [(0x2e26000,0x2000),(0x3975000,0x1000)]:
        u.mem_map(start,size);u.mem_write(start,blob[start:start+size])
    for start, size in [(STACK,0x10000),(DATA,0x1000),(STOP,0x1000)]:u.mem_map(start,size)
    counter=[0]
    def code(u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        assert 0x2e26fcc<=pc<0x2e2716c,hex(pc)
        # Logging/error path for an invalid Log setting is outside this experiment.
        assert not 0x2e270dc<=pc<0x2e27168,hex(pc)
        counter[0]+=1
    def write(u,access,address,size,value,unused):
        assert (STACK<=address and address+size<=STACK+0x10000
                or DATA+8<=address and address+size<=DATA+13),hex(address)
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(args):
        u.mem_write(DATA,b'\x5a'*32)
        for i,v in enumerate(args):u.reg_write(getattr(X,f'UC_ARM64_REG_X{i}'),v)
        u.reg_write(X.UC_ARM64_REG_X7,DATA)
        for i in range(19,30):u.reg_write(getattr(X,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        u.reg_write(X.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(X.UC_ARM64_REG_LR,STOP)
        u.emu_start(0x2e26fcc,STOP+4,count=1000)
        assert u.reg_read(X.UC_ARM64_REG_PC)==STOP
        assert u.reg_read(X.UC_ARM64_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(X,f'UC_ARM64_REG_X{i}'))==0x77770000+i for i in range(19,30))
        raw=bytes(u.mem_read(DATA,32));assert raw[:8]==b'\x5a'*8 and raw[13:]==b'\x5a'*19
        return list(raw[8:13])
    return run,counter


def cp_machine(blob,selector_va=None,selector_bytes=None):
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
    u.mem_map(BASE,(len(blob)+4095)&~4095);u.mem_write(BASE,blob)
    for start,size in [(PARAM&~4095,0x3000),(GLOBAL&~4095,0x1000),(STACK,0x10000),(DATA,0x1000),(STOP,0x1000)]:u.mem_map(start,size)
    if selector_va is not None:
        assert selector_bytes and selector_va%4096==0
        u.mem_map(selector_va,4096);u.mem_write(selector_va,selector_bytes)
    counter=[0]
    def code(u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        off=pc-BASE
        assert (0x689f9c<=off<0x68a002 or 0x8d1ad6<=off<0x8d1aee or ENTRY<=off<END
                or selector_va is not None and selector_va<=pc<selector_va+len(selector_bytes)),hex(pc)
        counter[0]+=1
    def write(u,access,address,size,value,unused):
        assert (STACK<=address and address+size<=STACK+0x10000
                or any(PARAM+off<=address and address+size<=PARAM+off+4 for off in [0xba0,0xba4,0xba8,0xbac,0xbb0,0x76c])),hex(address)
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    def call(entry,args,extra=()):
        for i,v in enumerate(args):u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),v)
        for i in range(4,12):u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(A.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(A.UC_ARM_REG_LR,STOP|1)
        if extra:u.mem_write(STACK+0xf000,struct.pack('<'+'I'*len(extra),*extra))
        u.emu_start((BASE+entry)|1,STOP+4,count=2000)
        assert u.reg_read(A.UC_ARM_REG_PC)==STOP and u.reg_read(A.UC_ARM_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(A,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        return u.reg_read(A.UC_ARM_REG_R0)
    def run(wire,old_gamut,field78,field7c,override=0):
        u.mem_write(DATA,b'\0'*8+bytes(wire)+b'\x5a'*19)
        u.mem_write(PARAM+0x76c,struct.pack('<I',17))
        for off in [0xba0,0xba4,0xba8,0xbac,0xbb0]:u.mem_write(PARAM+off,struct.pack('<I',old_gamut if off==0xbac else 0x5a))
        assert call(0x689f9c,[DATA])==1
        values=[struct.unpack('<I',u.mem_read(PARAM+off,4))[0] for off in [0xba0,0xba4,0xba8,0xbac,0xbb0]]
        expected=wire[:];expected[3]=old_gamut if wire[1]==3 else wire[3]
        assert values==expected
        assert struct.unpack('<I',u.mem_read(PARAM+0x76c,4))[0]==18
        adjusted=call(0x8d1ad6,values[:2]+[field78])
        u.mem_write(GLOBAL,bytes([override]))
        look=call(selector_va-BASE if selector_va is not None else ENTRY,
                  [values[1],adjusted,values[3],values[2]],[values[4],field7c])
        return dict(wire=wire,previous_color_gamut_fixture=old_gamut,field78_fixture=field78,
                    field7c_fixture=field7c,cp_fields=dict(zip(FIELDS,values)),adjusted_base_look=adjusted,
                    override_fixture=override,selected_look=look)
    return run,counter


def main():
    ap=AP.read_bytes();assert sha256(ap).hexdigest()==AP_PIN
    cp=image();builder,ap_counter=ap_machine(ap);receiver,cp_counter=cp_machine(cp)
    samples=[];unique={}
    for args in itertools.product([0,1,2,3,11],range(2),range(4),range(2),range(2),range(16),[0,1]):
        wire=builder(args)
        samples.append(dict(model_inputs=list(args),wire=wire))
        unique.setdefault(tuple(wire),list(args))
    cases=[]
    for wire in unique:
        for old,flag78,flag7c in itertools.product(range(2),repeat=3):
            cases.append(receiver(list(wire),old,flag78,flag7c))
    normal_ids=sorted({x['selected_look'] for x in cases})
    assert 22 not in normal_ids
    forced=receiver([9,1,1,1,0],1,0,0,22)
    assert forced['selected_look']==22
    # Independently verify the CP's own ID 22 registry, rather than borrowing A64 numbering.
    idx,ptr,n,nameptr=struct.unpack_from('<4I',cp,0xbf8ffc)
    assert (idx,ptr,n)==(22,0x2015794,70)
    name=cp[nameptr-BASE:cp.index(0,nameptr-BASE)].decode()
    assert name=='MLUT_LOOKNAME_SL3SG3_TO_ACESREC709'
    result=dict(ap_sha256=AP_PIN,cp_sha256=sha256(cp).hexdigest(),
                source_spans={'ap_builder':{'VA':'0x2e26fcc','bytes':0x1a0,'sha256':sha256(ap[0x2e26fcc:0x2e2716c]).hexdigest()},
                              'cp_receiver':{'file':'0x689f9c','bytes':0x66,'sha256':sha256(cp[0x689f9c:0x68a002]).hexdigest()}},
                model_argument_order=['setting_select_lut','is_exist_user_lut','setting_log_shooting','setting_input_signal','setting_gamut','setting_picture_profile','general_shooting_mode'],
                ap_samples=samples,unique_wire_count=len(unique),cp_cases=cases,
                normal_selected_look_IDs=normal_ids,forced_memory_only_fixture=forced,
                CP_ID22_registry={'name':name,'descriptors':hex(ptr),'count':n},
                original_AP_instructions=ap_counter[0],original_CP_instructions=cp_counter[0],
                scope='Original functions composed across declared messages and globals. No actual IPC, current scene, menu interaction, DMA or output proof. Field78/7c remain raw conditional fixtures.')
    (HERE/'ap-cp-message-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('AP cases',len(samples),'unique messages',len(unique),'CP cases',len(cases))
    print('normal IDs',normal_ids,'forced ID',forced['selected_look'])
    print('native instructions',ap_counter[0],cp_counter[0])


if __name__=='__main__':main()
