#!/usr/bin/env python3
"""Bounded original-byte audit of the fixed CP helper's FX6 kernel contract."""
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[6]
sys.path.insert(0,str(HERE.parent))
from elf64 import ELF64

SOURCES={
 'fx6_image':(HERE.parents[1]/'fat-files/nflasha3/vmlinux.bin','bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9'),
 'fx3_image':(ROOT/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin','da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'),
 'fx6_symbols':(HERE.parents[1]/'kernel-provider-binding/fx6-kernel-symbol-catalog.json','f81602bb6d754eccdd7b2c17af371ee2e03cc01fad86dff3552936bd1f9a6166'),
 'fx3_symbols':(ROOT/'work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/work/kernel-symbol-catalog.json','b37c6b7d4315f65234cd6b64c3be4a3d7c6e0d2cca66204e27cb5c575000a51e'),
 'liro_closure':(HERE/'liro-closure.json','e2c617cdd786c3536eeaca8090ac59b8367abf2e98af8281fa82b9dfbb5cf7a6'),
 'helper_source':(ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-cp-backup-v5-native101.c','b0de532abb5c688f360f46d862abe1c8c1b2114f8448b5e3a91573cd9987b4c0'),
 'helper_sync_header':(ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-backup-sync101-v1.h','6f2116440d17db50f7c35b57f7ab967ce304318a431649a76885c096bd87ee96'),
 'helper_core_header':(ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-cp-backup-reset-core-v2-sync100.h','ffa767cec3bdd7f94fa9aaf985024535f550446a2cd8ec7524fd10dc63701e47'),
 'software_gate':(HERE/'software-first-gate.json',''),
}

def sha(data):return hashlib.sha256(data).hexdigest()

def symbol_extent(symbols,name):
    matches=[i for i,v in enumerate(symbols) if v['name']==name]
    if len(matches)!=1:raise ValueError('symbol missing/ambiguous '+name)
    i=matches[0];v=symbols[i]
    size=symbols[i+1]['address']-v['address']
    if not 0<size<4096:raise ValueError('symbol extent invalid '+name)
    return v,size

def relocation(elf,section_name,offset):
    sec=elf.byname['.rela'+section_name];symtab=elf.sections[sec['link']]
    names=elf.section_bytes(symtab['link']);hits=[]
    for at in range(sec['offset'],sec['offset']+sec['size'],sec['entsize']):
        loc,info,addend=struct.unpack_from('<QQq',elf.data,at)
        if loc!=offset:continue
        idx,kind=info>>32,info&0xffffffff
        sym_off=symtab['offset']+idx*symtab['entsize']
        name_off=struct.unpack_from('<I',elf.data,sym_off)[0]
        hits.append({'type':kind,'symbol':elf.cstr(names,name_off),'addend':addend})
    if len(hits)!=1:raise ValueError('relocation missing/ambiguous')
    return hits[0]

def main():
    for key,(path,digest) in SOURCES.items():
        if digest and sha(path.read_bytes())!=digest:raise ValueError('source changed '+key)
    gate=json.loads(SOURCES['software_gate'][0].read_text())
    if not gate['first_proven_conditional_software_block_if_reached']['module_matches_compiled_local_v5']:
        raise ValueError('compiled helper identity not established')
    closure=json.loads(SOURCES['liro_closure'][0].read_text())
    backup_path=Path(closure['closure_modules']['/usr/kmod/backup.ko']['path'])
    if sha(backup_path.read_bytes())!='8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d':
        raise ValueError('original FX3 Backup module changed')
    backup=ELF64(backup_path)
    caller=[s for s in backup.symbols() if s['name']=='backupfile_get_cp_data' and s['shndx']==backup.byname['.text']['index']]
    if len(caller)!=1 or caller[0]['value']!=0x7030 or caller[0]['size']!=348:
        raise ValueError('original Backup caller symbol changed')
    edge=relocation(backup,'.text',0x70bc)
    if edge!={'type':283,'symbol':'pcidma_transfer_async','addend':0}:
        raise ValueError('original Backup call target changed')
    image={model:SOURCES[model+'_image'][0].read_bytes() for model in ('fx3','fx6')}
    symbols={model:json.loads(SOURCES[model+'_symbols'][0].read_text()) for model in ('fx3','fx6')}
    f={}
    for model in ('fx3','fx6'):
        entry,size=symbol_extent(symbols[model],'pcidma_transfer_async')
        patch,patch_size=symbol_extent(symbols[model],'aarch64_insn_patch_text')
        if size!=0x168 or patch_size!=0xd8:raise ValueError('kernel function size changed')
        body=image[model][entry['file_offset']:entry['file_offset']+size]
        patch_body=image[model][patch['file_offset']:patch['file_offset']+patch_size]
        f[model]={'pcidma_address':hex(entry['address']),'pcidma_file_offset':hex(entry['file_offset']),'pcidma_size':size,'pcidma_sha256':sha(body),'pcidma_first16_hex':body[:16].hex(),'fallback_null_target':hex(entry['address']+0x160),'fallback_nonnul_target':hex(entry['address']+0x10),'patch_text_address':hex(patch['address']),'patch_text_file_offset':hex(patch['file_offset']),'patch_text_size':patch_size,'patch_text_sha256':sha(patch_body)}
    a,b=[image[model][int(f[model]['pcidma_file_offset'],0):int(f[model]['pcidma_file_offset'],0)+0x168] for model in ('fx3','fx6')]
    diffs=[{'offset':hex(i),'fx3_word_le':a[i:i+4].hex(),'fx6_word_le':b[i:i+4].hex()} for i in range(0,0x168,4) if a[i:i+4]!=b[i:i+4]]
    if [d['offset'] for d in diffs]!=['0x68','0xbc','0xd0','0xd8','0x13c']:
        raise ValueError('pcidma full-function difference set changed')
    add_imm=[]
    for off in (0x68,0xbc):
        old_imm=(int.from_bytes(a[off:off+4],'little')>>10)&0xfff
        new_imm=(int.from_bytes(b[off:off+4],'little')>>10)&0xfff
        if (old_imm,new_imm)!=(0xd00,0xe00):raise ValueError('pcidma add immediate changed')
        add_imm.append({'function_offset':hex(off),'fx3_immediate':hex(old_imm),'fx6_immediate':hex(new_imm)})
    pa,pb=[image[model][int(f[model]['patch_text_file_offset'],0):int(f[model]['patch_text_file_offset'],0)+0xd8] for model in ('fx3','fx6')]
    patch_diffs=[hex(i) for i in range(0,0xd8,4) if pa[i:i+4]!=pb[i:i+4]]
    if patch_diffs!=['0x60','0x88','0xc8']:raise ValueError('patch API difference set changed')
    old=int(f['fx3']['pcidma_address'],0)
    s6=symbols['fx6'];occupied=[(i,v) for i,v in enumerate(s6) if v['address']<=old<s6[i+1]['address']]
    if len(occupied)!=1 or occupied[0][1]['name']!='watchdog_touch_exception':
        raise ValueError('FX6 old-address collision changed')
    i,owner=occupied[0];old_file=owner['file_offset']+(old-owner['address'])
    old16=image['fx6'][old_file:old_file+16]
    if old_file!=0x2a20c8 or old16.hex()!='620000b9c20e805223300091620000b9':
        raise ValueError('FX6 occupied original address bytes changed')
    pinned='000b00b4fd7bbba9fd030091f35301a9'
    if f['fx6']['pcidma_first16_hex']!=pinned or old16.hex()==pinned:
        raise ValueError('helper patch entry requirement changed')
    def owner_of(addr):
        hits=[(j,v) for j,v in enumerate(s6[:-1]) if v['address']<=addr<s6[j+1]['address']]
        if len(hits)!=1:raise ValueError('unresolved FX6 code owner')
        j,v=hits[0]
        return {'address':hex(addr),'symbol':v['name'],'symbol_start':hex(v['address']),'symbol_end_exclusive':hex(s6[j+1]['address']),'file_offset':hex(v['file_offset']+addr-v['address'])}
    fallbacks=[owner_of(old+0x160),owner_of(old+0x10)]
    if [v['symbol'] for v in fallbacks]!=['subsys_new_mm','watchdog_touch_exception']:
        raise ValueError('FX6 fallback collision changed')
    return {'status':'PASS_STATIC_FIRMWARE_SIDE_CONTRACT_NO_PATCH','sources':{k:{'path':str(path),'sha256':digest or sha(path.read_bytes())} for k,(path,digest) in SOURCES.items()},'original_backup_consumer':{'module_path':str(backup_path),'sha256':sha(backup_path.read_bytes()),'function':'backupfile_get_cp_data','function_text_offset':'0x7030','call_instruction_text_offset':'0x70bc','return_pc_text_offset':'0x70c0','call_instruction_file_offset':hex(backup.byname['.text']['offset']+0x70bc),'relocation':'R_AARCH64_CALL26 pcidma_transfer_async'},'kernel_functions':f,'pcidma_differing_instruction_words':diffs,'pcidma_add_immediate_differences':add_imm,'patch_text_differing_instruction_offsets':patch_diffs,'old_fx3_address_in_fx6_image':{'address':hex(old),'owner_symbol':owner['name'],'owner_start':hex(owner['address']),'owner_end_exclusive':hex(s6[i+1]['address']),'file_offset':hex(old_file),'first16_hex':old16.hex(),'first16_sha256':sha(old16),'equals_helper_pinned_first16':False},'fallback_targets_in_fx6_image':fallbacks,'helper_contract':{'lookup_must_return_fixed_address':f['fx3']['pcidma_address'],'then_reads_and_patches_exact_first16':True,'patch_function_name':'aarch64_insn_patch_text','patch_function_body_same_sha':f['fx3']['patch_text_sha256']==f['fx6']['patch_text_sha256'],'hardcoded_fallback_targets':[hex(old+0x160),hex(old+0x10)],'targeted_backup_return_pc_relative_to_module':'backupfile_get_cp_data+0x90','other_calls_forward_via_pinned_fallback':True,'target_descriptor_40B_fields':'source=0x404000000; destination=0x4040d2000; length=1369580; callback=backupfile_cb_getcp; full schema in original header lines 55-76','synthetic_cp_bank_header_required':'BK4 magic at +12; 819 groups, 31197 rows, data start 192384; see pinned helper core header'},'minimal_firmware_diff_feasible_now':False,'reason':'old FX3 patch address is live FX6 watchdog_touch_exception code; both native fallback targets and full function body differ, so an export alias or one-address change would overwrite/branch into unrelated code','runtime_lookup_observed':False,'runtime_module_load_observed':False,'firmware_image_modified':False}

if __name__=='__main__':
    result=main();(HERE/'firmware-side-contract.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'status':result['status'],'old_address_owner':result['old_fx3_address_in_fx6_image']['owner_symbol'],'pcidma_differing_words':len(result['pcidma_differing_instruction_words']),'candidate_patch_created':False},indent=2))
