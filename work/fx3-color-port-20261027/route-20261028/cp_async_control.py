#!/usr/bin/env python3
"""Original CP look-state/callback code with explicit SDK outcome fixtures."""
from hashlib import sha256
import json
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm_const as R
from cp_look_route import image, BASE, HERE

STACK, DATA, STOP=0x50000000,0x51000000,0x60000000
STATE, LOOK, PENDING=0x13d847c,0x13d8480,0x147d2ce
SDK={0xa4f618:'pre',0xa4f8ba:'set_builtin',0xa4fa3e:'set_ei'}


class Guest:
    def __init__(self,b,outcomes=None):
        self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u=self.u
        u.mem_map(BASE,(len(b)+4095)&~4095);u.mem_write(BASE,b)
        for a,n in [(0x13d8000,0x1000),(0x1435000,0x1000),(0x147d000,0x1000),(STACK,0x10000),(DATA,0x1000),(STOP,0x1000)]:u.mem_map(a,n)
        self.calls=[];self.logs=[];self.instructions=0;self.outcomes=outcomes or {}
        u.hook_add(UC_HOOK_CODE,self.code);u.hook_add(UC_HOOK_MEM_WRITE,self.write)
        # Declared resource and parameters; no real current-camera instance.
        p=bytearray(0x80)
        struct.pack_into('<I',p,0,22);struct.pack_into('<I',p,8,11)
        struct.pack_into('<II',p,0x10,100,800)
        u.mem_write(DATA,bytes(p))

    def code(self,u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        if pc in SDK:
            name=SDK[pc];args=[u.reg_read(r) for r in [R.UC_ARM_REG_R0,R.UC_ARM_REG_R1,R.UC_ARM_REG_R2]]
            if name=='pre':assert struct.unpack('<I',u.mem_read(args[0],4))[0]==0x42
            if name=='set_builtin':
                assert args[0]==22 and args[1]==BASE+0x326681
                assert struct.unpack('<I',u.mem_read(args[2],4))[0]==0x42
            value=self.outcomes.get(name,0)
            self.calls.append(dict(name=name,args=[hex(x) for x in args],declared_return=value))
            u.reg_write(R.UC_ARM_REG_R0,value&0xffffffff)
            u.reg_write(R.UC_ARM_REG_PC,u.reg_read(R.UC_ARM_REG_LR));return
        if pc==0x9e6684:
            self.logs.append(hex(u.reg_read(R.UC_ARM_REG_R0)))
            u.reg_write(R.UC_ARM_REG_PC,u.reg_read(R.UC_ARM_REG_LR));return
        off=pc-BASE
        assert 0x3263fc<=off<0x326600 or 0x326680<=off<0x3266d0 or 0x8d1a7e<=off<0x8d1ad6,hex(pc)
        self.instructions+=1

    def write(self,u,access,address,size,value,unused):
        assert any(a<=address and address+size<=a+n for a,n in [(0x13d8000,0x1000),(0x147d000,0x1000),(STACK,0x10000)]),hex(address)

    def call(self,entry,args):
        u=self.u
        for i,v in enumerate(args):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),v)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.emu_start((BASE+entry)|1,STOP+4,count=5000)
        assert u.reg_read(R.UC_ARM_REG_PC)==STOP and u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        return u.reg_read(R.UC_ARM_REG_R0)

    def snapshot(self):
        u=self.u
        return dict(state=struct.unpack('<I',u.mem_read(STATE,4))[0],
                    look=struct.unpack('<I',u.mem_read(LOOK,4))[0],pending=u.mem_read(PENDING,1)[0],
                    sdk_call_count=len(self.calls))

    def set(self):
        self.call(0x3263fc,[0x42,DATA]);return self.snapshot()

    def ready(self):return self.call(0x8d1a7e,[22,11,DATA+0x18])


def main():
    b=image();g=Guest(b);phases=[]
    assert g.ready()==0
    phases.append(dict(step='pre',**g.set()));assert g.snapshot()['state']==1 and g.snapshot()['pending']==0
    phases.append(dict(step='submit fixture',**g.set()));assert g.snapshot()['state']==2 and g.snapshot()['pending']==1
    assert g.ready()==0
    before=len(g.calls);phases.append(dict(step='busy repeat',**g.set()));assert len(g.calls)==before
    g.call(0x326680,[0]);phases.append(dict(step='successful callback',**g.snapshot()));assert g.ready()==1
    before=len(g.calls);g.set();assert len(g.calls)==before
    pre_error=Guest(b,{'pre':5});pre_error.set();assert pre_error.snapshot()['state']==0 and pre_error.ready()==0
    set_error=Guest(b,{'set_builtin':7});set_error.set();set_error.set()
    assert set_error.snapshot()['state']==0 and set_error.snapshot()['pending']==0 and set_error.snapshot()['look']==0
    cb_error=Guest(b);cb_error.set();cb_error.set();cb_error.call(0x326680,[9])
    assert cb_error.snapshot()['state']==0 and cb_error.snapshot()['pending']==0 and cb_error.snapshot()['look']==0 and cb_error.ready()==0
    result=dict(status='PASS_ORIGINAL_CP_STATE_AND_CALLBACK_PATHS',phases=phases,SDK_fixtures=g.calls,
                failures={'pre':pre_error.snapshot(),'set':set_error.snapshot(),'callback':cb_error.snapshot()},
                original_instructions=sum(x.instructions for x in [g,pre_error,set_error,cb_error]),
                pinned_function_sha256=sha256(b[0x3263fc:0x326600]+b[0x326680:0x3266d0]+b[0x8d1a7e:0x8d1ad6]).hexdigest(),
                scope='The original CP control functions and callback execute in a guest; SDK results are declared. Hardware submission and callback causality are not proved. No real frame or routing acceptance.')
    (HERE/'cp-async-control-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
