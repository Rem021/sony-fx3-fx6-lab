#!/usr/bin/env python3
"""Original MLUT caller resource gate and callback-registration boundary."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'scene-binding-20261029'))
from scene_context_guest import Guest as SceneGuest,image,BASE,PIN,OBJ,DATA
from caller_binding_guest import STACK,STOP,RECORDS
SPANS=[(0x8cb454,0x8cb48a),(0x8cc1a8,0x8cc1ce),(0x8c7bac,0x8c7bda),
       (0x300236,0x300242),(0x8cb266,0x8cb28e),(0x8cdf6c,0x8cdf7e)]

class Guest(SceneGuest):
    def __init__(self,raw):
        super().__init__(raw);self.boundary=None;self.registration=False;self.entries={};self.latch_writes=[]
    def write(self,u,access,at,size,value,user):
        if at<=OBJ+0x120a<at+size:
            self.latch_writes.append(dict(address=hex(at),bytes=size,value=hex(value),pc=hex(u.reg_read(R.UC_ARM_REG_PC))))
        return super().write(u,access,at,size,value,user)
    def code(self,u,pc,size,user):
        if pc==self.stop_point:return super().code(u,pc,size,user)
        if pc in [0x4285c4,0x9d3558]:
            self.boundary=dict(operation='before_next_image_helper' if pc==0x4285c4 else 'before_object_virtual_dispatch',pc=hex(pc),native_call=False)
            u.emu_stop();return
        if pc==0x44d438 and self.registration:
            regs=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
            self.boundary=dict(operation='before_original_dispatcher',pc=hex(pc),dispatch_object_va=hex(regs[0]),packet_pointer=hex(regs[1]),object_pointer=hex(regs[2]),raw_argument=regs[3],
                               packet_words=[hex(v[0]) for v in struct.iter_unpack('<I',bytes(u.mem_read(regs[1],20)))],native_dispatch=False)
            u.emu_stop();return
        for entry,label in [(0x9d41a8,'resource_gate'),(0x9cfbac,'resource_checker'),(0x42e3fc,'mlut_controller')]:
            if pc==entry:self.entries[label]=self.entries.get(label,0)+1
        if any(a<=pc-BASE<z for a,z in SPANS):self.instructions+=1;return
        return super().code(u,pc,size,user)
    def prepare(self):
        produced=self.produce(0x40fc09,0,0,original_callsite=True)
        owner=self.bind_current_object(0);assert owner==0x80000001
        record=bytes(self.u.mem_read(RECORDS+22*64,64));assert record[:2]==b'\0\0' and record[4]==0 and record[5]==1
        param=bytearray(0x50);struct.pack_into('<I',param,0,22);struct.pack_into('<I',param,8,11);struct.pack_into('<II',param,0x10,100,800)
        self.u.mem_write(OBJ+0x10d8,bytes(param))
        return produced
    def invoke_prefix(self):
        self.boundary=None;before=dict(self.entries)
        u=self.u;u.reg_write(R.UC_ARM_REG_R0,OBJ);u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.emu_start(0x9d3455,STOP+4,count=40000)
        assert self.boundary and u.reg_read(R.UC_ARM_REG_PC)==int(self.boundary['pc'],16)
        return dict(boundary=dict(self.boundary),latch=bytes(u.mem_read(OBJ+0x120a,1))[0],phase=self.snapshot(),
                    entry_delta={k:v-before.get(k,0) for k,v in self.entries.items() if v-before.get(k,0)},instructions_total=self.instructions)
    def original_sync_clear(self):
        self.fragment(0x300236,0x300242,{4:OBJ})
        assert bytes(self.u.mem_read(OBJ+0x11c3,72))==b'\0'*72
    def register_boundary(self):
        self.registration=True;self.boundary=None;u=self.u
        for i,value in {0:0,4:OBJ,6:0}.items():u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),value)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.emu_start(0x9d3267,STOP+4,count=1000)
        assert self.boundary and self.boundary['operation']=='before_original_dispatcher'
        assert self.boundary['dispatch_object_va']=='0x13d7dd8' and self.boundary['object_pointer']==hex(OBJ)
        assert self.boundary['packet_words']==['0x9d36c1','0x0','0x9d3455','0x0','0x0']
        return dict(self.boundary)

def main():
    raw=image();rows=[]
    fixtures=[('original_fresh_empty_mask',None,None,0),('declared_mask_original_record',None,None,0),
              ('selected_word0_nonzero',0,1,0),('selected_byte5_zero',5,0,0),('selected_byte4_nonzero',4,1,0),
              ('prelatched',None,None,1)]
    for label,offset,value,latch in fixtures:
        guest=Guest(raw);producer=guest.prepare();mask_fixture=label!='original_fresh_empty_mask'
        if mask_fixture:guest.u.mem_write(OBJ+0x11c3+22,b'\1')
        if offset is not None:guest.u.mem_write(RECORDS+22*64+offset,struct.pack('<H',value) if offset==0 else bytes([value]))
        if latch:guest.u.mem_write(OBJ+0x120a,bytes([latch]))
        phases=[guest.invoke_prefix()]
        positive=offset is None and latch==0
        if positive:
            assert phases[0]['boundary']['operation']=='before_next_image_helper' and phases[0]['phase']==dict(state=1,look=0,pending=0,commands=0)
            phases.append(guest.invoke_prefix());assert phases[1]['phase']==dict(state=2,look=22,pending=1,commands=1)
        else:
            assert phases[0]['boundary']['operation']=='before_object_virtual_dispatch' and phases[0]['latch']==1 and phases[0]['phase']['commands']==0
            assert phases[0]['entry_delta'].get('mlut_controller',0)==0
        if latch:assert phases[0]['entry_delta'].get('resource_checker',0)==0
        rows.append(dict(case=label,declared_mask_resource22=mask_fixture,declared_record_mutation=None if offset is None else dict(offset=offset,value=value),declared_initial_latch=latch,
                         producer=producer,phases=phases,original_latch_writes=guest.latch_writes,commands=[list(c) for c in guest.commands]))
    guest=Guest(raw);guest.prepare();guest.u.mem_write(OBJ+0x11c3+22,b'\1');guest.u.mem_write(RECORDS+22*64+4,b'\1')
    first=guest.invoke_prefix();guest.u.mem_write(RECORDS+22*64+4,b'\0');second=guest.invoke_prefix()
    assert first['latch']==second['latch']==1 and second['entry_delta'].get('resource_checker',0)==0
    guest.original_sync_clear();third=guest.invoke_prefix()
    assert third['latch']==0 and third['entry_delta']['mlut_controller']==1 and third['boundary']['operation']=='before_next_image_helper'
    rows.append(dict(case='failure_latch_and_original_sync_clear',phases=[first,second,third],original_latch_writes=guest.latch_writes,
                     scope='Restore declared record byte, then execute original 72-byte clear fragment. After clear the mask is empty; no normal mask repopulation or complete sync lifecycle is claimed.'))
    registration=Guest(raw);registration.prepare();packet=registration.register_boundary()
    result=dict(cp_sha256=PIN,cases=rows,registration_cases=[packet],source_spans=[dict(file_offset=hex(a),bytes=z-a,sha256=hashlib.sha256(raw[a:z]).hexdigest()) for a,z in SPANS],
                scope='Original MLUT caller prologue, resource gate, 71-entry checker, original pointer getter, controller and SDK execute up to the next image helper or before virtual object dispatch. Seven cases include explicit mask/record/latch fixtures; only the first retains the empty mask from the original fresh VFX allocation with the previous STP success stub. Another original fragment clears mask+latch. One registration record is built by original instructions and stops at the original dispatcher entry without queue/callback fabrication. Original hardware/OSAL/pre/EI/queue stubs and look22 fixture inherited from prior guest remain. The next image helper, real event arrival, full scene, buffers, MAIN pixels and firmware flashability are not established. No native target, hardware or device action.')
    (HERE/'caller-gate-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(gate_cases=len(rows),registration_cases=1,normal_MAIN_unproven=True,device_actions=0)))

if __name__=='__main__':main()
