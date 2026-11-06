#!/usr/bin/env python3
"""Original caller output slot -> allocator -> original LUT caller/SDK."""
import sys,json,struct
from unicorn import arm_const as R
from resource_binding_guest import Guest as AcquireGuest,HERE,image,BASE,PIN,STACK,DATA,STOP,OBJ,OUT,OWNERS,RECORDS
sys.path.insert(0,str(HERE.parent/'resource-20261028'))
from vfx_resource_guest import Guest as SDKGuest,SPANS as SDK_SPANS

STATE,LOOK,PENDING=0x13d847c,0x13d8480,0x147d2ce
EXTRA_SPANS=[(0x302724,0x3027c6),(0x8d1308,0x8d1538),(0x8ad662,0x8ad6c4),
             (0x8c7336,0x8c735c),(0x8cb474,0x8cb484),(0x3263fc,0x326600),
             (0x326680,0x3266d0),(0x8d1a7e,0x8d1ad6)]


class Guest(AcquireGuest):
    def __init__(self,b):
        super().__init__(b)
        for a,n in [(0x13d8000,0x1000),(0x147d000,0x1000)]:self.u.mem_map(a,n)
        self.stop_point=None;self.commands=[]
        self.busy_return=1;self.queue_return=0;self.lock_return=0;self.unlock_return=0
        self.u.mem_write(0xf42e18,struct.pack('<I',1))
        self.other_bundle_requests=[];self.pre_calls=[]

    def code(self,u,pc,size,unused):
        if pc==self.stop_point:u.emu_stop();return
        if pc==0x3c7574 and u.reg_read(R.UC_ARM_REG_R1)!=15:
            kind=u.reg_read(R.UC_ARM_REG_R1);assert kind==16,kind
            self.other_bundle_requests.append(dict(context=u.reg_read(R.UC_ARM_REG_R0),kind=kind,declared_return=1))
            self.ret(1);return
        if pc==0xa4f618:
            p=u.reg_read(R.UC_ARM_REG_R0);owner=struct.unpack('<I',u.mem_read(p,4))[0]
            assert owner==struct.unpack('<I',u.mem_read(OUT,4))[0]
            self.pre_calls.append(owner);u.mem_write(0x13eb088,struct.pack('<I',owner));self.ret(0);return
        if pc==0xa4fa3e:
            assert [u.reg_read(R.UC_ARM_REG_R0),u.reg_read(R.UC_ARM_REG_R1)]==[100,800]
            self.events.append(['declared_EI',0]);self.ret(0);return
        off=pc-BASE
        if any(a<=off<z for a,z in EXTRA_SPANS):self.instructions+=1;return
        if (any(a<=off<z for a,z in SDK_SPANS) and not 0x380094<=off<0x3801e4
                or pc in [0xa4eb28,0xa1f2f2,0xa50d72]):
            SDKGuest.code(self,u,pc,size,unused);return
        super().code(u,pc,size,unused)

    def write(self,u,access,address,size,value,unused):
        if (0x13d847c<=address and address+size<=0x13d8494
                or address==PENDING and size==1 or address==0x13eb088 and size==4):return
        super().write(u,access,address,size,value,unused)

    def fragment(self,start,end,registers,stack_fields=None):
        u=self.u;self.stop_point=BASE+end
        for i in range(4):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        for i,v in registers.items():u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),v)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.mem_write(STACK+0xc000,b'\xa7'*0x1000)
        if stack_fields:
            for off,v in stack_fields.items():u.mem_write(STACK+0xf000+off,struct.pack('<I',v))
        u.emu_start((BASE+start)|1,STOP+4,count=40000)
        assert u.reg_read(R.UC_ARM_REG_PC)==BASE+end and u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
        assert bytes(u.mem_read(STACK+0xc000,0x1000))==b'\xa7'*0x1000
        self.stop_point=None

    def bind(self,context,raw_flag):
        u=self.u;u.mem_write(OBJ,b'\0'*0x3000)
        u.mem_write(RECORDS,b'\0'*(71*64));u.mem_write(OWNERS,b'\0'*32)
        u.mem_write(OBJ+0x1214,struct.pack('<I',context))
        return self.bind_current_object(raw_flag)

    def bind_current_object(self,raw_flag):
        u=self.u
        self.fragment(0x302724,0x3027c6,{9:OBJ,11:0x100,5:0,8:0x77770008},
                      {0x38:OBJ+0x11c3,0x3c:OBJ+0x8e4,0x48:raw_flag,0x5c:0x100})
        assert u.reg_read(R.UC_ARM_REG_R0)==1
        owner=struct.unpack('<I',u.mem_read(OUT,4))[0]
        assert owner!=0
        return owner

    def snapshot(self):
        return dict(state=struct.unpack('<I',self.u.mem_read(STATE,4))[0],
                    look=struct.unpack('<I',self.u.mem_read(LOOK,4))[0],
                    pending=self.u.mem_read(PENDING,1)[0],commands=len(self.commands))

    def color_step(self):
        self.fragment(0x8cb474,0x8cb484,{4:OBJ})
        return self.snapshot()


def main():
    b=image();cases=[];total=0
    for context in range(1,8):
        for raw_flag in [0,1]:
            g=Guest(b);owner=g.bind(context,raw_flag)
            group=[0,1,2,3,5,6,4][context-1]
            assert owner==0x80000001 | group<<16
            # Original call site reads both acquire ID and look-parameter pointer from the same object.
            param=bytearray(0x50);struct.pack_into('<I',param,0,22);struct.pack_into('<I',param,8,11)
            struct.pack_into('<II',param,0x10,100,800);g.u.mem_write(OBJ+0x10d8,bytes(param))
            pre=g.color_step();assert pre==dict(state=1,look=0,pending=0,commands=0)
            submit=g.color_step();assert submit==dict(state=2,look=22,pending=1,commands=1)
            assert g.commands[0][1:3]==(22,group)
            busy=g.color_step();assert busy==submit
            g.call(BASE+0x326680,[0]);done=g.snapshot()
            assert done==dict(state=2,look=22,pending=0,commands=1)
            assert g.call(BASE+0x8d1a7e,[22,11,OBJ+0x10f0])==1
            assert len(g.other_bundle_requests)==1 and g.other_bundle_requests[0]['kind']==16
            cases.append(dict(context=context,caller_flag_raw=raw_flag,computed_owner=hex(owner),
                              driver_group=group,owner_allocator=g.allocations,other_bundle_boundary=g.other_bundle_requests,
                              phases={'pre':pre,'submit':submit,'busy_repeat':busy,'manual_success_callback':done},
                              command=list(g.commands[0])))
            total+=g.instructions
    result=dict(status='PASS_ORIGINAL_CALLER_SLOT_ALLOCATION_TO_ORIGINAL_COLOR_SDK',cp_sha256=PIN,
                cases=cases,original_instructions=total,
                producer={'fragment':'0x302724..0x3027c6','output_slot':'object+0x10d0','helper':'0x8d1308',
                          'wrapper':'0x2bf574','broker':'0x2fbe30','allocator':'0x37fbe0'},
                consumer={'fragment':'0x8cb474..0x8cb484','parameter_slot':'object+0x10d8','controller':'0x3263fc'},
                scope='Producer and consumer original caller fragments share one declared object. Original graph selector, broker, acquire wrapper, owner allocator, CP controller and SDK execute. Other bundle kind 16, hardware resource setup, locks, pre/EI, queue outcome and callback arrival are declared. Context selector inputs and other caller live-ins are fixtures, not proof of the currently running movie/monitor scene.')
    (HERE/'caller-binding-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'cases',len(cases),'original instructions',total)


if __name__=='__main__':main()
