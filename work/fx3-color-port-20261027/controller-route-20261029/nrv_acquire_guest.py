#!/usr/bin/env python3
"""Original kind3/NRV broker path up to the first unreplied handle operation."""
import hashlib,json,struct,sys
from pathlib import Path
from collections import deque
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'binding-20261028'))
from resource_binding_guest import Guest as AcquireGuest,SPANS as BROKER_SPANS,image,BASE,PIN,DATA,STACK,STOP,R
SPANS=[(0x4056f4,0x40575a),(0x44f004,0x44f084),(0x44d710,0x44d732)]
ADAPTED=[0x52c474,0x528248,0x5286a0,0xa4d310,0xa4d314,0x9e6684,0x9e6530,0x9e64ec]

class Guest(AcquireGuest):
    def __init__(self,raw):
        super().__init__(raw);self.u.mem_map(0x117a000,0x1000)
        self.boundary=None;self.entries=[];self.trace=deque(maxlen=20)
    def code(self,u,pc,size,user):
        regs=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
        self.trace.append(dict(pc=hex(pc),registers=[hex(v) for v in regs]))
        if pc in [0x4056f4,0x44f004,0x44d710]:self.entries.append(dict(pc=hex(pc),registers=[hex(v) for v in regs]))
        if pc==0x4a032c:
            self.boundary=dict(pc=hex(pc),registers=[hex(v) for v in regs],input_word=hex(struct.unpack('<I',u.mem_read(regs[2]-4,4))[0]),
                               original_lr=hex(u.reg_read(R.UC_ARM_REG_LR)),native_call=False,service_reply_supplied=False)
            u.emu_stop();return
        if any(a<=pc<z for a,z in SPANS):self.instructions+=1;return
        assert pc==STOP or any(a<=pc-BASE<z for a,z in BROKER_SPANS) or pc in ADAPTED,hex(pc)
        return super().code(u,pc,size,user)
    def execute(self,context):
        u=self.u
        for i,v in enumerate([context,3,0x100,0]):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),v)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.mem_write(STACK+0xf000,struct.pack('<7I',0,0,1,0,0,DATA+0x10d0,0))
        u.emu_start(0x3c7575,STOP+4,count=30000)
        assert self.boundary and u.reg_read(R.UC_ARM_REG_PC)==0x4a032c
        assert self.boundary['registers'][:2]==['0x2a','0x5'] and self.boundary['input_word']=='0x2'
        assert [x['pc'] for x in self.entries]==['0x4056f4','0x44f004','0x44d710']
        assert self.entries[0]['registers']==['0x0',hex({1:0,5:4,7:6}[context]),'0x0','0x4']
        assert self.entries[1]['registers']==['0x117adf0','0x4af','0x1','0x0']
        assert not self.events # Stops before even the inherited hardware adapters.
        return dict(declared_context=context,declared_kind=3,declared_broker_arguments=[context,3,'0x100',0],
                    declared_stack_arguments=[0,0,1,0,0,hex(DATA+0x10d0),0],
                    original_entries=self.entries,unreplied_boundary=self.boundary,final_trace=list(self.trace),instructions=self.instructions,
                    normal_controller_handle_produced=False,scope='Declared free broker and acquisition arguments. Original graph/broker selects NRV_0 id4, then original allocation helper requests the first of two descriptors using key0x4af. No allocation/handle reply, normal controller, successful bundle acquisition or hardware result is supplied.')

def main():
    raw=image();rows=[Guest(raw).execute(c) for c in [1,5,7]]
    out=dict(cp_sha256=PIN,cases=rows,source_spans=[dict(va=hex(a),bytes=z-a,sha256=hashlib.sha256(raw[a-BASE:z-BASE]).hexdigest()) for a,z in SPANS],
             scope='Three original NRV broker prefixes in RAM only, all stop at the same unreplied common handle operation. Does not establish normal runtime context selection, resource reply, controller construction, pixels, full donor chain or firmware admission.')
    (HERE/'nrv-acquire-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),first_resource_id=4,allocation_key='0x4af',native_calls=0,device_actions=0)))

if __name__=='__main__':main()
