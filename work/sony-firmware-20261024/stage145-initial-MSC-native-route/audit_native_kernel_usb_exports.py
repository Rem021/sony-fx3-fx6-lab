#!/usr/bin/env python3
"""Recover exact-name static export candidates from the original kernel Image."""
from pathlib import Path
from hashlib import sha256
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
import json
import re
import struct

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
K=0xffffff8008080000


def candidates(kernel,name):
    result=[];cursor=0;needle=b'\0'+name.encode()+b'\0'
    while True:
        at=kernel.find(needle,cursor)
        if at<0:break
        off=at+1;cursor=off+len(name);pointer=K+off;start=0
        while True:
            ref=kernel.find(struct.pack('<Q',pointer),start)
            if ref<0:break
            start=ref+1;entry=ref-8
            if entry<16 or entry%8 or ref+24>len(kernel):continue
            neighbors=[]
            for row in (entry-16,entry,entry+16):
                value,ptr=struct.unpack_from('<QQ',kernel,row);where=ptr-K
                if not 0<=where<len(kernel):break
                end=kernel.find(b'\0',where,where+160)
                if end<0:break
                label=kernel[where:end]
                if not re.fullmatch(rb'[A-Za-z_][A-Za-z_0-9]*',label) or not K<=value<K+0x10000000:break
                neighbors.append({'name':label.decode(),'value':hex(value),'entry_offset':hex(row)})
            if len(neighbors)!=3 or [x['name'] for x in neighbors]!=sorted(x['name'] for x in neighbors):continue
            if neighbors[1]['name']!=name:continue
            result.append({'address':int(neighbors[1]['value'],16),'neighbors':neighbors})
    return result


def main():
    path=BASE/'stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin'
    raw=path.read_bytes();assert sha256(raw).hexdigest()=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
    rows=[];md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    for name in ['usb_gadgetcore_stop_other_driver','usb_gadgetcore_register_driver','usb_gadgetcore_unregister_driver']:
        found=candidates(raw,name);assert len(found)==1,(name,len(found))
        entry=found[0];address=entry['address'];offset=address-K
        assert 0<=offset and offset+0x120<=len(raw)
        rows.append({'name':name,'address':hex(address),'file_offset':hex(offset),'export_neighbors':entry['neighbors'],
                     'prefix_bytes':0x120,'prefix_sha256':sha256(raw[offset:offset+0x120]).hexdigest(),
                     'prefix_not_complete_function_or_execution':[{'pc':hex(i.address),'asm':i.mnemonic+' '+i.op_str}
                         for i in md.disasm(raw[offset:offset+0x120],address)]})
    result={'status':'ORIGINAL_702_KERNEL_USB_EXPORT_CANDIDATES_AND_PREFIXES_NOT_FULL_DISPATCHER_PROOF',
        'kernel_path':path.relative_to(ROOT).as_posix(),'kernel_sha256':sha256(raw).hexdigest(),
        'kernel_base_reference':hex(K),'exports':rows,'setup_vendor_specific_static_function_not_recovered':True,
        'original_kernel_executed_or_camera_access':False}
    with (HERE/'native-kernel-usb-exports.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'exports':[{'name':r['name'],'address':r['address'],'file_offset':r['file_offset']} for r in rows],
                      'new_device_operations':0}))


if __name__=='__main__':main()
