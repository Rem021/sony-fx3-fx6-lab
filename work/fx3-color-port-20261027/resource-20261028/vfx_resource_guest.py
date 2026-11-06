#!/usr/bin/env python3
"""Original CP owner resolver, SDK look setter, and MLUT queue admission."""
from pathlib import Path
import sys,json,struct,itertools
from hashlib import sha256
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm_const as R

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'route-20261028'))
from cp_look_route import image,BASE,PIN

STACK,DATA,STOP=0x50000000,0x51000000,0x60000000
OWNERS=0x13eaff8
LOCK=0x528248;UNLOCK=0x5286a0;CONTEXT=0x52c474
CALLBACK=(BASE+0x326680)|1
SPANS=[(0x380094,0x3801e4),(0x3812c8,0x381304),
       (0x9478ba,0x947a3e),(0x947824,0x947870),
       (0x9483f6,0x948406),(0x948d26,0x948d4e),
       (0x90cd86,0x90ce52),(0x90e1d0,0x90e1dc),
       (0x450af4,0x450c30)]


class Guest:
    def __init__(self,b):
        self.u=u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
        u.mem_map(BASE,(len(b)+4095)&~4095);u.mem_write(BASE,b)
        for a,n in [(STACK,0x10000),(DATA,0x3000),(STOP,0x1000),(0x13ea000,0x2000)]:u.mem_map(a,n)
        self.events=[];self.commands=[];self.instructions=0
        self.busy_return=1;self.queue_return=0;self.lock_return=0;self.unlock_return=0
        u.hook_add(UC_HOOK_CODE,self.code);u.hook_add(UC_HOOK_MEM_WRITE,self.write)
        # Log mode fixture suppresses optional diagnostic calls; original getter executes.
        u.mem_write(0xf42e18,struct.pack('<I',1))

    def ret(self,value):
        u=self.u;u.reg_write(R.UC_ARM_REG_R0,value&0xffffffff)
        u.reg_write(R.UC_ARM_REG_PC,u.reg_read(R.UC_ARM_REG_LR))

    def code(self,u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        if pc==CONTEXT:self.events.append(['context']);self.ret(0);return
        if pc in [LOCK,UNLOCK]:
            assert u.reg_read(R.UC_ARM_REG_R0)==0x2e
            self.events.append(['lock' if pc==LOCK else 'unlock'])
            self.ret(self.lock_return if pc==LOCK else self.unlock_return);return
        if pc in [0xa4d310,0xa4d314]:
            self.events.append(['diagnostic',u.reg_read(R.UC_ARM_REG_R0),u.reg_read(R.UC_ARM_REG_R2)])
            self.ret(0);return
        if pc==0xa4eb28:
            self.events.append(['declared_busy_probe',u.reg_read(R.UC_ARM_REG_R0)])
            self.ret(self.busy_return);return
        if pc==0xa1f2f2:
            ptr=u.reg_read(R.UC_ARM_REG_R0);raw=bytes(u.mem_read(ptr,56))
            self.commands.append(struct.unpack('<14I',raw))
            self.ret(self.queue_return);return
        if pc==0xa50d72:
            self.events.append(['declared_post_submit_resource_operation',u.reg_read(R.UC_ARM_REG_R0)])
            self.ret(0);return
        off=pc-BASE
        assert any(a<=off<z for a,z in SPANS),hex(pc)
        self.instructions+=1

    def write(self,u,access,address,size,value,unused):
        assert (STACK<=address and address+size<=STACK+0x10000 or
                DATA+0x100<=address and address+size<=DATA+0x108 or
                address==0x13eb088 and size==4),hex(address)

    def call(self,entry,args):
        u=self.u
        for i in range(4):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),args[i] if i<len(args) else 0)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.emu_start((BASE+entry)|1,STOP+4,count=3000)
        assert u.reg_read(R.UC_ARM_REG_PC)==STOP and u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        return u.reg_read(R.UC_ARM_REG_R0)

    def owners(self,mask,namespace=0):
        raw=b''.join(struct.pack('<II',0x42 if mask>>i&1 else 0x99,namespace+1) for i in range(4))
        self.u.mem_write(OWNERS,raw)

    def resolve(self,mask,namespace=0):
        self.owners(mask,namespace);u=self.u
        u.mem_write(DATA+0x100,struct.pack('<I',0xa7a7a7a7))
        status=self.call(0x380094,[namespace,0x42,DATA+0x100])
        out=struct.unpack('<I',u.mem_read(DATA+0x100,4))[0]
        return dict(mask=mask,namespace=namespace,status=status,internal_group=out)

    def set(self,mask,namespace=0,look=22,pre_owner=0x42,busy=1,queue=0,lock=0,unlock=0):
        self.owners(mask,namespace);u=self.u
        self.busy_return=busy;self.queue_return=queue;self.lock_return=lock;self.unlock_return=unlock
        u.mem_write(DATA,struct.pack('<I',0x42));u.mem_write(0x13eb088,struct.pack('<I',pre_owner))
        before=len(self.events);c=len(self.commands)
        status=self.call(0x9478ba,[look,CALLBACK,DATA])
        return dict(mask=mask,namespace=namespace,look=look,declared_busy_return=busy,
                    declared_queue_return=queue,declared_pre_owner=pre_owner,
                    declared_lock_return=lock,declared_unlock_return=unlock,status=status,
                    commands=[list(x) for x in self.commands[c:]],events=self.events[before:],
                    pre_owner_after=struct.unpack('<I',u.mem_read(0x13eb088,4))[0])


def main():
    b=image();g=Guest(b)
    expected={1:0,2:1,4:2,8:3,15:4,3:5,12:6}
    # The dictionary is checked against original execution and captured range endpoints.
    resolutions=[g.resolve(mask,ns) for ns,mask in itertools.product(range(2),range(16))]
    recovered={x['mask']:x['internal_group'] for x in resolutions if x['namespace']==0 and x['status']==0}
    assert recovered==expected,(recovered,expected)
    assert all(x['status']==(0 if x['mask'] in expected else 5) for x in resolutions)
    ranges=[]
    for group in range(8):
        g.u.mem_write(DATA+0x100,b'\xa7'*8)
        status=g.call(0x3812c8,[group,DATA+0x100,DATA+0x104])
        pair=[g.u.mem_read(DATA+0x100,1)[0],g.u.mem_read(DATA+0x104,1)[0]]
        ranges.append(dict(group=group,status=status,resource_range_inclusive=pair))
    assert [r['resource_range_inclusive'] for r in ranges[:7]]==[[0,0],[1,1],[2,2],[3,3],[0,3],[0,1],[2,3]]
    successful=[]
    for ns,mask in itertools.product(range(2),expected):
        r=g.set(mask,ns);assert r['status']==0 and len(r['commands'])==1
        command=r['commands'][0]
        assert command[:7]==[0,22,expected[mask],CALLBACK,0x2ae085a,0,0] and command[7:]==[0]*7
        assert r['pre_owner_after']==0
        successful.append(r)
    failures=[]
    for mask in sorted(set(range(16))-set(expected)):
        r=g.set(mask);assert r['status']==5 and not r['commands'];failures.append(r)
    for kwargs,expected_status in [({'pre_owner':0x99},8),({'busy':0},8),({'look':0},1),
                                   ({'look':30},1),({'look':255},1),({'queue':7},1),
                                   ({'lock':9},3),({'unlock':9},2)]:
        r=g.set(1,**kwargs);assert r['status']==expected_status,(kwargs,r)
        if 'queue' not in kwargs:assert not r['commands']
        failures.append(r)
    source=[dict(file_start=hex(a),file_end_exclusive=hex(z),sha256=sha256(b[a:z]).hexdigest()) for a,z in SPANS]
    result=dict(status='PASS_ORIGINAL_RESOURCE_RESOLVER_SDK_AND_MLUT_ADMISSION',cp_sha256=PIN,
                owner_resolutions=resolutions,group_ranges=ranges,successful_sets=successful,failure_probes=failures,
                original_instructions=g.instructions,source_spans=source,
                fixtures={'owner_rows':'Four declared (acquire_id, namespace_tag) pairs at VA 0x13eaff8.',
                          'OSAL':'Context query and lock/unlock returns are declared; actual scheduler/locks are not executed.',
                          'busy':'Underlying a4eb28 status is declared. Its original boolean wrapper and group iteration execute.',
                          'pre':'Pre stage ownership at VA 0x13eb088 is declared, not established by the original hardware pre function.',
                          'queue':'Original core command construction executes; stopped at a1f2f2 queue entry and returns a declared outcome.',
                          'post':'Post-submit per-resource operation a50d72 is intercepted as declared no-op.'},
                scope='No actual acquire owner, camera mode, MAIN/monitor assignment, OSAL queue, DMA, register programming or pixels. Internal groups 0..6 are resource groups and must not be mislabeled as independent physical MLUT engines.')
    (HERE/'vfx-resource-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'owner cases',len(resolutions),'successful sets',len(successful),'failure probes',len(failures))


if __name__=='__main__':main()
