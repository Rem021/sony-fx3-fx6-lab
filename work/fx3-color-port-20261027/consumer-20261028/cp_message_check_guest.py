#!/usr/bin/env python3
"""Original CP registration, setter and consistency comparator; no IPC."""
from pathlib import Path
import json, struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm_const as R
from ec_mode_guest import image,BASE,PIN,PARAM,STACK,DATA,STOP,setup,prepare,preserved,HERE

OFFSETS=[0xba0,0xba4,0xba8,0xbac,0xbb0]
CHECK_START,CHECK_END=0x1f605c,0x1f60f8


def main():
    b=image();registration=struct.unpack_from('<5I',b,0xe003a0)
    assert registration==(0x4151,BASE+0x689f9c+1,0,0,BASE+CHECK_START+1)
    u=setup(b);u.mem_map(0x1435000,0x1000)
    logs=[];count=[0]
    def string(addr):
        off=addr-BASE
        assert 0<=off<len(b)
        return b[off:b.index(0,off)].decode()
    def code(u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        if pc==0x9e6684:
            logs.append(dict(format=string(u.reg_read(R.UC_ARM_REG_R0)),
                             tag=string(u.reg_read(R.UC_ARM_REG_R1)),
                             current=u.reg_read(R.UC_ARM_REG_R2),requested=u.reg_read(R.UC_ARM_REG_R3)))
            u.reg_write(R.UC_ARM_REG_PC,u.reg_read(R.UC_ARM_REG_LR));return
        off=pc-BASE
        assert 0x689f9c<=off<0x68a002 or CHECK_START<=off<CHECK_END or 0x689c38<=off<0x689c42,hex(pc)
        count[0]+=1
    writes=[]
    def write(u,access,address,size,value,unused):
        assert STACK<=address and address+size<=STACK+0x10000 or any(
            PARAM+f<=address and address+size<=PARAM+f+4 for f in OFFSETS+[0x76c]),hex(address)
        if not STACK<=address<STACK+0x10000:writes.append([address,size])
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    def call(entry,args):
        prepare(u)
        for i,v in enumerate(args):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),v)
        u.emu_start((BASE+entry)|1,STOP+4,count=500)
        assert u.reg_read(R.UC_ARM_REG_PC)==STOP;preserved(u)
        return u.reg_read(R.UC_ARM_REG_R0)
    def init(wire,old=None):
        u.mem_write(DATA,b'\xa7'*8+bytes(wire)+b'\xa7'*19)
        for off,v in zip(OFFSETS,old or [0x11223344]*5):u.mem_write(PARAM+off,struct.pack('<I',v))
        u.mem_write(PARAM+0x76c,struct.pack('<I',17))
        u.mem_write(0x1435c68,b'\0')
    def compare(flag):
        before=len(logs);w=len(writes)
        call(CHECK_START,[DATA,flag]);assert len(writes)==w
        return logs[before:]
    rows=[]
    for base_look in range(256):
        wire=[base_look,1,1,0,0];init(wire)
        assert call(0x689f9c,[DATA])==1
        fields=[struct.unpack('<I',u.mem_read(PARAM+x,4))[0] for x in OFFSETS]
        assert fields==wire and struct.unpack('<I',u.mem_read(PARAM+0x76c,4))[0]==18
        assert compare(1)==[]
        rows.append(dict(base_look=base_look,setter_fields=fields,matched_comparison_logs=0))
    # The comparator reports mismatch. It is not a byte-range admission predicate.
    mismatches=[]
    for base_look in [0,11,12,13,255]:
        wire=[base_look,1,1,0,0];init(wire,[0x11223344,1,1,0,0])
        found=compare(1);assert len(found)==1
        assert found[0]['current']==0x11223344 and found[0]['requested']==base_look
        assert compare(0)==[]
        mismatches.append(dict(base_look=base_look,logs=found))
    init([12,3,1,0,0],[0,0,0,1,0]);assert call(0x689f9c,[DATA])==1
    sticky=compare(1);assert len(sticky)==1 and sticky[0]['current']==1 and sticky[0]['requested']==0
    # Change each one of the five fields independently to prove comparator coverage.
    each=[]
    for field in range(5):
        old=[12,1,1,0,0];old[field]+=1;init([12,1,1,0,0],old)
        found=compare(1);assert len(found)==1
        each.append(dict(field_index=field,logs=found))
    result=dict(status='PASS_ORIGINAL_CP_SETTER_AND_COMPARATOR',cp_sha256=PIN,
                registration={'file':'0xe003a0','words':[hex(x) for x in registration],
                              'layout_scope':'Five-word registration recovered from paired unique handler/checker pointers; dispatcher-wide contract is still untraced.'},
                setter_byte_cases=rows,mismatch_probes=mismatches,independent_field_probes=each,
                mode3_sticky_color_gamut_probe=sticky,original_instructions=count[0],
                scope='Original registered setter accepts these declared message bytes; registered CheckSetParamBasePictureSetting compares current/requested values and logs differences. No enum-range rejection occurs inside either tested function. No AP model/UI admission, IPC transport or recorded image is proved.')
    (HERE/'cp-message-check-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'base bytes',len(rows),'original instructions',count[0])


if __name__=='__main__':main()
