#!/usr/bin/env python3
"""Original BK4 lookup and DMM source-range checks, stopped at kernel/map gates."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import arm_const as R
from unicorn import UC_PROT_READ
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
sys.path.insert(0,str(TASK/'dmm-config-20261029'))
from config_guest import Guest as ParserGuest,image,BASE,PIN,DATA,STACK,STOP,words
BACKUP=0x04000000
THUMB=[(0x4985c4,0x498636),(0xa85174,0xa8527c),(0xa84be8,0xa84c3c),(0x4d7a84,0x4d7b40)]

class Guest(ParserGuest):
    def __init__(self,raw,record,adapted=False):
        super().__init__(raw,b'');self.adapted=adapted;self.adapter_calls=[];self.query_returns=[]
        self.u.mem_map(BACKUP,(len(record)+4095)&~4095,UC_PROT_READ);self.u.mem_write(BACKUP,record)
        self.u.mem_map(0x13eb000,0x1000)
    def write(self,u,access,at,size,value,user):
        if 0x13eb2e8<=at and at+size<=0x13eb2f4:
            assert 0x4985c4<=u.reg_read(R.UC_ARM_REG_PC)<0x498636;self.writes+=1;return
        return super().write(u,access,at,size,value,user)
    def code(self,u,pc,size,user):
        if pc in [0x52ee34,0x52f17c]:
            if self.adapted:
                self.adapter_calls.append(dict(pc=hex(pc),declared_return=0,operation='declared_backup_mutex_enter' if pc==0x52ee34 else 'declared_backup_mutex_exit'))
                self.ret(0);return
            self.boundary=dict(pc=hex(pc),operation='before_original_backup_mutex',
                registers=[hex(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)],
                kernel_result_supplied=False,provider_reply_supplied=False)
            u.emu_stop();return
        if pc in [0x53894c,0x1500c0]:
            self.boundary=dict(pc=hex(pc),operation='before_original_memory_attribute_validation' if pc==0x53894c else 'before_original_no_range_diagnostic',
                registers=[hex(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)],
                kernel_result_supplied=False,memory_attribute_result_supplied=False,provider_reply_supplied=False)
            u.emu_stop();return
        if pc==0x4d7a9c:
            self.query_returns.append(dict(pc=hex(pc),value_low=hex(u.reg_read(R.UC_ARM_REG_R0)),value_high=hex(u.reg_read(R.UC_ARM_REG_R1))))
        if any(a<=pc<z for a,z in THUMB):self.instructions+=1;return
        return super().code(u,pc,size,user)

def main():
    target=HERE/'backup-query-results.json';assert not target.exists();raw=image()
    evidence=json.loads((HERE/'public-template-parameters.json').read_text())
    template=next(t for t in evidence['templates'] if t['member']==evidence['canonical_template']);cases=[]
    for bank in template['records']:
        record=(HERE/bank['saved_original']).read_bytes();assert hashlib.sha256(record).hexdigest()==bank['sha256']
        entry=int(bank['parameters'][0]['entry_offset'],16);value_at=int(bank['parameters'][0]['data_offset'],16)
        expected=int(bank['parameters'][0]['u64'],16)
        for adapted in [False,True]:
            g=Guest(raw,record,adapted);init=g.call(0x4985c4,[BACKUP]);assert init['returned'] and init['raw_r0']=='0x0'
            lookup=g.call(0xa85174,[0xfa0182]);pointer=int(lookup['raw_r0'],16);assert pointer==BACKUP+entry
            length=g.call(0xa8520a,[pointer]);assert length['raw_r0']=='0x8'
            data=g.call(0xa8523e,[pointer]);assert int(data['raw_r0'],16)==BACKUP+value_at
            actual=int.from_bytes(g.u.mem_read(BACKUP+value_at,8),'little');assert actual==expected
            out=g.call(0x4d7a84,[DATA,16])
            want=('0x1500c0' if bank['index']==0 else '0x53894c') if adapted else '0x52ee34'
            assert out['boundary']['pc']==want
            if adapted:
                assert len(g.adapter_calls)==2 and len(g.query_returns)==1
                assert int(g.query_returns[0]['value_low'],16)|(int(g.query_returns[0]['value_high'],16)<<32)==expected
                if bank['index']==1:assert out['boundary']['registers'][0]=='0x9a08e00'
            else:assert not g.adapter_calls and not g.query_returns
            assert g.reads==[]  # Parent's sequential-file adapter is never entered.
            cases.append(dict(bank_index=bank['index'],adapted_backup_mutex=adapted,original_record_sha256=bank['sha256'],
                initialization=init,original_entry_lookup=lookup,original_size_lookup=length,original_data_lookup=data,
                original_parameter_value=hex(actual),DMM_source_prefix=out,original_query_returns=g.query_returns,
                declared_mutex_adapters=g.adapter_calls,sequential_file_adapter_calls=0,
                original_instructions=g.instructions,original_RAM_writes=g.writes))
    target.write_text(json.dumps(dict(CP_sha256=PIN,cases=cases,
        scope='Original public BK4 records loaded as explicit RAM inputs and parsed by original CP initializer/helpers. Strict DMM path stops before backup mutex. Adapted mutex0 paths use original query and range code, stopping before no-range log or memory-attribute validation. No DmmCfg bytes loaded at candidate pointer, memory-attribute result, provider reply, physical allocation, normal bank selection, live state, native Sony program or device action.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),strict_mutex_stops=2,original_parameter_queries=2,bank0_no_CP_range=1,bank1_before_memory_attributes=1,file_adapter_calls=0,device_actions=0)))

if __name__=='__main__':main()
