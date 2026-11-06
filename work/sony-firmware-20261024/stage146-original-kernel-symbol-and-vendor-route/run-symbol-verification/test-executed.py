#!/usr/bin/env python3
"""Cross-check two independent original tables and a leaf original guest function."""
from pathlib import Path
from hashlib import sha256
import json
import struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_MEM_WRITE,UC_HOOK_INTR
from unicorn import arm64_const as reg
from kernel_symbols import KernelSymbols,K

HERE=Path(__file__).resolve().parent
OUT=0x10000040
RETURN=0x60000000


def main():
    image=KernelSymbols();exports=[];groups=[]
    for suffix in ('','_gpl','_gpl_future','_unused','_unused_gpl'):
        lo=image.unique('__start___ksymtab'+suffix)['file_offset']
        hi=image.unique('__stop___ksymtab'+suffix)['file_offset']
        assert 0<=lo<=hi<=len(image.raw) and (hi-lo)%16==0
        names=[]
        for at in range(lo,hi,16):
            address,pointer=struct.unpack_from('<QQ',image.raw,at);offset=pointer-K
            assert 0<=offset<len(image.raw)
            end=image.raw.find(b'\0',offset,offset+160);assert end>=0
            name=image.raw[offset:end].decode('ascii')
            matches=[r for r in image.by_name.get(name,[]) if r['address']==address]
            assert matches,(suffix,hex(at),name,hex(address))
            exports.append({'group':suffix or 'ordinary','entry_offset':at,'name':name,'address':address})
            names.append(name)
        assert names==sorted(names)
        groups.append({'group':suffix or 'ordinary','start_offset':lo,'end_offset':hi,'entries':len(names)})
    original=json.loads((HERE.parent/'stage145-initial-MSC-native-route/native-kernel-usb-exports.json').read_text())
    for record in original['exports']:
        row=image.unique(record['name']);assert row['address']==int(record['address'],16) and row['file_offset']==int(record['file_offset'],16)
    uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    uc.mem_map(K,(len(image.raw)+4095)&~4095);uc.mem_write(K,image.raw)
    uc.mem_map(0x10000000,0x1000);uc.mem_map(0x20000000,0x1000);uc.mem_map(RETURN,0x1000)
    original_function=image.unique('kallsyms_expand_symbol.constprop.1')['address']
    guard=bytes([0xc7])*32
    def wrote(machine,access,address,size,value,user):
        assert OUT<=address and address+size<=OUT+128,('guest write outside output',hex(address),size)
    def interrupted(machine,number,user):raise AssertionError(('guest interrupt denied',number))
    uc.hook_add(UC_HOOK_MEM_WRITE,wrote);uc.hook_add(UC_HOOK_INTR,interrupted)
    indices={(image.count-1)*n//999 for n in range(1000)}
    chosen=['delayed_setup_thread','kallsyms_lookup_name','kallsyms_on_each_symbol',
            'usb_gadgetcore_stop_other_driver','usb_gadgetcore_register_driver','usb_gadgetcore_unregister_driver']
    indices.update(image.unique(name)['index'] for name in chosen)
    indices.add(max(image.rows,key=lambda r:len(r['name']))['index'])
    checked=[]
    for index in sorted(indices):
        row=image.rows[index]
        uc.mem_write(OUT-32,guard+bytes([0xa5])*128+guard)
        uc.reg_write(reg.UC_ARM64_REG_X0,row['compressed_offset'])
        uc.reg_write(reg.UC_ARM64_REG_X1,OUT);uc.reg_write(reg.UC_ARM64_REG_X30,RETURN)
        uc.reg_write(reg.UC_ARM64_REG_SP,0x20000f00)
        saved={n:0xabcd0000+n for n in range(19,30)}
        for n,value in saved.items():uc.reg_write(getattr(reg,'UC_ARM64_REG_X'+str(n)),value)
        uc.emu_start(original_function,RETURN,timeout=1000000,count=20000)
        assert uc.reg_read(reg.UC_ARM64_REG_PC)==RETURN
        assert uc.reg_read(reg.UC_ARM64_REG_X0)==row['compressed_next']
        actual=bytes(uc.mem_read(OUT,128)).split(b'\0',1)[0].decode('ascii')
        assert actual==row['name'][:127],(index,actual,row['name'])
        assert bytes(uc.mem_read(OUT-32,32))==guard and bytes(uc.mem_read(OUT+128,32))==guard
        assert uc.reg_read(reg.UC_ARM64_REG_SP)==0x20000f00
        for n,value in saved.items():assert uc.reg_read(getattr(reg,'UC_ARM64_REG_X'+str(n)))==value
        checked.append({'index':index,'name':row['name'],'original_return_next':row['compressed_next'],
                        'name_and_next_offset_match':True,'output_guards_SP_and_callee_saved_match':True})
    output=HERE/'run-symbol-verification';output.mkdir(exist_ok=False)
    (output/'parser-executed.py').write_bytes((HERE/'kernel_symbols.py').read_bytes())
    (output/'test-executed.py').write_bytes(Path(__file__).read_bytes())
    with (output/'export-crosscheck.json').open('x') as f:json.dump(exports,f,separators=(',',':'));f.write('\n')
    result={'status':'PASS_ORIGINAL_EXPORT_PAIRS_AND_SAMPLED_ORIGINAL_NAME_EXPANSION_NOT_KERNEL_BOOT',
        'recovered_symbols':image.count,'original_export_entries':len(exports),'export_groups':groups,
        'original_leaf_guest_calls':len(checked),'original_leaf_cases':checked,
        'original_kernel_global_state_initialization_or_execution_beyond_name_expansion':False,
        'no_native_kernel_Host_USB_or_camera_execution':True,
        'parser_sha256':sha256((HERE/'kernel_symbols.py').read_bytes()).hexdigest(),
        'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'all_41269_names_guest_executed':False}
    assert len(exports)==6089
    with (output/'results.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'recovered_symbols':image.count,'original_export_pairs':len(exports),
                      'original_leaf_guest_calls':len(checked),'new_USB_or_camera_operations':0}))


if __name__=='__main__':main()
