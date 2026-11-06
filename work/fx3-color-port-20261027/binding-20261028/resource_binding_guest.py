#!/usr/bin/env python3
"""Original resource graph selector/broker/allocation, declared hardware edges."""
from pathlib import Path
from hashlib import sha256
import sys,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_INVALID
from unicorn import arm_const as R

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'route-20261028'))
from cp_look_route import image,BASE,PIN

STACK,DATA,STOP=0x50000000,0x51000000,0x60000000
OBJ=DATA
OUT=OBJ+0x10d0
OWNERS=0x13eaff8
RECORDS=0x13c38f8
SPANS=[(0x2bf294,0x2bf322),(0x8ad4f4,0x8ad58a),(0x2bf574,0x2bf638),
       (0x2fbe30,0x2fce16),(0x8c724c,0x8c72a4),(0x3259bc,0x325a8c),
       (0x37ff6c,0x380094),(0x37fa74,0x37fd14),(0x380094,0x3801e4)]
HARDWARE_STUBS={0x48919c:'configure_resource_sync',0x489468:'configure_resource_parameters',
                0xa500f2:'initialize_resource',0x487dec:'resource_event_query',
                0x487d14:'reset_resource_status',0xa4f210:'set_AIC_parameters',
                0x48904c:'set_transfer_sync',0x9ff67a:'dependent_event_query',
                0xa4b500:'post_acquire_housekeeping'}


class Guest:
    def __init__(self,b):
        self.u=u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
        u.mem_map(BASE,(len(b)+4095)&~4095);u.mem_write(BASE,b)
        for a,n in [(STACK,0x10000),(DATA,0x10000),(STOP,0x1000),
                    (0x13c3000,0x2000),(0x13ea000,0x2000),(0x1435000,0x1000)]:u.mem_map(a,n)
        self.events=[];self.logs=[];self.instructions=0;self.allocations=[]
        u.hook_add(UC_HOOK_CODE,self.code);u.hook_add(UC_HOOK_MEM_WRITE,self.write)
        def invalid(u,access,address,size,value,unused):
            raise AssertionError(('unmapped boundary',hex(u.reg_read(R.UC_ARM_REG_PC)),hex(address),size))
        u.hook_add(UC_HOOK_MEM_INVALID,invalid)

    def ret(self,v):
        self.u.reg_write(R.UC_ARM_REG_R0,v&0xffffffff)
        self.u.reg_write(R.UC_ARM_REG_PC,self.u.reg_read(R.UC_ARM_REG_LR))

    def code(self,u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        if pc==0x52c474:self.events.append(['declared_context_query',0]);self.ret(0);return
        if pc in [0x528248,0x5286a0]:
            self.events.append(['declared_lock_primitive',hex(pc),u.reg_read(R.UC_ARM_REG_R0),0]);self.ret(0);return
        if pc in [0xa4d310,0xa4d314,0x9e6684,0x9e6530,0x9e64ec]:
            self.logs.append(hex(pc));self.ret(0);return
        if pc in HARDWARE_STUBS:
            self.events.append([HARDWARE_STUBS[pc],[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)],0])
            self.ret(0);return
        if pc==0x487be0:
            self.allocations.append(dict(namespace=u.reg_read(R.UC_ARM_REG_R0),output=hex(u.reg_read(R.UC_ARM_REG_R1)),
                                         driver_group=u.reg_read(R.UC_ARM_REG_R2),flag=u.reg_read(R.UC_ARM_REG_R3)))
        off=pc-BASE
        assert any(a<=off<z for a,z in SPANS),hex(pc)
        self.instructions+=1

    def write(self,u,access,address,size,value,unused):
        assert (STACK<=address and address+size<=STACK+0x10000 or
                DATA<=address and address+size<=DATA+0x10000 or
                RECORDS<=address and address+size<=RECORDS+71*64 or
                OWNERS<=address and address+size<=OWNERS+32),hex(address)

    def call(self,va,args,extra=()):
        u=self.u
        for i in range(4):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),args[i] if i<len(args) else 0)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        if extra:u.mem_write(STACK+0xf000,struct.pack('<'+'I'*len(extra),*extra))
        u.emu_start(va|1,STOP+4,count=30000)
        assert u.reg_read(R.UC_ARM_REG_PC)==STOP,hex(u.reg_read(R.UC_ARM_REG_PC))
        assert u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        return u.reg_read(R.UC_ARM_REG_R0)

    def select(self,context,kind):
        self.u.mem_write(DATA+0x200,struct.pack('<4I',*([0xfe]*4)))
        status=self.call(0x9b54f4,[context,kind,DATA+0x200])
        return dict(context=context,kind=kind,status=status,
                    resource_ids=list(struct.unpack('<4I',self.u.mem_read(DATA+0x200,16))))

    def acquire(self,context):
        self.u.mem_write(OUT,b'\0'*4)
        # A declared free broker state, not a recovered camera RAM snapshot.
        self.u.mem_write(RECORDS,b'\0'*(71*64));self.u.mem_write(OWNERS,b'\0'*32)
        begin=len(self.events);a=len(self.allocations)
        status=self.call(0x3c7574,[context,15,0x100,0],[0,0,1,0,0,OUT,0])
        owner=struct.unpack('<I',self.u.mem_read(OUT,4))[0]
        rows=list(struct.iter_unpack('<II',self.u.mem_read(OWNERS,32)))
        self.u.mem_write(DATA+0x300,struct.pack('<I',0xa7a7a7a7))
        resolved=self.call(0x488094,[0,owner,DATA+0x300])
        group=struct.unpack('<I',self.u.mem_read(DATA+0x300,4))[0]
        return dict(context=context,status=status,owner=hex(owner),owner_rows=rows,
                    resolver_status=resolved,resolved_driver_group=group,
                    allocator_calls=self.allocations[a:],events=self.events[begin:])


def names(b):
    result=[]
    for i in range(71):
        key,p=struct.unpack_from('<II',b,0xcedc44-BASE+i*8);assert key==i
        result.append(b[p-BASE:b.index(0,p-BASE)].decode())
    return result


def main():
    b=image();g=Guest(b);labels=names(b)
    selections=[g.select(c,k) for c in range(1,11) for k in range(25)]
    expected={1:[22],2:[29],3:[36],4:[43],5:[22,29],6:[36,43],7:[22,29,36,43],8:[],9:[],10:[]}
    for x in selections:
        if x['kind']==15:assert [i for i in x['resource_ids'] if i!=0xfe]==expected[x['context']]
    acquires=[g.acquire(c) for c in range(1,8)]
    expected_groups=[0,1,2,3,5,6,4]
    for x,group in zip(acquires,expected_groups):
        assert x['status']==1 and x['resolver_status']==0 and x['resolved_driver_group']==group,x
        assert x['owner']==hex(0x80000001 | group<<16)
        assert x['allocator_calls'][0]['driver_group']==group
    result=dict(status='PASS_ORIGINAL_GRAPH_TO_BROKER_TO_OWNER_TO_RESOLVER',cp_sha256=PIN,
                resource_names=labels,selector_cases=selections,acquisition_cases=acquires,original_instructions=g.instructions,
                source_spans=[dict(file_start=hex(a),end_exclusive=hex(z),sha256=sha256(b[a:z]).hexdigest()) for a,z in SPANS],
                fixtures={'broker_records':'71 free zeroed records, including declared zero dependencies; not a live snapshot.',
                          'window_arguments':[0,0,1,0,0,'object+0x10d0',0],
                          'hardware_and_OSAL':'Explicit success stubs listed in hardware_boundaries. Original resource owner allocation and owner-table writes execute.'},
                hardware_boundaries={hex(k):v for k,v in HARDWARE_STUBS.items()},
                scope='Original file-backed graph resource maps, original selector/broker, original acquire wrapper and owner allocator. Does not prove current movie/monitor scene selection, resource initialization on hardware, scheduling or image output.')
    (HERE/'resource-binding-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'selector cases',len(selections),'acquisitions',len(acquires),'instructions',g.instructions)


if __name__=='__main__':main()
