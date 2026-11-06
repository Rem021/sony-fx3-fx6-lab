#!/usr/bin/env python3
"""Original UIPC dynamic-ID allocator, RAM metadata pool and NRV prefix."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'controller-route-20261029'))
from nrv_acquire_guest import Guest as NRVGuest,image,BASE,PIN,DATA,STACK,STOP
META=0x53000000
POOL=0x100be00
INDEX=0x100be40
BANK=0xee55c0
BITMAP=0x1921a80
COUNTERS=0x147f940
THUMB=[(0x4a032c,0x4a0772),(0xa87084,0xa8710e),(0xa87206,0xa874e2),
       (0x49eaf8,0x49eb56),(0x49ebfc,0x49ec12),(0x57b7be,0x57b802),(0x44f9c4,0x44fa38),
       (0x44d710,0x44d768)]
ARM=[(0x52c474,0x52c488),(0x52c4a8,0x52c4b4),(0x558af4,0x558c30)]

def words(u,at,n):return list(struct.unpack('<'+'I'*n,u.mem_read(at,4*n)))

class Guest(NRVGuest):
    def __init__(self,raw,adapted=True):
        super().__init__(raw);self.adapted=adapted
        self.u.mem_map(META,0x10000);self.u.mem_map(0x1921000,0x2000);self.u.mem_map(0x147f000,0x1000)
        self.u.reg_write(R.UC_ARM_REG_CPSR,self.u.reg_read(R.UC_ARM_REG_CPSR)|0x80)
        self.adapter_calls=[];self.dynamic_events=[];self.metadata_writes=[];self.pool_initialization=None
        self.ram_metadata_results=[]

    def write(self,u,access,at,size,value,user):
        pc=u.reg_read(R.UC_ARM_REG_PC)
        regions=[(META,META+0x10000),(POOL,POOL+0x20),(INDEX,INDEX+0x210),(BITMAP,BITMAP+0x200),(COUNTERS,COUNTERS+0x14)]
        if any(a<=at and at+size<=z for a,z in regions) or at==BANK:
            assert any(a<=pc<z for a,z in THUMB) or 0x558af4<=pc<0x558c30,hex(pc)
            self.metadata_writes.append(dict(va=hex(at),bytes=size,value=hex(value),pc=hex(pc)));return
        return super().write(u,access,at,size,value,user)

    def code(self,u,pc,size,user):
        if pc in [0x52c488,0x49e0ac,0x49f80c,0xa870c4]:
            label={0x52c488:'before_cpu_affinity_register',0x49e0ac:'before_resource_exhaustion_notification',
                   0x49f80c:'before_message_buffer_allocation',0xa870c4:'before_busy_spin_wait'}[pc]
            regs=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
            self.boundary=dict(operation=label,pc=hex(pc),registers=[hex(v) for v in regs],original_lr=hex(u.reg_read(R.UC_ARM_REG_LR)),
                               native_call=False,resource_reply_supplied=False,affinity_register_value_supplied=False)
            if pc==0x49f80c:
                sp=u.reg_read(R.UC_ARM_REG_SP)
                self.boundary['stack_words']=[hex(v) for v in words(u,sp,4)]
            u.emu_stop();return
        if pc==0x52c474:
            if self.adapted:return super().code(u,pc,size,user)
            self.instructions+=1;return
        if pc in [0x53fea0,0x53ffec]:
            assert self.adapted
            self.adapter_calls.append(dict(va=hex(pc),operation='declared_critical_enter' if pc==0x53fea0 else 'declared_critical_exit',declared_return=0))
            self.ret(0);return
        if pc in [0x4a032c,0xa87248,0x49eaf8,0x57b7be]:
            self.dynamic_events.append(dict(pc=hex(pc),registers=[hex(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)]))
        if pc==0x4a0390:
            # After original dynamic-ID function sets R0; capture actual output before unwinding.
            pointer=words(u,u.reg_read(R.UC_ARM_REG_SP)+0x20,1)[0]
            self.ram_metadata_results.append(dict(raw_return=hex(u.reg_read(R.UC_ARM_REG_R0)),output_pointer=hex(pointer),
                                                 output_word=hex(words(u,pointer,1)[0]),slot_context_pointer=hex(u.reg_read(R.UC_ARM_REG_R5))))
        if any(a<=pc<z for a,z in THUMB+ARM):self.instructions+=1;return
        return super().code(u,pc,size,user)

    def bounded(self,va,args,extra=()):
        self.boundary=None;u=self.u
        for i in range(4):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),args[i] if i<len(args) else 0)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        if extra:u.mem_write(STACK+0xf000,struct.pack('<'+'I'*len(extra),*extra))
        u.emu_start(va|1,STOP+4,count=180000)
        pc=u.reg_read(R.UC_ARM_REG_PC)
        if self.boundary:assert pc==int(self.boundary['pc'],16)
        else:
            assert pc==STOP,hex(pc)
            assert u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
            assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        return dict(boundary=self.boundary,returned=pc==STOP,raw_r0=hex(u.reg_read(R.UC_ARM_REG_R0)))

    def initialize(self,blocks=16):
        self.u.mem_write(META,b'\xa7'*0x10000)
        out=self.bounded(0xa87206,[META,blocks*64]);assert out['returned']
        assert words(self.u,POOL+0x10,4)==[META,blocks*64,blocks*64,blocks*64]
        p=words(self.u,POOL+8,1)[0];chain=[]
        while p:
            assert p not in chain;chain.append(p);p=words(self.u,p,1)[0]
        assert chain==[META+64*i for i in range(blocks)]
        self.pool_initialization=dict(original_initializer='0xa87206',declared_RAM_base=hex(META),declared_bytes=blocks*64,
                                      original_free_chain=[hex(v) for v in chain],pool_header=[hex(v) for v in words(self.u,POOL,8)],
                                      scope='Declared emulated RAM extent initialized by original code; software metadata pool, not physical image memory or a recovered camera heap.')
        return self.pool_initialization

    def snapshot(self):
        free=words(self.u,POOL+0x18,1)[0]
        return dict(free_metadata_bytes=free,used_metadata_blocks=(self.pool_initialization['declared_bytes']-free)//64,
                    bitmap_first_words=[hex(v) for v in words(self.u,BITMAP,4)],
                    original_lazy_object_count=words(self.u,COUNTERS,1)[0],original_index_block_count=words(self.u,COUNTERS+0x10,1)[0],
                    lazy_root_pointer=hex(words(self.u,INDEX+0x110+0x30*4,1)[0]))

    def nrv_prefix(self,context):
        return self.bounded(0x3c7574,[context,3,0x100,0],[0,0,1,0,0,DATA+0x10d0,0])

def main():
    raw=image();rows=[]
    g=Guest(raw,False);init=g.initialize();out=g.nrv_prefix(1)
    assert out['boundary']['pc']=='0x52c488' and not g.adapter_calls and not g.events
    assert g.snapshot()['used_metadata_blocks']==0
    rows.append(dict(case='strict_original_context_stops_before_CP15',initialization=init,result=out,snapshot=g.snapshot(),
                     critical_adapters=g.adapter_calls,inherited_context_adapters=g.events))
    for context in [1,5,7]:
        g=Guest(raw);init=g.initialize();out=g.nrv_prefix(context)
        assert out['boundary']['pc']=='0x49f80c'
        assert out['boundary']['registers'][0]=='0x61003c' and out['boundary']['registers'][2:] == ['0xd8','0x0']
        assert len(g.ram_metadata_results)==1 and g.ram_metadata_results[0]['raw_return']=='0x0'
        assert g.ram_metadata_results[0]['output_word']=='0x9005601f'
        snap=g.snapshot();assert snap['used_metadata_blocks']==5 and snap['bitmap_first_words'][0]=='0x80000000'
        assert snap['original_lazy_object_count']==1 and snap['original_index_block_count']==3
        rows.append(dict(case=f'original_NRV_context{context}_to_message_allocation',context=context,initialization=init,result=out,
                         original_dynamic_ID_results=g.ram_metadata_results,snapshot=snap,metadata_events=g.dynamic_events,
                         critical_adapters=g.adapter_calls,inherited_context_adapters=g.events,write_events=g.metadata_writes))
    g=Guest(raw);init=g.initialize();ids=[]
    for slot in [DATA+0x200,DATA+0x204]:
        g.u.mem_write(slot,b'\xa7'*4);out=g.bounded(0x4a032c,[0x2a,5,slot]);assert out['returned'] and out['raw_r0']=='0x0'
        ids.append(hex(words(g.u,slot,1)[0]))
    assert ids==['0x9005601f','0x9005601e']
    assert g.snapshot()['used_metadata_blocks']==7 and g.snapshot()['bitmap_first_words'][0]=='0xc0000000'
    rows.append(dict(case='two_original_dynamic_ID_allocations',initialization=init,ids=ids,snapshot=g.snapshot(),
                     original_results=g.ram_metadata_results,critical_adapters=g.adapter_calls,inherited_context_adapters=g.events,write_events=g.metadata_writes))
    for label,blocks,full,busy in [('empty_metadata_pool',0,False,False),('full_dynamic_ID_bitmap',16,True,False),('busy_original_spinlock',16,False,True)]:
        g=Guest(raw);init=g.initialize(blocks)
        if full:g.u.mem_write(BITMAP,b'\xff'*0x200)
        if busy:g.u.mem_write(BANK,struct.pack('<I',0x80000000))
        g.u.mem_write(DATA+0x200,b'\xa7'*4);out=g.bounded(0x4a032c,[0x2a,5,DATA+0x200])
        assert out['boundary']['pc']==('0xa870c4' if busy else '0x49e0ac')
        assert words(g.u,DATA+0x200,1)[0]==0xa7a7a7a7 and not g.ram_metadata_results
        assert g.snapshot()['used_metadata_blocks']==0
        rows.append(dict(case=label,initialization=init,declared_full_bitmap=full,declared_busy_lock=busy,result=out,
                         output_sentinel_unchanged=True,snapshot=g.snapshot(),critical_adapters=g.adapter_calls,
                         inherited_context_adapters=g.events,write_events=g.metadata_writes))
    out=dict(cp_sha256=PIN,cases=rows,source_spans=[dict(va=hex(a),bytes=z-a,mode='Thumb',sha256=hashlib.sha256(raw[a-BASE:z-BASE]).hexdigest()) for a,z in THUMB]+
             [dict(va=hex(a),bytes=z-a,mode='ARM',sha256=hashlib.sha256(raw[a-BASE:z-BASE]).hexdigest()) for a,z in ARM],
             scope='Original dynamic OSAL ID and metadata allocation in RAM. Strict NRV case stops before MPIDR/CP15 read with no context/critical adapters. Adapted cases use declared context0, IRQ-mask initial state and critical enter/exit returns0; original CPSR query, LDREX/STREX spinlocks, metadata pool initializer/pop, sparse queue-object/index construction, ID-bit allocation and original NRV/descriptor/message-container prefixes execute. No dynamic-ID, memory-block or image-service result is supplied by a hook. Declared RAM heap and zeroed bitmap/index state are not live state. The new ID is software metadata, not a frame buffer or CMOS RAW. Stops before original message-buffer allocation or resource-exhaustion/busy-wait boundary; no real message, target-native/device action, pixels, donor ISP or flashability.')
    (HERE/'dynamic-id-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),normal_prefixes_to_message_allocation=3,dynamic_ID_results_fabricated=0,device_actions=0)))

if __name__=='__main__':main()
