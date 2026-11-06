#!/usr/bin/env python3
"""Independent FX6 __ksymtab/export and bounded original name-expansion checks."""
from hashlib import sha256
import json
import struct

from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_MEM_WRITE, UC_HOOK_INTR
from unicorn import arm64_const as R

from kernel_symbols import HERE, KernelSymbols

OUT=0x10000040
STOP=0x60000000


def main():
    image=KernelSymbols();exports=[];groups=[]
    for suffix in ('','_gpl','_gpl_future','_unused','_unused_gpl'):
        lo=image.unique('__start___ksymtab'+suffix)['file_offset']
        hi=image.unique('__stop___ksymtab'+suffix)['file_offset']
        assert 0<=lo<=hi<=len(image.raw) and (hi-lo)%16==0
        names=[]
        for at in range(lo,hi,16):
            address,pointer=struct.unpack_from('<QQ',image.raw,at)
            off=pointer-image.base
            assert 0<=off<len(image.raw)
            end=image.raw.find(b'\0',off,off+160);assert end>=0
            name=image.raw[off:end].decode('ascii')
            matches=[row for row in image.by_name.get(name,[]) if row['address']==address]
            assert matches,(suffix,hex(at),name,hex(address))
            exports.append({'group':suffix or 'ordinary','file_offset':hex(at),
                            'name':name,'address':hex(address)})
            names.append(name)
        assert names==sorted(names)
        groups.append({'name':suffix or 'ordinary','start_file_offset':hex(lo),
                       'stop_file_offset':hex(hi),'entries':len(names)})
    # Only fixed original ARM64 bytes execute.  All writes are bounded to host output.
    uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    uc.mem_map(image.base,(len(image.raw)+4095)&~4095);uc.mem_write(image.base,image.raw)
    uc.mem_map(0x10000000,0x1000);uc.mem_map(0x20000000,0x1000);uc.mem_map(STOP,0x1000)
    entry=image.unique('kallsyms_expand_symbol.constprop.1')['address']
    writes=[]
    def write(machine,access,address,size,value,user):
        assert OUT<=address and address+size<=OUT+128,('unexpected guest write',hex(address),size)
        writes.append({'address':hex(address),'size':size})
    def intr(machine,number,user):raise AssertionError(('guest interrupt',number))
    uc.hook_add(UC_HOOK_MEM_WRITE,write);uc.hook_add(UC_HOOK_INTR,intr)
    indices={(image.count-1)*n//999 for n in range(1000)}
    for name in ('kallsyms_expand_symbol.constprop.1','kallsyms_lookup_name',
                 'SyS_init_module','load_module','apply_relocate_add','module_finalize'):
        indices.add(image.unique(name)['index'])
    indices.add(max(image.rows,key=lambda r:len(r['name']))['index'])
    checked=[];guard=b'\xc7'*32
    for index in sorted(indices):
        row=image.rows[index]
        uc.mem_write(OUT-32,guard+b'\xa5'*128+guard)
        uc.reg_write(R.UC_ARM64_REG_X0,row['compressed_offset'])
        uc.reg_write(R.UC_ARM64_REG_X1,OUT)
        uc.reg_write(R.UC_ARM64_REG_LR,STOP)
        uc.reg_write(R.UC_ARM64_REG_SP,0x20000f00)
        saved={n:0xabcd0000+n for n in range(19,30)}
        for n,v in saved.items():uc.reg_write(getattr(R,'UC_ARM64_REG_X'+str(n)),v)
        before=len(writes)
        uc.emu_start(entry,STOP,timeout=1000000,count=20000)
        assert uc.reg_read(R.UC_ARM64_REG_PC)==STOP
        assert uc.reg_read(R.UC_ARM64_REG_X0)==row['compressed_next']
        got=bytes(uc.mem_read(OUT,128)).split(b'\0',1)[0].decode('ascii')
        assert got==row['name'][:127],(index,got,row['name'])
        assert bytes(uc.mem_read(OUT-32,32))==guard and bytes(uc.mem_read(OUT+128,32))==guard
        assert uc.reg_read(R.UC_ARM64_REG_SP)==0x20000f00
        assert all(uc.reg_read(getattr(R,'UC_ARM64_REG_X'+str(n)))==v for n,v in saved.items())
        checked.append({'index':index,'name':row['name'],'original_return_next':row['compressed_next'],
                        'bounded_output_writes':len(writes)-before})
    (HERE/'export-crosscheck.json').write_text(json.dumps(exports,separators=(',',':'))+'\n')
    result={'status':'PASS_FX6_ORIGINAL_EXPORT_PAIRS_AND_ORIGINAL_NAME_EXPANSION',
            'kernel_sha256':image.raw and sha256(image.raw).hexdigest(),
            'symbols':image.count,'export_entries':len(exports),'export_groups':groups,
            'guest_original_calls':len(checked),'guest_cases':checked,
            'export_sha256':sha256((HERE/'export-crosscheck.json').read_bytes()).hexdigest(),
            'kernel_boot_or_provider_execution':False}
    (HERE/'symbol-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'symbols':image.count,'exports':len(exports),'original_guest_cases':len(checked),'status':'PASS'}))


if __name__=='__main__':main()
