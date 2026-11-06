#!/usr/bin/env python3
"""Original CP bootstrap/MMU producer in bounded RAM; no physical/host Sony execution."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from unicorn import *
from unicorn import arm_const as R
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
SOURCE=TASK.parent/'sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
PIN='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
BASE=0x108000;TOP=0x1600000;STACK=0x20000000;STOP=0x30000000;FLAG=0x3e42000;ROOT=0x14007c8
class Guest:
    def __init__(self,raw,flag=None):
        self.raw=raw;self.flag=flag;self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        self.u.mem_map(BASE,TOP-BASE);self.u.mem_write(BASE,raw)
        self.u.mem_map(STACK,0x10000);self.u.mem_map(STOP,0x1000)
        if flag is not None:self.u.mem_map(FLAG,0x1000,UC_PROT_READ);self.u.mem_write(FLAG,bytes([flag,0]))
        self.init=bytearray(TOP-BASE);self.init[:len(raw)]=b'\1'*len(raw)
        self.cs={False:Cs(CS_ARCH_ARM,CS_MODE_ARM),True:Cs(CS_ARCH_ARM,CS_MODE_THUMB)};self.decoded={}
        self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_READ,self.read);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
        self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid)
        self.results=[];self.reset()
    def reset(self):
        self.instructions=0;self.writes=0;self.flag_reads=0;self.boundary=None;self.trace=[];self.stop_at={}
    def stop(self,reason,**kwargs):
        self.boundary=dict(reason=reason,PC=hex(self.u.reg_read(R.UC_ARM_REG_PC)),**kwargs);self.u.emu_stop()
    def code(self,u,pc,size,user):
        if pc==STOP:self.stop('returned');return
        if pc in self.stop_at:self.stop(self.stop_at[pc]);return
        if not BASE<=pc<BASE+len(self.raw):self.stop('outside_original_image_execution',address=hex(pc));return
        thumb=bool(u.reg_read(R.UC_ARM_REG_CPSR)&0x20);key=(pc,thumb)
        if key not in self.decoded:
            decoded=list(self.cs[thumb].disasm(bytes(u.mem_read(pc,4)),pc,count=1));assert decoded
            self.decoded[key]=(decoded[0].mnemonic,decoded[0].op_str)
        mn,op=self.decoded[key]
        if mn in ['mcr','mrc','mcrr','mrrc','cpsid','cpsie','svc','smc','hvc','wfe','wfi','dsb','isb','sev']:
            self.stop('before_privileged_or_hardware_operation',instruction=mn+' '+op);return
        self.instructions+=1
        if len(self.trace)<24:self.trace.append(hex(pc))
        if self.instructions>=500000:self.stop('instruction_budget')
    def read(self,u,access,at,size,value,user):
        if at in [FLAG,FLAG+1]:
            if at==FLAG+1 or self.flag is None:self.stop('before_unknown_hardware_flag_read',address=hex(at),bytes=size);return
            self.flag_reads+=1;return
        if BASE<=at and at+size<=TOP:
            offset=at-BASE
            if 0 in self.init[offset:offset+size]:self.stop('before_uninitialized_RAM_read',address=hex(at),bytes=size)
        elif not STACK<=at<STACK+0x10000:self.stop('before_external_read',address=hex(at),bytes=size)
    def write(self,u,access,at,size,value,user):
        if BASE<=at and at+size<=TOP:
            assert (0x108d8c<=at and at+size<=0x108f20) or at>=0x1007000,(hex(at),hex(u.reg_read(R.UC_ARM_REG_PC)))
            self.init[at-BASE:at-BASE+size]=b'\1'*size;self.writes+=1
        elif not (STACK<=at and at+size<=STACK+0x10000):self.stop('before_external_write',address=hex(at),bytes=size)
    def invalid(self,u,access,at,size,value,user):
        reason='before_unknown_hardware_flag_read' if at in [FLAG,FLAG+1] else 'unmapped_memory_boundary'
        self.stop(reason,address=hex(at),bytes=size);return False
    def call(self,entry,args=(),stops=None):
        self.reset();self.stop_at=stops or {}
        self.u.reg_write(R.UC_ARM_REG_CPSR,0x10)
        self.u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);self.u.reg_write(R.UC_ARM_REG_LR,STOP)
        for i,v in enumerate(args):self.u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),v)
        try:self.u.emu_start(entry,STOP+4,timeout=3000000,count=500000)
        except UcError as e:
            if self.boundary is None:raise
        assert self.boundary is not None
        r=dict(entry=hex(entry),args=list(map(hex,args)),declared_optional_flag=self.flag,boundary=self.boundary,
            original_instructions=self.instructions,original_RAM_writes=self.writes,flag_reads=self.flag_reads,first_trace=self.trace,
            registers=[hex(self.u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)])
        self.results.append(r);return r
    def words(self,at,n):return list(struct.unpack('<'+'I'*n,bytes(self.u.mem_read(at,n*4))))
def main():
    dest=HERE/'bootstrap-guest-results.json';assert not dest.exists();raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
    boot=raw[0x20000:0x20000+0x17c];assert hashlib.sha256(boot).hexdigest()=='543e6e57aa6ebb26257a96e3a28c59068cbd5eb9fef26c67ed8684c7fc05f50b'
    cases=[]
    g=Guest(raw);r=g.call(0x108398);assert r['boundary']['PC']=='0x10897c';cases.append(dict(name='strict_full_entry',**r))
    g=Guest(raw);r=g.call(0x1083a4);assert r['boundary']['PC']=='0x1089ec'
    cases.append(dict(name='strict_post_poll_fragment',**r,L1_pointer=hex(g.words(0x108f1c,1)[0]),L2_pointer=hex(g.words(0x108d98,1)[0]),
        note='Separate fragment after polling; poll success is not supplied or claimed.'))
    for flag in [0,1]:
        g=Guest(raw,flag);stop={0x108728:'before_CPU_setup_call'} if flag==0 else {0x108434:'after_declared_optional_flag_before_table_generation'}
        r=g.call(0x1083a4,stops=stop)
        cases.append(dict(name=f'post_poll_declared_flag_{flag}',**r,L1_pointer=hex(g.words(0x108f1c,1)[0]),
            L2_pointer=hex(g.words(0x108d98,1)[0]),boot_metadata=[hex(x) for x in g.words(0x1007000,6)],
            original_copy_matches=bytes(g.u.mem_read(0x108da0,len(boot)))==boot))
        if flag==0:
            assert r['boundary']['PC']=='0x108728'
            r2=g.call(0x553d48,[ROOT]);cases.append(dict(name='original_software_MMU_init_after_flag0_prefix',**r2,
                ROOT_first3=[hex(x) for x in g.words(ROOT,3)],ROOT_boot_fields=[hex(x) for x in g.words(ROOT+0x20c,3)]))
    dest.write_text(json.dumps(dict(CP_source=str(SOURCE),CP_sha256=PIN,embedded_boot_descriptor_VA='0x128000',descriptor_bytes=len(boot),
        descriptor_sha256=hashlib.sha256(boot).hexdigest(),cases=cases,
        scope='Only original CP instructions in isolated RAM. Strict entry stops at hardware flag. Post-poll fragments do not claim the real poll passed; optional hardware flag0/1 are declared fixtures. Unknown RAM reads, external memory and privileged instructions stop. No synthetic MMU/table/attribute reply, device or full camera boot.'),indent=2)+'\n')
    print(json.dumps([dict(name=r['name'],boundary=r['boundary'],instructions=r['original_instructions'],writes=r['original_RAM_writes']) for r in cases]))
if __name__=='__main__':main()
