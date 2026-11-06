#!/usr/bin/env python3
"""Original STP allocator up to lock/MMIO boundaries; no register read fixture."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'frame-route-20261029'))
from mask_acquisition_guest import Guest as MaskGuest,image,BASE,PIN,OBJ,RECORDS
OWNERS=0x1491214
SCRATCH=0x11941d0
LOCK_ID=0x53545001
SPANS=[(0x37b078,0x37b1e0),(0x37b250,0x37b292),(0x37c8c0,0x37c8e4),(0x37c994,0x37c9a2),
       (0x93fdcc,0x93fe10),(0x93fb88,0x93fbf0),(0x36c024,0x36c03c)]

class Guest(MaskGuest):
    def __init__(self,raw,adapt_lock=False,occupied=False):
        super().__init__(raw,True);self.adapt_lock=adapt_lock;self.occupied=occupied
        self.u.mem_map(0x1491000,4096);self.u.mem_map(0x1194000,4096)
        self.u.mem_write(OWNERS,b'\0'*96)
        if occupied:self.u.mem_write(OWNERS,struct.pack('<I',0x50001))
        self.u.mem_write(0x100d560,struct.pack('<I',LOCK_ID));self.u.mem_write(0x1004a85,b'\0')
        self.stp_output=None;self.stp_writes=[];self.stp_events=[];self.stp_returns=[]
    def write(self,u,access,at,size,value,user):
        if OWNERS<=at and at+size<=OWNERS+96:
            pc=u.reg_read(R.UC_ARM_REG_PC)
            assert size==4 and pc in [0x48316e,0x4831a2]
            assert (at-OWNERS)%24 in [0,16]
            self.stp_writes.append(dict(address=hex(at),bytes=size,value=hex(value),pc=hex(pc)));return
        if SCRATCH<=at and at+size<=SCRATCH+0x44:
            pc=u.reg_read(R.UC_ARM_REG_PC)
            assert 0x558af4<=pc<0x558c30 or pc in [0x483152,0x4831d0]
            self.stp_writes.append(dict(address=hex(at),bytes=size,value=hex(value),pc=hex(pc)));return
        return super().write(u,access,at,size,value,user)
    def code(self,u,pc,size,user):
        if self.binding and pc==0x483078:self.stp_output=u.reg_read(R.UC_ARM_REG_R2)
        if pc==0x49d6a4:
            assert u.reg_read(R.UC_ARM_REG_R0)==LOCK_ID and u.reg_read(R.UC_ARM_REG_R1)==0xffffffff
            if not self.adapt_lock:
                self.boundary=dict(operation='before_original_lock_wait',pc=hex(pc),native_call=False);u.emu_stop();return
            self.stp_events.append(dict(adapter='declared RAM lock wait',result=0));self.ret(0);return
        if pc==0x49d910:
            assert self.adapt_lock and u.reg_read(R.UC_ARM_REG_R0)==LOCK_ID
            self.stp_events.append(dict(adapter='declared RAM lock release',result=0));self.ret(0);return
        if pc==0x474306:
            address=u.reg_read(R.UC_ARM_REG_R2);assert address==0xf5410828
            assert not any(lo<=address<=hi for lo,hi,permissions in u.mem_regions())
            self.boundary=dict(operation='before_first_fixed_register_read',pc=hex(pc),address=hex(address),bytes=4,address_mapped_in_guest=False,register_value_supplied=False,native_read=False)
            u.emu_stop();return
        if pc==0x483166:self.stp_returns.append(hex(u.reg_read(R.UC_ARM_REG_R0)))
        if self.binding and any(a<=pc-BASE<z for a,z in SPANS):self.instructions+=1;return
        return super().code(u,pc,size,user)
    def result(self):
        producer=self.produce(0x40fc09,0,0,original_callsite=True);row=self.bind_bounded()
        row.update(producer=producer,declared_lock_adapter=self.adapt_lock,declared_occupied_stp_slot=self.occupied,
                   declared_log_mode=0,stp_output_at_boundary=None if self.stp_output is None else hex(struct.unpack('<I',self.u.mem_read(self.stp_output,4))[0]),
                   stp_owner_records_hex=bytes(self.u.mem_read(OWNERS,96)).hex(),original_stp_global_writes=self.stp_writes,stp_adapter_events=self.stp_events,original_stp_return_values=self.stp_returns)
        return row

def main():
    raw=image();rows=[]
    for label,adapt,occupied in [('before_lock',False,False),('free_slot_before_register',True,False),('occupied_slot',True,True)]:
        guest=Guest(raw,adapt,occupied);row=guest.result();row['case']=label
        if label=='before_lock':assert row['boundary']['operation']=='before_original_lock_wait' and not row['original_stp_global_writes']
        elif label=='free_slot_before_register':
            assert row['boundary']['operation']=='before_first_fixed_register_read' and row['stp_output_at_boundary']=='0x50001'
            assert row['stp_owner_records_hex'][:8]=='01000500' and not row['original_stp_return_values']
        else:
            assert row['returned'] and row['return_value']==0 and row['original_stp_return_values']==['0xffffffff']
            assert not any(int(w['address'],16)>=OWNERS for w in row['original_stp_global_writes'])
        rows.append(row)
    result=dict(cp_sha256=PIN,cases=rows,source_spans=[dict(file_offset=hex(a),bytes=z-a,sha256=hashlib.sha256(raw[a:z]).hexdigest()) for a,z in SPANS],
                scope='Original selector/broker/STP allocator, original lock wrapper, quiet diagnostic branch and first initialization/dispatch execute in Unicorn. Free-slot case writes STP owner and flags using original instructions, then stops before the first fixed-register read, with no MMIO value or success supplied. One case stops before lock wait; adapted cases declare RAM lock wait/release success, ownership slots, log flag and lock ID, not actual OSAL/hardware state. Occupied case returns original failure through broker. Existing VFX hardware stubs remain explicit. No native target execution, device, real registers, complete STP success, image buffers or flashability.')
    (HERE/'stp-prefix-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),first_register='0xf5410828',original_free_handle='0x50001',MMIO_reads=0,device_actions=0)))

if __name__=='__main__':main()
