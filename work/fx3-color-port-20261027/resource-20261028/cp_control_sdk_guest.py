#!/usr/bin/env python3
"""Original CP controller plus previously bounded SDK, in one CPU guest."""
import json,struct
from unicorn import arm_const as R
from vfx_resource_guest import Guest,HERE,image,BASE,PIN,DATA

STATE,LOOK,PENDING=0x13d847c,0x13d8480,0x147d2ce
LOOK_PARAM=DATA+0x200


class ControlGuest(Guest):
    def __init__(self,b):
        super().__init__(b)
        for a,n in [(0x13d8000,0x1000),(0x1435000,0x1000),(0x147d000,0x1000)]:self.u.mem_map(a,n)
        raw=bytearray(0x80);struct.pack_into('<I',raw,0,22);struct.pack_into('<I',raw,8,11)
        struct.pack_into('<II',raw,0x10,100,800);self.u.mem_write(LOOK_PARAM,bytes(raw))
        self.pre_status=0;self.pre_owner=0x42;self.ei_status=0

    def code(self,u,pc,size,unused):
        if pc==0xa4f618:
            p=u.reg_read(R.UC_ARM_REG_R0);assert struct.unpack('<I',u.mem_read(p,4))[0]==0x42
            self.events.append(['declared_pre_stage',self.pre_status,self.pre_owner])
            if self.pre_status==0:u.mem_write(0x13eb088,struct.pack('<I',self.pre_owner))
            self.ret(self.pre_status);return
        if pc==0xa4fa3e:
            assert [u.reg_read(R.UC_ARM_REG_R0),u.reg_read(R.UC_ARM_REG_R1)]==[100,800]
            self.events.append(['declared_ei_stage',self.ei_status]);self.ret(self.ei_status);return
        if pc==0x9e6684:
            self.events.append(['CP_diagnostic']);self.ret(0);return
        off=pc-BASE
        if 0x3263fc<=off<0x326600 or 0x326680<=off<0x3266d0 or 0x8d1a7e<=off<0x8d1ad6:
            self.instructions+=1;return
        super().code(u,pc,size,unused)

    def write(self,u,access,address,size,value,unused):
        if (0x13d847c<=address and address+size<=0x13d8494 or address==PENDING and size==1):return
        super().write(u,access,address,size,value,unused)

    def snapshot(self):
        return dict(state=struct.unpack('<I',self.u.mem_read(STATE,4))[0],
                    look=struct.unpack('<I',self.u.mem_read(LOOK,4))[0],pending=self.u.mem_read(PENDING,1)[0],
                    queue_commands=len(self.commands))

    def step(self):self.call(0x3263fc,[0x42,LOOK_PARAM]);return self.snapshot()
    def ready(self):return self.call(0x8d1a7e,[22,11,LOOK_PARAM+0x18])


def main():
    b=image();rows=[];total=0
    for mask in [1,2,4,8,15,3,12]:
        g=ControlGuest(b);g.owners(mask)
        assert g.ready()==0
        pre=g.step();assert pre==dict(state=1,look=0,pending=0,queue_commands=0)
        submit=g.step();assert submit==dict(state=2,look=22,pending=1,queue_commands=1) and g.ready()==0
        repeat=g.step();assert repeat==submit
        g.call(0x326680,[0]);done=g.snapshot()
        assert done==dict(state=2,look=22,pending=0,queue_commands=1) and g.ready()==1
        g.step();assert len(g.commands)==1
        rows.append(dict(mask=mask,phases={'pre':pre,'submit':submit,'busy_repeat':repeat,'declared_callback':done},
                         command=list(g.commands[0]),events=g.events));total+=g.instructions
    failures=[]
    for label,mask,opts in [('no_owner',0,{}),('busy',1,{'busy_return':0}),('queue',1,{'queue_return':7}),
                            ('pre_owner_mismatch',1,{'pre_owner':0x99}),('pre_error',1,{'pre_status':5})]:
        g=ControlGuest(b);g.owners(mask)
        for k,v in opts.items():setattr(g,k,v)
        g.step();state=g.step()
        assert state['state']==0 and state['look']==0 and state['pending']==0
        failures.append(dict(label=label,state=state,events=g.events,commands=[list(x) for x in g.commands]));total+=g.instructions
    g=ControlGuest(b);g.owners(1);g.step();g.step();g.call(0x326680,[9]);error=g.snapshot()
    assert error['state']==0 and error['look']==0 and error['pending']==0 and g.ready()==0
    total+=g.instructions
    result=dict(status='PASS_ORIGINAL_CP_CONTROLLER_THROUGH_ORIGINAL_SDK',cp_sha256=PIN,
                successful_resource_groups=rows,failures=failures,callback_error=error,original_instructions=total,
                scope='Controller, owner resolver, SDK admission, core command construction and callback all execute in one guest. Pre preparation/EI, scheduler, busy status, queue outcome and manual callback arrival remain declared. Actual queue transport and DMA are separately bounded; no camera state or footage.')
    (HERE/'cp-control-sdk-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'groups',len(rows),'error paths',len(failures)+1,'original instructions',total)


if __name__=='__main__':main()
