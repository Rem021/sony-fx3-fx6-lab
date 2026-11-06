#!/usr/bin/env python3
"""Original GetInfo stage record -> original copies/vector -> sync consumer."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'binding-20261028'))
from context_binding_guest import Guest as ContextGuest,image,BASE,PIN,DATA,OBJ,OUT
SCENE=DATA+0x4000
VECTOR=DATA+0xa000
SOURCE=SCENE+0x13a8
SPANS=[(0x8c9038,0x8c946a),(0x8ce7ac,0x8ce7d0),(0x8cf210,0x8cf320),(0x8cdea8,0x8cdecc),(0x450400,0x450700),(0x2ffa94,0x2ffab4)]

class Guest(ContextGuest):
    def __init__(self,raw):
        super().__init__(raw);self.constructor_writes=[];self.record_constructor=False;self.copy_calls=0
    def code(self,u,pc,size,user):
        if pc!=self.stop_point and any(a<=pc-BASE<z for a,z in SPANS):
            self.instructions+=1
            if pc==0x558400:self.copy_calls+=1
            return
        return super().code(u,pc,size,user)
    def write(self,u,access,at,size,value,user):
        if self.record_constructor and SOURCE<=at and at+size<=SOURCE+0x32c:
            self.constructor_writes.append(dict(offset=hex(at-SOURCE),bytes=size,value=hex(value),pc=hex(u.reg_read(R.UC_ARM_REG_PC))))
        return super().write(u,access,at,size,value,user)
    def produce(self,stage,graph,live_flag,default=False,original_callsite=False):
        u=self.u;u.mem_write(OBJ,b'\0'*0x3000);u.mem_write(SCENE,b'\0'*0x50b0);u.mem_write(VECTOR,b'\xa7'*0xc8)
        # Declared non-device global inputs; ordinary override nibble is zero.
        u.mem_write(0x13c3168,struct.pack('<I',0));u.mem_write(0x1435c72,b'\0');u.mem_write(0x147d018,bytes([live_flag]))
        self.record_constructor=True
        if original_callsite:self.fragment(0x2ffa94,0x2ffab4,{6:SOURCE,8:0,5:0,10:0})
        elif default:self.call(0x9d1442,[SOURCE])
        else:self.call(0x9d1038,[1,0,0,stage],[graph,1,0,SOURCE])
        self.record_constructor=False
        descriptor=bytes(u.mem_read(SOURCE,0x32c))
        assert struct.unpack_from('<I',descriptor,0xc)[0]==graph
        assert struct.unpack_from('<I',descriptor,0x2c)[0]==stage
        self.fragment(0x8ce7ac,0x8ce7d0,{4:SCENE,5:SOURCE})
        assert bytes(u.mem_read(SCENE+0x16d4,0x32c))==descriptor
        assert bytes(u.mem_read(SCENE+0x1074,0x32c))==descriptor
        self.call(0x9d7210,[SCENE,VECTOR])
        param=struct.unpack('<I',u.mem_read(VECTOR+0xc,4))[0]
        assert param==SCENE+0xde0
        raw_900,raw_908=struct.unpack('<I',u.mem_read(param+0x900,4))[0],struct.unpack('<I',u.mem_read(param+0x908,4))[0]
        assert raw_900==graph and raw_908==struct.unpack_from('<I',descriptor,0x14)[0]
        before=bytes(u.mem_read(SCENE+0x16d4,0x32c))
        self.fragment(0x3004ca,0x300696,{4:OBJ,11:VECTOR,10:0x147d00f})
        assert bytes(u.mem_read(SCENE+0x16d4,0x32c))==before
        fields=list(struct.unpack('<4I',u.mem_read(OBJ+0x1210,16)))
        origin='original caller fragment' if original_callsite else 'original default wrapper' if default else 'declared function arguments'
        return dict(raw_constructor_stage_pointer=hex(stage),raw_graph_argument=graph,constructor_argument_origin=origin,declared_live_flag=live_flag,
                    descriptor_sha256=hashlib.sha256(descriptor).hexdigest(),original_constructor_writes=self.constructor_writes,
                    constructor_type_14=raw_908,vector_parameter_pointer=hex(param),parameter_900=raw_900,parameter_908=raw_908,
                    sync_fields_1210_1214_1218_121c=fields,original_memcpy_calls=self.copy_calls)

def main():
    raw=image();rows=[]
    fixtures=[('default_wrapper',0x416105,0,0,True,0,[0,0,0,0]),
              ('stage_40bb9d',0x40bb9d,0,0,False,1,[8,8,1,1]),
              ('stage_40bb9d_flag1',0x40bb9d,0,1,False,1,[8,10,1,2]),
              ('stage_40de65_single',0x40de65,0,0,False,3,[1,1,1,1]),
              ('stage_40fc09_two',0x40fc09,1,0,False,2,[1,5,1,2]),
              ('stage_40fc09_four',0x40fc09,4,0,False,2,[5,7,2,4]),
              ('original_caller_407a94',0x40fc09,0,0,False,2,[1,1,1,1])]
    for label,stage,graph,flag,default,expected_type,expected_fields in fixtures:
        guest=Guest(raw);row=guest.produce(stage,graph,flag,default,original_callsite=label=='original_caller_407a94');row['case']=label
        assert row['constructor_type_14']==expected_type and row['sync_fields_1210_1214_1218_121c']==expected_fields
        assert row['original_memcpy_calls']==2
        context=expected_fields[1]
        if context in [1,5,7]:
            owner=guest.bind_current_object(0);group={1:0,5:5,7:4}[context]
            assert owner==0x80000001|group<<16
            param=bytearray(0x50);struct.pack_into('<I',param,0,22);struct.pack_into('<I',param,8,11);struct.pack_into('<II',param,0x10,100,800)
            guest.u.mem_write(OBJ+0x10d8,bytes(param))
            guest.color_step();phase=guest.color_step();assert phase==dict(state=2,look=22,pending=1,commands=1)
            assert guest.commands[0][1:3]==(22,group)
            row['resource_result']=dict(computed_owner=hex(owner),group=group,command=list(guest.commands[0]),phase=phase)
        elif context in [8,10]:
            guest.u.mem_write(OUT,struct.pack('<I',0xa7a7a7a7))
            status=guest.call(0x3c7574,[context,15,0x100,0],[0,0,1,0,0,OUT,0])
            assert status==0 and not guest.allocations and struct.unpack('<I',guest.u.mem_read(OUT,4))[0]==0xa7a7a7a7
            row['resource_result']=dict(status=status,allocations=0,output_slot_unchanged=True)
        else:row['resource_result']=dict(boundary='zero context; resource request not attempted')
        row['instructions']=guest.instructions;rows.append(row)
    result=dict(cp_sha256=PIN,cases=rows,source_spans=[dict(file_offset=hex(a),bytes=z-a,sha256=hashlib.sha256(raw[a:z]).hexdigest()) for a,z in SPANS],
                scope='Original GetInfo.cpp constructor determines type at +0x14 from a source-listed stage pointer. One case executes original caller fragment 0x407a94..0x407ab4 to supply stage40fc09 and graph0 constants; another executes the original default wrapper. Other stage/graph arguments remain declared. Original ARM memcpy copies the record twice, original vector constructor supplies parameter pointers, original sync instructions produce contexts, and four cases continue through existing original allocator and colour SDK. Caller branch entry/live-ins, zeroed scene/header inputs, global mode/override flags, free owner state, hardware/OSAL success boundaries and look22 remain explicit fixtures. No complete normal caller or scene lifecycle, actual MAIN/monitor routing, source pixel domain, DMA, device, native code or flashable firmware is proven.')
    (HERE/'scene-context-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),original_constructor_to_sync_to_sdk=4,original_caller_supplies_stage_and_graph=1,original_no_vfx=2,default_zero_context=1,native_device_actions=0)))

if __name__=='__main__':main()
