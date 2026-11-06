#!/usr/bin/env python3
"""Persist symbol metadata and selected original spans; no native execution."""
from pathlib import Path
from hashlib import sha256
import json
import re
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from kernel_symbols import KernelSymbols,K,KERNEL_SHA256

HERE=Path(__file__).resolve().parent


def main():
    image=KernelSymbols()
    names=['kallsyms_lookup_name','kallsyms_on_each_symbol','kallsyms_expand_symbol',
           'setup_vendor_specific','delayed_setup_req','usb_gadgetcore_stop_other_driver',
           'usb_gadgetcore_register_driver','usb_gadgetcore_unregister_driver']
    selected={name:image.by_name.get(name,[]) for name in names}
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);spans=[]
    for name in names:
        start,end=image.span(name)
        assert end-start<=0x4000
        rows=[]
        for ins in md.disasm(image.raw[start:end],K+start):
            rows.append({'pc':hex(ins.address),'file_offset':hex(ins.address-K),'bytes':ins.bytes.hex(),
                         'asm':ins.mnemonic+' '+ins.op_str})
        spans.append({'name':name,'start_offset':start,'next_symbol_offset':end,
                      'bytes':end-start,'sha256':sha256(image.raw[start:end]).hexdigest(),
                      'inferred_next_symbol_span_not_ELF_function_size':True,'instructions':rows})
    catalog=HERE/'work/kernel-symbol-catalog.json'
    with catalog.open('x') as f:json.dump(image.rows,f,ensure_ascii=False,separators=(',',':'));f.write('\n')
    relevant=[x for x in image.rows if re.search('nin_|senser|auth|sha1|sha256',x['name'],re.I)]
    result={'status':'ORIGINAL_702_COMPRESSED_KERNEL_SYMBOLS_RECOVERED_NOT_EXECUTION_OR_DEVICE_STATE',
            'original_kernel_sha256':KERNEL_SHA256,'kernel_base':hex(K),'tables':image.tables,
            'symbol_count':image.count,'compressed_names_end':image.names_end,
            'selected':selected,'selected_spans':spans,'related_symbol_names':relevant,
            'catalog_sha256':sha256(catalog.read_bytes()).hexdigest(),
            'parser_sha256':sha256((HERE/'kernel_symbols.py').read_bytes()).hexdigest(),
            'original_kernel_or_camera_execution':False}
    with (HERE/'kernel-symbol-recovery.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'symbol_count':image.count,'tables':image.tables,
                      'selected':selected,'related_symbol_names':[x['name'] for x in relevant][:100]}))


if __name__=='__main__':main()
