#!/usr/bin/env python3
"""Original DmmWrapper AllocNew message construction, stopped before submission."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'dynamic-id-20261029'))
from dynamic_id_guest import Guest as DynamicGuest,image,BASE,PIN,META,POOL,INDEX,DATA,STACK,STOP,words
VAR=0x147f9c0
VAR_BYTES=0x80000
SPANS=[(0x49dbea,0x49dc1a),(0x49f80c,0x49f8d8),(0x49fc4c,0x49fdf0),(0x4a0980,0x4a0aee),
       (0x44d710,0x44d7e8),(0xa878d2,0xa878d8)]

class Guest(DynamicGuest):
    def __init__(self,raw,adapted=True):
        super().__init__(raw,adapted);self.u.mem_map(META+0x10000,0x80000);self.u.mem_map(0x147d000,0x1000)
        self.initializing=False;self.var_base=None;self.message_writes=[];self.allocation_returns=[];self.packet_entries=[]

    def write(self,u,access,at,size,value,user):
        pc=u.reg_read(R.UC_ARM_REG_PC)
        if VAR<=at and at+size<=VAR+0x20 or self.var_base is not None and self.var_base<=at and at+size<=self.var_base+VAR_BYTES:
            assert any(a<=pc<z for a,z in SPANS) or 0xa87084<=pc<0xa8710e,hex(pc)
            self.message_writes.append(dict(va=hex(at),bytes=size,value=hex(value),pc=hex(pc)));return
        if META<=at and at+size<=META+0x10000 and any(a<=pc<z for a,z in SPANS):
            self.message_writes.append(dict(va=hex(at),bytes=size,value=hex(value),pc=hex(pc),region='software_metadata'));return
        return super().write(u,access,at,size,value,user)

    def code(self,u,pc,size,user):
        if self.initializing and pc==0x49dc1a:u.emu_stop();return
        if pc==0xa878ca:
            regs=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
            p=regs[1];header=bytes(u.mem_read(p-0x18,0x18));body=bytes(u.mem_read(p,0xd8))
            mask=bytearray(0xd8)
            for w in self.message_writes:
                a=int(w['va'],16);z=a+w['bytes']
                if p<=a and z<=p+0xd8:mask[a-p:z-p]=b'\1'*w['bytes']
            assert sum(mask)==14 and all(v==0xa7 for v,m in zip(body,mask) if not m)
            self.boundary=dict(operation='before_original_DMM_submission',pc=hex(pc),registers=[hex(v) for v in regs],
                               original_lr=hex(u.reg_read(R.UC_ARM_REG_LR)),native_call=False,submission_executed=False,service_reply_supplied=False,
                               payload_pointer=hex(p),payload_bytes=len(body),payload_hex=body.hex(),header_hex=header.hex(),
                               original_payload_write_mask=mask.hex(),original_payload_written_bytes=sum(mask),unwritten_payload_fill='0xa7',
                               original_payload_fields=dict(word0=hex(struct.unpack_from('<H',body,0)[0]),key4=hex(struct.unpack_from('<I',body,4)[0]),
                                                            wordC=hex(struct.unpack_from('<I',body,0xc)[0]),word14=hex(struct.unpack_from('<H',body,0x14)[0]),
                                                            word16=hex(struct.unpack_from('<H',body,0x16)[0])),
                               original_header_fields=dict(block_count=header[8],flags=hex(header[9]),reference_count=struct.unpack_from('<H',header,0xa)[0],
                                                           reply_ID=hex(struct.unpack_from('<I',header,0xc)[0]),length=struct.unpack_from('<I',header,0x10)[0],
                                                           guard=hex(struct.unpack_from('<I',header,0x14)[0])),
                               tail_guard=hex(words(u,p+0xd8,1)[0]))
            u.emu_stop();return
        if pc in [0x49f80c,0x49fc4c,0x4a0980,0x44d710]:
            self.packet_entries.append(dict(pc=hex(pc),registers=[hex(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)]))
        if pc==0x49f8d2:
            self.allocation_returns.append(dict(pc=hex(pc),raw_return=hex(u.reg_read(R.UC_ARM_REG_R0)),
                                                output_pointer=hex(u.reg_read(R.UC_ARM_REG_R6)),
                                                output_word=hex(words(u,u.reg_read(R.UC_ARM_REG_R6),1)[0])))
        if any(a<=pc<z for a,z in SPANS):self.instructions+=1;return
        return super().code(u,pc,size,user)

    def initialize(self,blocks=16):
        u=self.u;self.var_base=META+blocks*64;u.mem_write(META,b'\xa7'*0x90000)
        for i in range(4):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_R4,META);u.reg_write(R.UC_ARM_REG_R5,blocks*64)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        self.initializing=True;u.emu_start(0x49dbeb,STOP+4,count=40000);self.initializing=False
        assert u.reg_read(R.UC_ARM_REG_PC)==0x49dc1a and u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
        assert words(u,POOL+0x10,4)==[META,blocks*64,blocks*64,blocks*64]
        assert words(u,VAR+8,2)==[self.var_base,self.var_base] and words(u,VAR+0x18,2)==[VAR_BYTES,VAR_BYTES]
        assert words(u,self.var_base,2)==[0,VAR_BYTES] and words(u,VAR+0x10,1)==[VAR_BYTES]
        chain=[];p=words(u,POOL+8,1)[0]
        while p:
            assert p not in chain;chain.append(p);p=words(u,p,1)[0]
        assert chain==[META+64*i for i in range(blocks)]
        self.pool_initialization=dict(original_fragment='0x49dbea..0x49dc1a',declared_entry_registers=dict(r4=hex(META),r5=blocks*64),
                                      declared_RAM_base=hex(META),declared_bytes=blocks*64,original_free_chain=[hex(v) for v in chain],
                                      original_variable_pool_base=hex(self.var_base),original_variable_pool_bytes=VAR_BYTES,
                                      original_variable_pool_header=[hex(v) for v in words(u,VAR,8)],
                                      scope='Original initializer fragment and called metadata initializer, with declared base and metadata extent; fixed512KiB variable-pool size comes from original instructions. Not normal boot execution or current camera RAM.')
        return self.pool_initialization

    def snapshot(self):
        r=super().snapshot();r['variable_pool']=dict(header=[hex(v) for v in words(self.u,VAR,8)],
                                                   free_bytes=words(self.u,VAR+0x18,1)[0],first_free_block_size=words(self.u,self.var_base+4,1)[0])
        return r

def main():
    raw=image();rows=[]
    for c in [1,5,7]:
        g=Guest(raw);init=g.initialize();out=g.nrv_prefix(c);b=out['boundary']
        assert b['pc']=='0xa878ca' and b['registers'][0]=='0x61003c'
        assert b['original_payload_fields']==dict(word0='0x20',key4='0x4af',wordC='0x0',word14='0x55',word16='0x1')
        assert b['original_header_fields']==dict(block_count=4,flags='0x1',reference_count=1,reply_ID='0x9005601f',length=0xd8,guard='0x55555555')
        assert b['tail_guard']=='0x77777777' and b['payload_pointer']==hex(g.var_base+VAR_BYTES-0x100+0x18)
        snap=g.snapshot();assert snap['used_metadata_blocks']==7 and snap['variable_pool']['free_bytes']==VAR_BYTES-0x100
        assert len(g.allocation_returns)==1 and g.allocation_returns[0]['raw_return']=='0x0'
        rows.append(dict(case=f'original_NRV_context{c}_DMM_packet',context=c,initialization=init,result=out,snapshot=snap,
                         original_message_allocation_returns=g.allocation_returns,packet_entries=g.packet_entries,
                         original_dynamic_ID_results=g.ram_metadata_results,message_writes=g.message_writes,
                         critical_adapters=g.adapter_calls,inherited_context_adapters=g.events,
                         scope='Original descriptor-allocation client, message allocators, metadata and variable pools, container and DmmWrapper fields execute under explicit environment fixtures. Unwritten payload bytes retain a7 fixture fill. Stops before submission; no provider reply, image handle or pixels supplied.'))
    g=Guest(raw,False);init=g.initialize();out=g.nrv_prefix(1)
    assert out['boundary']['pc']=='0x52c488' and not g.adapter_calls and not g.events
    rows.append(dict(case='strict_context_after_original_pool_fragment',initialization=init,result=out,snapshot=g.snapshot(),
                     critical_adapters=g.adapter_calls,inherited_context_adapters=g.events))
    for label,busy in [('variable_pool_exhausted',False),('variable_pool_lock_busy',True)]:
        g=Guest(raw);init=g.initialize()
        if busy:g.u.mem_write(VAR,struct.pack('<I',0x80000000))
        else:
            # Declared exhausted state; no fake allocation or provider result.
            g.u.mem_write(VAR+8,b'\0'*4);g.u.mem_write(VAR+0x18,b'\0'*8)
        out=g.nrv_prefix(1)
        assert out['boundary']['pc']==('0xa870c4' if busy else '0x49e0ac')
        if busy:assert out['boundary']['registers'][0]=='0x80000000'
        assert not g.allocation_returns
        rows.append(dict(case=label,initialization=init,declared_busy_variable_lock=busy,declared_variable_pool_exhausted=not busy,
                         result=out,snapshot=g.snapshot(),critical_adapters=g.adapter_calls,inherited_context_adapters=g.events,
                         original_dynamic_ID_results=g.ram_metadata_results,message_writes=g.message_writes,packet_entries=g.packet_entries))
    g=Guest(raw);g.u.mem_write(DATA+0x200,b'\xa7'*4)
    out=g.bounded(0x49f80c,[0x61003c,DATA+0x200,0x1001,0])
    assert out['returned'] and out['raw_r0']=='0xfffffc00' and words(g.u,DATA+0x200,1)==[0xa7a7a7a7]
    assert not g.adapter_calls and not g.events
    rows.append(dict(case='original_message_length_limit',declared_payload_bytes=0x1001,result=out,output_sentinel_unchanged=True,
                     critical_adapters=g.adapter_calls,inherited_context_adapters=g.events))
    out=dict(cp_sha256=PIN,cases=rows,source_spans=[dict(va=hex(a),bytes=z-a,sha256=hashlib.sha256(raw[a-BASE:z-BASE]).hexdigest()) for a,z in SPANS],
             scope='Original DmmWrapper AllocNew request construction in Unicorn RAM only: original metadata/variable-pool initialization fragment, original allocation and framing, under declared RAM, context0, initial IRQ mask1 and critical enter/exit0. No allocation pointer, dynamic-ID or provider response is fabricated by a hook. Strict case stops before MPIDR; successful packet cases stop before submission. Does not prove queue receiver identity, main recording binding, physical DMA/buffers/CMOS RAW, full donor colour pipeline or modified firmware admission. No native/device/USB/real IPC action.')
    (HERE/'dmm-request-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),original_packets_before_submission=3,provider_replies=0,device_actions=0)))

if __name__=='__main__':main()
