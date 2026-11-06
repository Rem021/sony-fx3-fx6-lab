#!/usr/bin/env python3
"""Read-only SHA-pinned audit of fixed FX3 /init lines 79..115 under FX6 Image."""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
EARLY=HERE.parent
ROOT=HERE.parents[7]
sys.path.insert(0,str(EARLY))
sys.path.insert(0,str(EARLY.parent))
from audit_software_gate import selected_cpio_members
from elf64 import ELF64

RUNTIME=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability'
HELPERS=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers'
RUN=EARLY/'runs/fixed-fx3-c72ee0b9'
PINS={
 'cpio_audit':(RUNTIME/'vmopt-20261103-try2-long-media-gap-v2/cpio-audit.json','cc0b3c5b1925aa4bb0cb14aab275f2831833c7378490ca5408789f3824eb4847'),
 'candidate':(EARLY/'fixed-kernel-candidate.json','42cddf844eb37a4712feb59a0c595ab9746eee21b37b210a7f81741bdb16797c'),
 'run_receipt':(RUN/'run-receipt.json','c37ad1d014d90fd3311722eec1ff025468aeeccc1001d91456bd06cf6b278ceb'),
 'run_serial':(RUN/'serial.log','034552e396f4dbd49aa55e85fb931272d009e41cf7c0a413d85b373b9c7b8536'),
 'ldec_build':(HELPERS/'fx3-ldec-soft103-v1-build.json','2cb966171e77ca33360feb0d1658e6a7af8430530cdf32de4a9630400701b329'),
 'ldec_source':(HELPERS/'fx3-ldec-soft103-v1.c','6c026aeb7231801f196af93524248d4c515f2a69788a3e3485b8b90d1ed35c9d'),
 'ldec_unit':(HELPERS/'fx3-ldec-soft103-v1-module-unit.c','bf154834ecf29a72143bc8b93e4695594f0c4857308892ba92bb2bef43ee6745'),
 'ldec_decoder':(ROOT/'work/fx3-vm-20261101/lead-claude/impl/ldec-lz77/ldec_soft.c','10eacafe48b4d3c6ff3afcde507619e394294cdf8324dc5e0c7af9d1fd233780'),
 'ldec_test_build':(HELPERS/'fx3-ldec-ioctl103-test-v2-build.json','c4bd12cab476458974d595425cd6ca52c7e94bd32c0aa1d2dd4bfed738942d94'),
 'ldec_test_source':(HELPERS/'fx3-ldec-ioctl103-test-v2.c','c00720368f0dee921a6cd07a30ed870a29d70a1500c8b705581d20ded0d1d7ff'),
 'file_observer_build':(HELPERS/'fx3-file100-observer-v2-build.json','fe7635a2958b2c664c531f14c62258eb6f7d5f779c640ab6c5cd87b3d943b343'),
 'file_observer_source':(HELPERS/'fx3-file100-observer-v2.c','288f6946cbd43dd4a8bf82aa5b71dca3a93d9626ba2456202161e3e394bcb9f6'),
 'devno_module':(ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/payloads/cca1d9acd87a718c7742d168ea0de402b01a7c04cd40433ff2ca4071150dbc23','cca1d9acd87a718c7742d168ea0de402b01a7c04cd40433ff2ca4071150dbc23'),
}
GUEST={
 'simulation/fx3-ldec-soft103-v1.ko':('fx3-ldec-soft103-v1.ko','ldec_build'),
 'simulation/fx3-ldec-ioctl103-test-v2':('fx3-ldec-ioctl103-test-v2','ldec_test_build'),
 'simulation/fx3-file100-observer-v2':('fx3-file100-observer-v2','file_observer_build'),
 'simulation/fx3-cp-backup-reset-v1.ko':('fx3-cp-backup-v5-native101.ko',None),
}

def sha(data):return hashlib.sha256(data).hexdigest()

def fdt_reservations(data):
    if len(data)<40 or struct.unpack_from('>I',data)[0]!=0xd00dfeed:raise ValueError('FDT magic')
    total,off=struct.unpack_from('>II',data,4)[0],struct.unpack_from('>I',data,16)[0]
    if total>len(data) or off<40 or off>=total:raise ValueError('FDT bounds')
    rows=[]
    while off+16<=total:
        start,size=struct.unpack_from('>QQ',data,off);off+=16
        if start==size==0:return rows
        if size==0:raise ValueError('empty FDT reservation')
        rows.append((start,size))
    raise ValueError('FDT reservation terminator missing')

def reloc_at(elf,section,offset):
    rel=elf.byname['.rela'+section];symtab=elf.sections[rel['link']]
    names=elf.section_bytes(symtab['link']);hits=[]
    for at in range(rel['offset'],rel['offset']+rel['size'],rel['entsize']):
        loc,info,addend=struct.unpack_from('<QQq',elf.data,at)
        if loc!=offset:continue
        index,kind=info>>32,info&0xffffffff
        sym_off=symtab['offset']+index*symtab['entsize']
        name_off,_,_,shndx=struct.unpack_from('<IBBH',elf.data,sym_off)
        hits.append({'type':kind,'symbol':elf.cstr(names,name_off),'symbol_section':elf.sections[shndx]['name'] if shndx<len(elf.sections) else None,'addend':addend})
    if len(hits)!=1:raise ValueError('relocation missing/ambiguous '+section+'+'+hex(offset))
    return hits[0]

def main():
    for name,(path,pin) in PINS.items():
        if sha(path.read_bytes())!=pin:raise ValueError('changed input '+name)
    candidate=json.loads(PINS['candidate'][0].read_text())
    assert candidate['platform_changes']==[] and candidate['firmware_payload_changes'][0]['to_sha256']=='bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9'
    receipt=json.loads(PINS['run_receipt'][0].read_text())
    serial=PINS['run_serial'][0].read_text(errors='replace')
    positive=[f'FX3_INSMOD_RC_{name}=0' for name in ('/kmod/devno.ko','/usr/kmod/osal_utm.ko','/usr/kmod/osal_uipc.ko')]
    if receipt['manifest_sha256']!='42cddf844eb37a4712feb59a0c595ab9746eee21b37b210a7f81741bdb16797c' or receipt['reason']!='original_devno_insmod_rc' or any(line not in serial.splitlines() for line in positive) or 'FX3_UIPC_ORIGINAL_NODE_PRESENT' in serial:
        raise ValueError('new runtime boundary differs')
    audit=json.loads(PINS['cpio_audit'][0].read_text());lines=audit['init_text'].splitlines()
    if 'FX3_PROC_MODULES_BEGIN' not in lines[78] or 'FX3_LDEC103_INIT_BEGIN' not in lines[87] or 'fx3-ldec-soft103-v1.ko' not in lines[88] or 'fx3-ldec-ioctl103-test-v2' not in lines[94] or 'fx3-file100-observer-v2' not in lines[98] or 'fx3-cp-backup-reset-v1.ko' not in lines[114]:
        raise ValueError('init route shifted')
    names=list(GUEST)+['simulation/fx3-sync100-shutdown.sh']
    cpio=candidate['unchanged_full_binary_sha256']['software_guest_cpio']
    cpio_path=Path(cpio['path']);assert sha(cpio_path.read_bytes())==cpio['sha256']
    blobs=selected_cpio_members(cpio_path,names)
    entries={v['path']:v for v in audit['members']}
    guest={}
    for name,(local,build_name) in GUEST.items():
        blob=blobs[name];digest=sha(blob)
        if digest!=entries[name]['sha256'] or digest!=sha((HELPERS/local).read_bytes()):raise ValueError('CPIO/local binary identity '+name)
        if build_name:
            build=json.loads(PINS[build_name][0].read_text())
            source_pin=PINS[{'ldec_build':'ldec_source','ldec_test_build':'ldec_test_source','file_observer_build':'file_observer_source'}[build_name]][1]
            if build['exit']!=0 or build['source_sha256']!=source_pin or build['output_sha256']!=digest:raise ValueError('build/source/output closure '+name)
        elf=ELF64(HELPERS/local)
        if elf.machine!=183 or elf.etype not in (1,2,3):raise ValueError('guest AArch64 ELF type '+name)
        imports=sorted({s['name'] for s in elf.symbols() if s['name'] and s['shndx']==0 and s['bind']!=0})
        guest[name]={'sha256':digest,'bytes':len(blob),'elf_machine':elf.machine,'elf_type':elf.etype,'undefined_symbols':imports,'kernel_text_patch_imports':[n for n in imports if n in ('aarch64_insn_patch_text','probe_kernel_write','text_poke','set_memory_rw')],'runtime_result':'UNTESTED'}
    if sha(blobs['simulation/fx3-sync100-shutdown.sh'])!=entries['simulation/fx3-sync100-shutdown.sh']['sha256']:
        raise ValueError('shutdown script changed')
    for key in ('ldec_source','ldec_decoder','ldec_test_source','file_observer_source'):
        source=PINS[key][0].read_text()
        if re.search(r'0xffffff8[0-9a-fA-F]{9}',source) or re.search(r'aarch64_insn_patch_text|probe_kernel_write|text_poke',source):
            raise ValueError('old kernel address/patch in pre-CP source '+key)
    if '#include "fx3-ldec-soft103-v1.c"' not in PINS['ldec_unit'][0].read_text() or 'ldec_soft.c' not in PINS['ldec_source'][0].read_text():raise ValueError('ldec build source chain')
    ldec=ELF64(HELPERS/'fx3-ldec-soft103-v1.ko')
    ldec_init=next(s for s in ldec.symbols() if s['name']=='init_module')
    if ldec_init['value']!=0x4e8 or ldec_init['size']!=296 or reloc_at(ldec,'.text',0x4e8)['symbol']!='udif_devnodes' or reloc_at(ldec,'.text',0x5c4)['symbol']!='udif_cdev_register':
        raise ValueError('LDEC init symbol/registration edge changed')
    dev=ELF64(PINS['devno_module'][0]);sym=next(s for s in dev.symbols() if s['name']=='udif_devnodes')
    if sym['size']!=1088 or sym['value']!=0:raise ValueError('devno table layout')
    dev_row=dev.section_bytes(dev.sections[sym['shndx']]['name'])[5*16:6*16]
    if dev_row.hex()!='00000000000000000000fb00cd000100':raise ValueError('devno ldec row changed')
    name_data=dev.section_bytes('.rodata.str1.8')
    if name_data[0x48:0x4d]!=b'ldec\0':raise ValueError('devno ldec name changed')
    name_link=reloc_at(dev,'.data',0x50)
    if name_link['type']!=257 or name_link['symbol_section']!='.rodata.str1.8' or name_link['addend']!=0x48:
        raise ValueError('devno row5 name pointer changed')
    fdt=candidate['unchanged_full_binary_sha256']['fx3_dtb_full_binary']
    data=Path(fdt['path']).read_bytes()
    if sha(data)!=fdt['sha256']:raise ValueError('guest DTB changed')
    reserves=fdt_reservations(data)
    needed=[(0x41d300000,0x100000),(0x41d400000,0x300000)]
    if not all(x in reserves for x in needed):raise ValueError('pre-CP reserved spans absent')
    source=PINS['file_observer_source'][0].read_text()
    if 'for(U i=0;i<4096;i++)out[i]=0' not in source or 'if(h[6]==0x100c1ea9UL&&!stopped)' not in source or 'system("/bin/sh /simulation/fx3-sync100-shutdown.sh")' not in source:
        raise ValueError('observer dormant shutdown condition changed')
    return {'status':'PASS_STATIC_PRE_CP_ROUTE_WITH_RUNTIME_FIRST_ORIGINAL_MODULES_ONLY','pinned_inputs':{k:{'path':str(v[0]),'sha256':v[1]} for k,v in PINS.items()},'fixed_cpio':cpio,'fixed_guest_dtb':fdt,'runtime_observed':{'receipt_sha256':PINS['run_receipt'][1],'serial_sha256':PINS['run_serial'][1],'original_insmod_rc_zero':positive,'next_first_unverified_condition':'/init line 86 -c /dev/uipc; no node/present marker in captured serial','simulation_executed':False},'reviewed_init_lines':[79,118],'guest_programs':guest,'ldec_init_linkage':{'function_text_offset':'0x4e8','function_file_offset':hex(ldec.byname['.text']['offset']+0x4e8),'devno_table_relocation':'.text+0x4e8 R_AARCH64_MOVW_UABS_G0_NC udif_devnodes','registration_call_relocation':'.text+0x5c4 R_AARCH64_CALL26 udif_cdev_register'},'devno_ldec_row':{'module_sha256':PINS['devno_module'][1],'symbol':'udif_devnodes','row_index':5,'row_file_offset':hex(dev.byname['.data']['offset']+5*16),'row_hex':dev_row.hex(),'name_relocation_rodata_offset':'0x48','name':'ldec','type':0,'major':251,'minor':205,'count':1},'pre_cp_physical_writes':{'ldec_test':{'start':'0x41d300000','size':'0x100000','fixed_dtb_reserved':True,'conditions':'guest test opens /dev/mem and /dev/ldec; module validates destination p32 and arch conversion, writes only after full decode and readback rollback'},'file100_observer':{'start':'0x41d400000','size':'0x300000','fixed_dtb_reserved':True,'conditions':'read-only /setting/Backup.bin; private observer span initialized and payload copied within CAP=0x230000; shutdown shell only after external magic at h[6]'}} ,'old_fx3_kernel_absolute_address_or_text_patch_in_verified_source':False,'kernel_export_implementation_and_runtime_mapping_fully_verified':False,'cp_helper_known_refusal_gate_preserved':True,'pre_cp_guest_execution_observed':False,'host_only_next_observation':'stop at first completed negative marker or CP helper insmod RC; if unexpected positive CP RC, stop before AP and flag guard; serial polling is not a CPU breakpoint'}

if __name__=='__main__':
    result=main();(HERE/'pre-cp-audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'status':result['status'],'guest_programs':len(result['guest_programs']),'first_unknown':result['runtime_observed']['next_first_unverified_condition']},indent=2))
