#!/usr/bin/env python3
"""Build a small, deterministic FX6 early-kernel CPIO and virt DTB; never boot."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[6]
DONOR=HERE.parents[1]
VM=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2'
FDT_TOOL=ROOT/'work/fx3-vm-20261101/fx3-audit/prepare_virt_dtb.py'
LIB= DONOR/'nested-files/nflasha3-initrd/lib'
SOURCE={
 'fx6_image':(DONOR/'fat-files/nflasha3/vmlinux.bin','bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9'),
 'virt_dtb':(VM/'guest.dtb','b6f9f4c04d0da101565d67244629a0ad7a3954c8af004f353c16ae0c8b499de7'),
 'qemu':(ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/qemu-display-build/bin/qemu-gpio5-bf4d46481998b8fb','bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d'),
 'busybox':(DONOR/'nested-files/nflasha3-initrd/bin/busybox','a306367cd67674b1d1a03464b24fbe8137a8ea8f630817e7733a054f761d0c6d'),
 'ld':(LIB/'ld-2.25.so','8eeed290e0992ef3717e61450831a3b1e25e9bff11e5062204cc0dc96a617a75'),
 'libc':(LIB/'libc-2.25.so','4ecddf81915c4e03d9815eade4e626363616618be7f70aabfa467d52cb0348fd'),
 'libcrypt':(LIB/'libcrypt-2.25.so','969fbcbc967305d69c32c1059fd76b1f2ca5118eef5da37fdc66f8d3069f3dc2'),
 'fdt_encoder':(FDT_TOOL,'ce65e3851c5e00f2167b8c8cd98a3109dd456f45f438194d365b6090a3141941'),
}
INIT=b'''#!/bin/sh
echo FX6_EARLY_INIT_REACHED
/bin/busybox uname -a
/bin/busybox mount -t proc proc /proc
echo FX6_EARLY_PROC_MOUNT_RC=$?
/bin/busybox mount -t sysfs sysfs /sys
echo FX6_EARLY_SYS_MOUNT_RC=$?
echo FX6_EARLY_INIT_HOLD
while :; do /bin/busybox sleep 10; done
'''
BOOTARGS='console=ttyAMA0 earlycon=pl011,0x09000000 rdinit=/init init=/init nokaslr ignore_loglevel loglevel=8 panic=-1'
INITRD_ADDR=0x440000000
DTB_ADDR=0x400002000


def sha(b):return hashlib.sha256(b).hexdigest()


def source_bytes():
    result={}
    for key,(path,expected) in SOURCE.items():
        if not path.is_file() or path.is_symlink():raise ValueError(f'missing or symlink source {path}')
        data=path.read_bytes()
        if sha(data)!=expected:raise ValueError(f'{key} SHA mismatch')
        result[key]=data
    return result


def newc(entries):
    out=bytearray()
    metadata=[]
    for ino,(name,mode,data,major,minor) in enumerate(entries,1):
        n=name.encode()+b'\0'
        fields=(ino,mode,0,0,2 if mode&0o170000==0o040000 else 1,0,len(data),0,0,major,minor,len(n),0)
        out.extend(b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)+n)
        out.extend(b'\0'*((-len(out))%4))
        off=len(out)
        out.extend(data)
        out.extend(b'\0'*((-len(out))%4))
        metadata.append({'path':name,'mode':oct(mode),'data_offset':off,'size':len(data),'sha256':sha(data) if data else None,'rdev':[major,minor]})
    name=b'TRAILER!!!\0';fields=(0,0,0,0,1,0,0,0,0,0,0,len(name),0)
    out.extend(b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)+name)
    out.extend(b'\0'*((-len(out))%4))
    return bytes(out),metadata


def main():
    b=source_bytes()
    spec=importlib.util.spec_from_file_location('pinned_fdt_encoder',FDT_TOOL)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    entries=[
      ('bin',0o040755,b'',0,0),('lib',0o040755,b'',0,0),('proc',0o040755,b'',0,0),('sys',0o040755,b'',0,0),('dev',0o040755,b'',0,0),
      ('init',0o100755,INIT,0,0),('bin/busybox',0o100755,b['busybox'],0,0),('bin/sh',0o120777,b'busybox',0,0),
      ('lib/ld-2.25.so',0o100755,b['ld'],0,0),('lib/ld-linux-aarch64.so.1',0o120777,b'ld-2.25.so',0,0),
      ('lib/libc-2.25.so',0o100644,b['libc'],0,0),('lib/libc.so.6',0o120777,b'libc-2.25.so',0,0),
      ('lib/libcrypt-2.25.so',0o100644,b['libcrypt'],0,0),('lib/libcrypt.so.1',0o120777,b'libcrypt-2.25.so',0,0),
      ('dev/console',0o020600,b'',5,1),('dev/null',0o020666,b'',1,3),
    ]
    cp,files=newc(entries)
    if len(cp)>=128*1024*1024:raise ValueError('initrd too large')
    root,before,reserve,meta=mod.parse(b['virt_dtb'])
    chosen=next(x for kind,x in root['items'] if kind=='node' and x['name']=='chosen')
    replacements={'bootargs':BOOTARGS.encode()+b'\0','linux,initrd-start':struct.pack('>Q',INITRD_ADDR),'linux,initrd-end':struct.pack('>Q',INITRD_ADDR+len(cp))}
    chosen['items']=[(kind,item) if not(kind=='prop' and item[0] in replacements) else ('prop',(item[0],replacements[item[0]])) for kind,item in chosen['items']]
    dt=mod.encode(root,reserve,meta)
    _,after,reserve2,meta2=mod.parse(dt)
    diff={key for key in set(before)|set(after) if before.get(key)!=after.get(key)}
    if diff!={('/chosen','bootargs'),('/chosen','linux,initrd-end')} or reserve!=reserve2 or meta['nodes']!=meta2['nodes'] or any(after[('/chosen',k)]!=v for k,v in replacements.items()):
        raise ValueError('DTB modification outside chosen bootargs/initrd-end')
    cp_path=HERE/'minimal-initrd.cpio';dt_path=HERE/'fx6-virt-early.dtb'
    cp_path.write_bytes(cp);dt_path.write_bytes(dt)
    record={'status':'BUILT_OFFLINE_NOT_BOOTED','source':{k:{'path':str(SOURCE[k][0]),'sha256':sha(v),'bytes':len(v)} for k,v in b.items()},'artifacts':{'initrd':{'path':str(cp_path),'sha256':sha(cp),'bytes':len(cp),'members':files},'dtb':{'path':str(dt_path),'sha256':sha(dt),'bytes':len(dt),'parent_sha256':sha(b['virt_dtb']),'changed_properties':[list(x) for x in sorted(diff)],'reserve_map_unchanged':True,'nodes_unchanged':True}},'bootargs':BOOTARGS,'initrd_load_address':hex(INITRD_ADDR),'dtb_load_address':hex(DTB_ADDR),'guest_tasks':['console','minimal shell init'],'excluded':['AP','CP','AV','writable disk','camera','USB','SD'],'qemu_started':False}
    (HERE/'build-receipt.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
    candidate={'schema':'fx6-early-kernel-candidate-v1','status':'WITHDRAWN_DO_NOT_RUN_FIXED_FX3_PLATFORM_CONSTRAINT','withdrawn_reason':'User requires the existing FX3 DTB and initrd unchanged; this exploratory candidate changed bootargs, initrd-end and init payload.','image':record['source']['fx6_image'],'qemu':record['source']['qemu'],'dtb':{k:record['artifacts']['dtb'][k] for k in ('path','sha256','bytes')},'initrd':{k:record['artifacts']['initrd'][k] for k in ('path','sha256','bytes')},'bootargs':BOOTARGS,'initrd_load_address':hex(INITRD_ADDR),'dtb_load_address':hex(DTB_ADDR),'machine':'virt,gic-version=2,secure=off','cpu':'cortex-a35','smp':4,'memory_mib':5120,'model_env':{'FX3_VM_ESRAM_RAM':'1','FX3_VM_HIGH_DDR':'1','FX3_VM_SONY_TIMER':'1','FX3_VM_SCU_REQUEST':'1','FX3_VM_GPIO_BANK5':'1'},'maximum_seconds':180,'stop_marker':'FX6_EARLY_INIT_REACHED','boot_result':'UNTESTED'}
    (HERE/'candidate.json').write_text(json.dumps(candidate,indent=2,ensure_ascii=False)+'\n')
    return record


if __name__=='__main__':print(json.dumps(main(),indent=2,ensure_ascii=False))
