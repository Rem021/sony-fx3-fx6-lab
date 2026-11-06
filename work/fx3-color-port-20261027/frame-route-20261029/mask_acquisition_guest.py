#!/usr/bin/env python3
"""Trace original resource-mask inputs and stop at unreviewed STP source."""
import json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'scene-binding-20261029'))
from scene_context_guest import Guest as SceneGuest,image,BASE,PIN,SCENE,SPANS as SCENE_SPANS
from context_binding_guest import PRODUCER_SPANS
from caller_binding_guest import EXTRA_SPANS,SDK_SPANS,OBJ,OUT,STACK,DATA,STOP
from resource_binding_guest import Guest as AcquireGuest,SPANS as ACQUIRE_SPANS,HARDWARE_STUBS,RECORDS

class Guest(SceneGuest):
    def __init__(self,raw,original_stp):
        super().__init__(raw);self.original_stp=original_stp;self.boundary=None;self.requests=[];self.mask_writes=[];self.broker_arguments=[];self.binding=False
    def write(self,u,access,at,size,value,user):
        if OBJ+0x11c3<=at and at+size<=OBJ+0x120a:
            self.mask_writes.append(dict(offset=hex(at-OBJ-0x11c3),bytes=size,value=hex(value),pc=hex(u.reg_read(R.UC_ARM_REG_PC))))
        return super().write(u,access,at,size,value,user)
    def code(self,u,pc,size,user):
        if pc==self.stop_point:return super().code(u,pc,size,user)
        if self.binding and pc==0x3c7574:
            regs=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
            self.requests.append(dict(pc=hex(pc),context=regs[0],kind=regs[1],args=[hex(x) for x in regs],stack_words=[hex(v[0]) for v in struct.iter_unpack('<I',bytes(u.mem_read(u.reg_read(R.UC_ARM_REG_SP),28)))]))
            if regs[1]==16 and self.original_stp:return AcquireGuest.code(self,u,pc,size,user)
        if self.binding and pc==0x403e30:
            self.broker_arguments.append(dict(registers=[hex(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)],stack_words=[hex(v[0]) for v in struct.iter_unpack('<I',bytes(u.mem_read(u.reg_read(R.UC_ARM_REG_SP),28)))]))
        allowed=SCENE_SPANS+PRODUCER_SPANS+EXTRA_SPANS+SDK_SPANS+ACQUIRE_SPANS
        primitives=set(HARDWARE_STUBS)|{STOP,0x52c474,0x528248,0x5286a0,0xa4d310,0xa4d314,0x9e6684,0x9e6530,0x9e64ec,0xa4f618,0xa4fa3e,0xa4eb28,0xa1f2f2,0xa50d72}
        if self.binding and pc not in primitives and not any(a<=pc-BASE<z for a,z in allowed):
            self.boundary=dict(operation='before_unreviewed_original_function',pc=hex(pc),registers=[hex(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)],native_call=False)
            u.emu_stop();return
        return super().code(u,pc,size,user)
    def bind_bounded(self):
        u=self.u;self.binding=True;self.stop_point=BASE+0x3027c6
        for i in range(4):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        for i,value in {9:OBJ,11:0x100,5:0,8:0x77770008}.items():u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),value)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        for off,value in {0x38:OBJ+0x11c3,0x3c:OBJ+0x8e4,0x48:0,0x5c:0x100}.items():u.mem_write(STACK+0xf000+off,struct.pack('<I',value))
        u.emu_start((BASE+0x302724)|1,STOP+4,count=40000)
        if self.boundary:assert u.reg_read(R.UC_ARM_REG_PC)==int(self.boundary['pc'],16)
        else:assert u.reg_read(R.UC_ARM_REG_PC)==self.stop_point and u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
        self.binding=False;self.stop_point=None
        mask=bytes(u.mem_read(OBJ+0x11c3,71))
        return dict(original_stp_requested=self.original_stp,boundary=self.boundary,returned=self.boundary is None,return_value=u.reg_read(R.UC_ARM_REG_R0) if self.boundary is None else None,
                    mask_hex=mask.hex(),nonzero_mask_ids=[i for i,b in enumerate(mask) if b],mask_original_writes=list(self.mask_writes),
                    resource_requests=list(self.requests),broker_arguments=list(self.broker_arguments),original_allocator_events=list(self.allocations),
                    original_owner_word=hex(struct.unpack('<I',u.mem_read(OUT,4))[0]),instructions=self.instructions,
                    selected_records={str(i):bytes(u.mem_read(RECORDS+64*i,64)).hex() for i in [22,26]})

def main():
    raw=image();rows=[]
    for original in [False,True]:
        guest=Guest(raw,original);produced=guest.produce(0x40fc09,0,0,original_callsite=True)
        row=guest.bind_bounded();row.update(producer=produced,case='original_STP_boundary' if original else 'fresh_with_declared_STP_success');rows.append(row)
        if not original:
            repeated=guest.bind_bounded();repeated.update(case='repeat_without_release',producer=produced);rows.append(repeated)
    assert rows[0]['returned'] and rows[0]['return_value']==1 and rows[0]['nonzero_mask_ids']==[] and rows[0]['original_owner_word']=='0x80000001'
    result=dict(cp_sha256=PIN,cases=rows,scope='Trace original caller/selector/broker arguments and mask stores after original GetInfo/copy/vector/sync production. Baseline retains earlier explicit STP success stub; comparison removes that stub and stops before any unreviewed original function. VFX resource/hardware/OSAL boundaries inherited from earlier guest remain synthetic. No real frame, device, IPC, target-native load or pixels.')
    (HERE/'mask-acquisition-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),baseline_mask=rows[0]['nonzero_mask_ids'],repeat_return=rows[1]['return_value'],repeat_mask=rows[1]['nonzero_mask_ids'],original_stp_boundary=rows[2]['boundary'])))

if __name__=='__main__':main()
