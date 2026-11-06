#!/usr/bin/env python3
"""Original DMM queue registration, original send prefix and callback boundary."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'dmm-request-20261029'))
from dmm_request_guest import Guest as RequestGuest,image,BASE,PIN,META,POOL,INDEX,DATA,STACK,STOP,words

SPANS=[(0x4d77e4,0x4d782a),(0x49ef00,0x49f00a),(0x49f368,0x49f5a0),
       (0xa874e2,0xa8750e),(0xab95e0,0xab9636),(0xa87b3c,0xa87b4e),(0xa878d8,0xa878de)]
SERVICE_SLOT=0x13f8fd8

class Guest(RequestGuest):
    def __init__(self,raw,adapted=True):
        super().__init__(raw,adapted)
        self.u.mem_map(0x13f8000,0x1000)
        self.service_events=[];self.service_writes=[];self.permit_submission=False
    def write(self,u,access,at,size,value,user):
        pc=u.reg_read(R.UC_ARM_REG_PC)
        if any(a<=pc<z for a,z in SPANS):
            assert (META<=at and at+size<=META+0x90000 or
                    SERVICE_SLOT<=at and at+size<=SERVICE_SLOT+4 or
                    INDEX<=at and at+size<=INDEX+0x210 or
                    0x147f940<=at and at+size<=0x147f954 or
                    STACK<=at and at+size<=STACK+0x10000), (hex(pc),hex(at))
            self.service_writes.append(dict(pc=hex(pc),va=hex(at),bytes=size,value=hex(value)));return
        return super().write(u,access,at,size,value,user)
    def code(self,u,pc,size,user):
        if pc in [0x52bd1c,0x52bdb8,0xab71cc]:
            self.boundary=dict(pc=hex(pc),operation='before_original_DMM_dispatcher' if pc==0xab71cc else 'before_original_kernel_thread_identity',
                registers=[hex(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)],
                original_lr=hex(u.reg_read(R.UC_ARM_REG_LR)),kernel_return_supplied=False,provider_reply_supplied=False)
            u.emu_stop();return
        if pc in [0x49ef00,0xa874e2,0xab95e0,0x49f4f4,0xa874fe]:
            self.service_events.append(dict(pc=hex(pc),registers=[hex(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)]))
        if self.permit_submission and 0xa878ca<=pc<0xa878d2 or any(a<=pc<z for a,z in SPANS):self.instructions+=1;return
        return super().code(u,pc,size,user)
    def register(self):
        out=self.bounded(0x4d77e4,[]);assert out['returned'] and out['raw_r0']=='0x0'
        record=words(self.u,SERVICE_SLOT,1)[0];context=words(self.u,INDEX+8+0x3c*4,1)[0]
        assert META<=record<META+0x10000 and words(self.u,record+8,1)==[0xa874e3]
        assert words(self.u,record+0x14,2)==[0xab95e1,0] and words(self.u,context+0x14,1)==[record]
        assert self.u.mem_read(record+0xd,1)==b'\1'
        return dict(result=out,record=hex(record),queue_context=hex(context),
                    record_words=[hex(v) for v in words(self.u,record,8)],
                    queue_words=[hex(v) for v in words(self.u,context,8)],
                    scope='Original registration function and original allocator/queue insertion under declared RAM pool/index state. Not normal boot scheduling or device registration.')

def main():
    target=HERE/'service-results.json';assert not target.exists();raw=image();rows=[]
    for context in [1,5,7]:
        g=Guest(raw);init=g.initialize();reg=g.register();packet=g.nrv_prefix(context)
        assert packet['boundary']['pc']=='0xa878ca';p=int(packet['boundary']['payload_pointer'],16)
        g.permit_submission=True;sent=g.bounded(0xa878ca,[0x61003c,p])
        assert sent['boundary']['pc']=='0x52bd1c'
        # The synchronous send has NOT completed. Test the exact originally stored
        # callback separately; no kernel identity or queue response is invented.
        record=int(reg['record'],16);callback=words(g.u,record+0x14,1)[0]
        received=g.bounded(callback&~1,[p,0])
        assert received['boundary']['pc']=='0xab71cc'
        assert received['boundary']['registers'][:3]==['0x9005601f',hex(p),'0xd8']
        rows.append(dict(case=f'original_registration_send_and_separate_callback_context{context}',
            context=context,initialization=init,registration=reg,packet=packet,send_prefix=sent,
            callback_prefix=received,separate_callback_entry=True,original_send_completed=False,
            snapshot=g.snapshot(),events=g.service_events,writes=g.service_writes,
            inherited_context_adapters=g.events,critical_adapters=g.adapter_calls))
    g=Guest(raw,False);g.initialize();reg=g.bounded(0x4d77e4,[])
    assert reg['boundary']['pc']=='0x52c488' and not g.events and not g.adapter_calls
    assert g.snapshot()['used_metadata_blocks']==0
    rows.append(dict(case='strict_original_queue_registration_before_CPU_affinity',registration_prefix=reg,
                     snapshot=g.snapshot(),events=g.service_events,writes=g.service_writes,
                     inherited_context_adapters=g.events,critical_adapters=g.adapter_calls))
    out=dict(cp_sha256=PIN,cases=rows,scope='Unicorn RAM only. Original queue registration and lookup connect ID0x61003c to callback0xab95e1. Original send stops before kernel thread identity. Separate direct entry of originally registered callback reaches dispatcher with original packet/header, without provider reply. No actual send completion, dispatcher handler execution, physical image buffer, MAIN pixel binding, complete donor ISP, modified firmware admission, device/USB or native Sony execution.')
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),adapted_original_registrations=3,strict_affinity_boundaries=1,send_kernel_boundaries=3,separate_callback_prefixes=3,provider_replies=0,device_actions=0)))

if __name__=='__main__':main()
