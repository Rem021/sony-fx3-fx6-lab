#!/usr/bin/env python3
"""Original NOR BK4 initializer/descriptor query in isolated ARM64 RAM."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from unicorn import *
from unicorn import arm64_const as R
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
BASE=0xfe049000;TOP=0xfe064000;BACKUP=0x100000000;STACK=0x200000000;OUT=0x300000000;STOP=0x400000000
PIN='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
class Guest:
    def __init__(self,raw,record):
        self.raw=raw;self.record=record;self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        self.u.mem_map(BASE,TOP-BASE);self.u.mem_write(BASE,raw)
        self.initialized=bytearray(TOP-BASE);self.initialized[:len(raw)]=b'\1'*len(raw)
        self.u.mem_map(BACKUP,(len(record)+4095)&~4095,UC_PROT_READ);self.u.mem_write(BACKUP,record)
        self.u.mem_map(STACK,0x10000);self.u.mem_map(OUT,0x4000);self.u.mem_write(OUT,b'\xa7'*0x4000)
        self.u.mem_map(STOP,0x1000)
        self.cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);self.cache={}
        self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_READ,self.read)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self.write);self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid)
    def stop(self,reason,**extra):
        self.boundary=dict(reason=reason,PC=hex(self.u.reg_read(R.UC_ARM64_REG_PC)),**extra);self.u.emu_stop()
    def code(self,u,pc,size,user):
        if pc==STOP:self.stop('returned');return
        if not BASE<=pc<BASE+len(self.raw):self.stop('outside_original_code',address=hex(pc));return
        if pc not in self.cache:
            i=next(self.cs.disasm(bytes(u.mem_read(pc,4)),pc,count=1));self.cache[pc]=(i.mnemonic,i.op_str)
        mn,op=self.cache[pc]
        if mn in ['mrs','msr','sys','sysl','dc','ic','tlbi','dsb','dmb','isb','sev','wfe','wfi','svc','hvc','smc']:
            self.stop('before_CPU_or_hardware_operation',instruction=mn+' '+op);return
        self.instructions+=1
        if len(self.trace)<16:self.trace.append(hex(pc))
        if self.instructions>=100000:self.stop('instruction_budget')
    def read(self,u,access,at,size,value,user):
        if BASE<=at and at+size<=TOP:
            if 0 in self.initialized[at-BASE:at-BASE+size]:self.stop('before_unknown_RAM_read',address=hex(at),bytes=size)
        elif BACKUP<=at and at+size<=BACKUP+len(self.record):pass
        elif STACK<=at and at+size<=STACK+0x10000:pass
        elif OUT<=at and at+size<=OUT+0x4000:pass
        else:self.stop('before_external_read',address=hex(at),bytes=size)
    def write(self,u,access,at,size,value,user):
        if 0xfe061e98<=at and at+size<=0xfe061eb0:
            self.initialized[at-BASE:at-BASE+size]=b'\1'*size;self.writes+=1
        elif OUT<=at and at+size<=OUT+0x4000:self.writes+=1
        elif not(STACK<=at and at+size<=STACK+0x10000):self.stop('before_external_write',address=hex(at),bytes=size)
    def invalid(self,u,access,at,size,value,user):
        self.stop('unmapped_external_state',address=hex(at),bytes=size);return False
    def call(self,entry,args=()):
        self.instructions=0;self.writes=0;self.trace=[];self.boundary=None
        self.u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);self.u.reg_write(R.UC_ARM64_REG_LR,STOP)
        for i,x in enumerate(args):self.u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),x)
        try:self.u.emu_start(entry,STOP+4,timeout=3000000,count=100000)
        except UcError:
            if self.boundary is None:raise
        assert self.boundary is not None
        return dict(entry=hex(entry),arguments=list(map(hex,args)),boundary=self.boundary,
            registers=[hex(self.u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))) for i in range(4)],
            original_instructions=self.instructions,nonstack_RAM_writes=self.writes,first_trace=self.trace)
def main():
    out=HERE/'NOR-descriptor-query-results.json';assert not out.exists()
    raw=(HERE/'original-files/loader_nor.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
    evidence=json.loads((HERE/'load-descriptor-sources.json').read_text())
    canonical=next(x for x in evidence['templates'] if x['member']==evidence['canonical_template'])
    cases=[]
    for bank in canonical['banks']:
        record=(TASK/f'dmm-backup-20261029/original-records/canonical-bank{bank["bank"]}.bin').read_bytes()
        assert hashlib.sha256(record).hexdigest()==bank['record_sha256']
        g=Guest(raw,record)
        init=g.call(0xfe04d63c,[BACKUP]);assert init['boundary']['reason']=='returned' and init['registers'][0]=='0x0'
        query=g.call(0xfe04c7b4,[0xfa0080,OUT]);assert query['boundary']['reason']=='returned'
        expected=(HERE/bank['saved_payload']).read_bytes();actual=bytes(g.u.mem_read(OUT,len(expected)))
        assert query['registers'][0]=='0x2400' and actual==expected
        canary=bytes(g.u.mem_read(OUT+len(expected),16));assert canary==b'\xa7'*16
        cases.append(dict(bank=bank['bank'],record_sha256=bank['record_sha256'],original_initializer=init,
            original_query=query,output_bytes=len(actual),output_sha256=hashlib.sha256(actual).hexdigest(),
            exact_original_payload_equal=True,following_16_byte_canary_unchanged=True))
    g=Guest(raw,record)
    strict=g.call(0xfe0545dc,[0x05000000,OUT+0x3000])
    assert strict['boundary']['address']=='0xfe26c300'
    result=dict(NOR_source_sha256=PIN,base=hex(BASE),cases=cases,strict_whole_configuration_entry=strict,
        scope='Original ARM64 BK4 initializer and 9216-byte query, with original records as explicit model inputs and no query/lock/file reply adapters. Strict whole loader stops at unknown backup-ready state. No normal record selection, FAT read, physical write, cache setup, camera/USB access, native Sony process or full boot.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=[dict(bank=x['bank'],bytes=x['output_bytes'],query=x['original_query']['boundary'],
        instructions=x['original_query']['original_instructions']) for x in cases],strict=strict['boundary'])))
if __name__=='__main__':main()
