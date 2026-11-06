#!/usr/bin/env python3
"""Original AP per-block checksum/length helpers, with explicit exception boundary."""
from pathlib import Path
from hashlib import sha256
import io,json,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_INVALID
from unicorn import arm64_const as R
from cbc_vectors import HERE,FW,pack

DATA,STACK,STOP=0x50000000,0x60000000,0x70000000


class Guest:
    def __init__(self,b):
        self.u=u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);e=ELFFile(io.BytesIO(b))
        loads=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD']
        top=max(s['p_vaddr']+s['p_memsz'] for s in loads)
        u.mem_map(0,(top+4095)&~4095)
        for s in loads:u.mem_write(s['p_vaddr'],s.data())
        for a,n in [(DATA,0x4000),(STACK,0x10000),(STOP,0x1000)]:u.mem_map(a,n)
        dyn=e.get_section_by_name('.dynsym');rel=e.get_section_by_name('.rela.plt');plt=e.get_section_by_name('.plt')
        self.plt={plt['sh_addr']+32+i*16:dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
        self.helpers={'_ZN7Updater15DecryptorModule13getHdDataSizeEv':0xa8d4,
                      '_ZN7Updater15DecryptorModule6calSumEv':0xa8a0,
                      '_ZN7Updater15DecryptorModule8getHdSumEv':0xa8e0}
        self.instructions=0;self.exception=None
        u.hook_add(UC_HOOK_CODE,self.code);u.hook_add(UC_HOOK_MEM_WRITE,self.write)
        def invalid(u,access,address,size,value,unused):raise AssertionError(('unmapped',hex(u.reg_read(R.UC_ARM64_REG_PC)),hex(address),size))
        u.hook_add(UC_HOOK_MEM_INVALID,invalid)

    def ret(self,value):
        self.u.reg_write(R.UC_ARM64_REG_X0,value);self.u.reg_write(R.UC_ARM64_REG_PC,self.u.reg_read(R.UC_ARM64_REG_LR))

    def code(self,u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        if pc in self.plt:
            name=self.plt[pc]
            if name in self.helpers:u.reg_write(R.UC_ARM64_REG_PC,self.helpers[name]);return
            if name=='printf':self.ret(0);return
            if name=='__cxa_allocate_exception':
                assert u.reg_read(R.UC_ARM64_REG_X0)==16
                self.ret(DATA+0x2000);return
            if name=='__cxa_throw':
                p=u.reg_read(R.UC_ARM64_REG_X0)
                self.exception=dict(code=hex(struct.unpack('<I',u.mem_read(p+8,4))[0]),
                                    declared_stop='__cxa_throw entry; no native unwinder or recovery executed')
                u.emu_stop();return
            raise AssertionError(('unhandled PLT',name))
        assert 0xa8a0<=pc<0xa9c0,hex(pc)
        self.instructions+=1

    def write(self,u,access,a,size,value,unused):
        assert (DATA<=a and a+size<=DATA+0x4000 or STACK<=a and a+size<=STACK+0x10000),hex(a)

    def call(self,entry,raw):
        u=self.u;assert len(raw)==1024
        u.mem_write(DATA,b'\0'*0x3000);u.mem_write(DATA+0xb0,raw)
        u.mem_write(STACK,b'\xa7'*0x10000)
        for i in range(19,30):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_LR,STOP)
        u.reg_write(R.UC_ARM64_REG_X0,DATA);self.exception=None
        before=self.instructions;u.emu_start(entry,STOP+4,count=10000)
        if self.exception is None:
            assert u.reg_read(R.UC_ARM64_REG_PC)==STOP and u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
            assert all(u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))==0x77770000+i for i in range(19,30))
        assert bytes(u.mem_read(STACK,0xe000))==b'\xa7'*0xe000
        return dict(returned=self.exception is None,exception=self.exception,instructions=self.instructions-before,
                    x0=u.reg_read(R.UC_ARM64_REG_X0))


def main():
    meta=json.loads((HERE/'verifier-library-inventory.json').read_bytes())
    pin=next(r['sha256'] for r in meta['libraries'] if r['source_path'].endswith('/libupdatercorecommon.so'))
    b=(HERE/'libraries/libupdatercorecommon.so').read_bytes();assert sha256(b).hexdigest()==pin
    g=Guest(b);vectors=json.loads((HERE/'cbc-vector-results.json').read_bytes());m=json.loads((FW/'fx3-7.02-offline-manifest.json').read_bytes())
    cases=[]
    with (FW/'fx3-7.02-decrypted.fdat').open('rb') as f:
        for row in vectors['samples']:
            i=row['block'];f.seek(i*1020);raw=pack(f.read(row['payload_bytes']),row['last'])
            result=g.call(0xa8e8,raw);assert result['returned']
            size=g.call(0xa8d4,raw)['x0'];end=g.call(0xa8c8,raw)['x0']
            assert size==row['payload_bytes'] and end==int(row['last'])
            cases.append(dict(label='official_plain_block',block=i,accepted=True,size=size,end=end,result=result))
            changed=bytearray(raw);changed[100]^=1
            result=g.call(0xa8e8,bytes(changed));assert result['exception']['code']=='0x30002'
            cases.append(dict(label='checksum_corruption',block=i,accepted=False,result=result))
    for flags in [0,1021,0x1001,0x2001,0x4001]:
        tail=struct.pack('<H',flags)+b'\xff'*1020
        raw=struct.pack('<H',sum(struct.unpack('<511H',tail))&0xffff)+tail
        result=g.call(0xa8e8,raw);expected=flags not in [0,1021]
        assert result['returned']==expected
        if not expected:assert result['exception']['code']=='0x30002'
        cases.append(dict(label='isolated_size_and_reserved_bits',flags_raw=hex(flags),accepted=expected,result=result))
    result=dict(status='PASS_ORIGINAL_AP_BLOCK_CHECKER_WITH_EXPLICIT_THROW_BOUNDARY',source_sha256=pin,
                source_library='libraries/libupdatercorecommon.so',helper_span=['0xa8a0','0xa9c0'],cases=cases,
                original_instructions=g.instructions,
                scope='Original AP helper only: size getter masks 0x0fff, end getter tests bit 15, checksum includes all other header bits. This helper accepting reserved bits is not whole update admission. No CBC decrypt, tail verification, exception unwinding, hardware or camera execution.')
    (HERE/'original-block-checker-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'cases',len(cases),'original instructions',g.instructions)


if __name__=='__main__':main()
