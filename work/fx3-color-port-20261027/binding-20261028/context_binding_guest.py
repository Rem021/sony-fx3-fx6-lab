#!/usr/bin/env python3
"""Original ImageParam sync context producer -> resource allocation, bounded inputs."""
import json,struct
from unicorn import arm_const as R
from caller_binding_guest import Guest as CallerGuest,HERE,image,BASE,PIN,DATA,OBJ,OUT,OWNERS,RECORDS

VECTOR=DATA+0x4000
PARAM=DATA+0x5000
HEADER=DATA+0x7000
PRODUCER_SPANS=[(0x3004ca,0x3005bc),(0x300654,0x300696),(0x3007c2,0x30082c)]


class Guest(CallerGuest):
    def code(self,u,pc,size,unused):
        off=pc-BASE
        if pc!=self.stop_point and any(a<=off<z for a,z in PRODUCER_SPANS):
            self.instructions+=1;return
        super().code(u,pc,size,unused)

    def sync_context(self,raw_900,raw_908,flag):
        u=self.u;u.mem_write(OBJ,b'\0'*0x3000)
        u.mem_write(VECTOR,b'\0'*0x40);u.mem_write(PARAM,b'\0'*0x1000)
        u.mem_write(HEADER,b'\0'*0x400)
        u.mem_write(VECTOR,struct.pack('<I',HEADER));u.mem_write(VECTOR+0xc,struct.pack('<I',PARAM))
        u.mem_write(PARAM+0x900,struct.pack('<I',raw_900))
        u.mem_write(PARAM+0x908,struct.pack('<I',raw_908))
        u.mem_write(0x147d018,bytes([flag]))
        # These are live-ins at the reviewed fragment entry. No camera scene is assumed.
        self.fragment(0x3004ca,0x300696,{4:OBJ,11:VECTOR,10:0x147d00f})
        return list(struct.unpack('<4I',u.mem_read(OBJ+0x1210,16)))


def main():
    b=image();cases=[];total=0;composed=[]
    for raw_900 in range(5):
        for raw_908 in range(8):
            for flag in [0,1]:
                g=Guest(b);fields=g.sync_context(raw_900,raw_908,flag)
                if raw_908 in [1,5,6,7]:expected=[8,10 if flag else 8,1,2 if flag else 1]
                elif raw_908 in [2,3,4]:expected=[[1,1,1,1],[1,5,1,2],[5,1,2,1],[5,5,2,2],[5,7,2,4]][raw_900]
                else:expected=[0,0,0,0]
                assert fields==expected,(raw_900,raw_908,flag,fields,expected)
                item=dict(parameter_900_raw=raw_900,parameter_908_raw=raw_908,global_147d018_raw=flag,
                          object_1210_1214_1218_121c=fields)
                cases.append(item)
                if fields[1] in [1,5,7]:
                    owner=g.bind_current_object(0)
                    group={1:0,5:5,7:4}[fields[1]]
                    assert owner==0x80000001 | group<<16
                    # Consume the producer-created context and allocated handle without resetting the object.
                    param=bytearray(0x50);struct.pack_into('<I',param,0,22);struct.pack_into('<I',param,8,11)
                    struct.pack_into('<II',param,0x10,100,800);g.u.mem_write(OBJ+0x10d8,bytes(param))
                    assert g.color_step()==dict(state=1,look=0,pending=0,commands=0)
                    assert g.color_step()==dict(state=2,look=22,pending=1,commands=1)
                    assert g.commands[0][1:3]==(22,group)
                    composed.append(dict(**item,computed_owner=hex(owner),driver_group=group,command=list(g.commands[0])))
                total+=g.instructions
    no_vfx=[]
    for context in [8,9,10]:
        g=Guest(b);g.u.mem_write(OUT,struct.pack('<I',0xa7a7a7a7))
        status=g.call(0x3c7574,[context,15,0x100,0],[0,0,1,0,0,OUT,0])
        assert status==0 and not g.allocations
        assert struct.unpack('<I',g.u.mem_read(OUT,4))[0]==0xa7a7a7a7
        no_vfx.append(dict(context=context,status=status,output_slot_unchanged=True,allocator_calls=len(g.allocations)))
        total+=g.instructions
    result=dict(status='PASS_ORIGINAL_CONTEXT_PRODUCER_TO_ALLOCATOR_TO_COLOR_SDK',cp_sha256=PIN,
                context_cases=cases,composed_cases=composed,no_vfx_cases=no_vfx,original_instructions=total,
                producer={'file_fragment':'0x3004ca..0x300696 with original branches to 0x3007c2..0x30082c',
                          'source_name':'ImageParam_Sync.cpp from referenced original fatal diagnostic string',
                          'input_fields':['parameter object +0x900','parameter object +0x908','global VA 0x147d018'],
                          'output_fields':['object +0x1210','object +0x1214','object +0x1218','object +0x121c']},
                fixtures='Parameter object, pointer vector, header, global flag, other zero fields and function-fragment live-ins are declared. Resource hardware/OSAL and SDK pre/EI/queue boundaries inherited explicitly from caller_binding_guest.py. Look 22 selection is an explicit fixture.',
                scope='Original ImageParam sync instructions now produce the graph context used by original resource allocation and original color SDK. Raw parameter enum meanings, their normal scene producers, actual MAIN/monitor pixel routing, hardware submission and camera flashing remain unproved. Resource ID 22 and look ID 22 belong to different domains.')
    (HERE/'context-binding-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'context cases',len(cases),'composed',len(composed),'no VFX',len(no_vfx),'original instructions',total)


if __name__=='__main__':main()
