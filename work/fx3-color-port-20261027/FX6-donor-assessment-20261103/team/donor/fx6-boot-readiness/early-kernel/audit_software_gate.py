#!/usr/bin/env python3
"""Pin the first fixed-CPIO init/module boundary before synthetic helpers run."""
import hashlib
import json
import re
import struct
import tempfile
from pathlib import Path

from fixed_runner import HERE,serial_observation
from fixed_platform import main as fixed_platform
import sys
sys.path.insert(0,str(HERE.parent))
from elf64 import ELF64

ROOT=HERE.parents[6]
AUDIT=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/cpio-audit.json'
REVIEW=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx6-init-boundary-fixed-platform-review.json'
RUN=HERE/'runs/fixed-fx3-306428ab'
HELPER=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers'
PINS={
 'cpio_audit':(AUDIT,'cc0b3c5b1925aa4bb0cb14aab275f2831833c7378490ca5408789f3824eb4847'),
 'owner_init_review':(REVIEW,'63b04f21d58cf90f1add79bd705b8fde56dcd52eb9c4424ce945b713a4b73a42'),
 'init_run_receipt':(RUN/'run-receipt.json','9c3e04bc3a6b62c57ea411b781c3093321d4b0543eb7c12e039bc4cf3daa204f'),
 'init_run_serial':(RUN/'serial.log','69eea39535b90eeb4e02584a2256bd6ecca5218314c5f61fadf95c288a50a978'),
 'liro_closure':(HERE/'liro-closure.json','e2c617cdd786c3536eeaca8090ac59b8367abf2e98af8281fa82b9dfbb5cf7a6'),
 'module_vs_kernel_abi':(HERE/'fx3-modules-vs-fx6-kernel.json','3cd9122713905ae3c883375c1a22164058504a78ebc7d5af0404cab00fac0fdc'),
 'cp_helper_build':(HELPER/'fx3-cp-backup-v5-native101-build.json','d9a14d32fd284e9deb9253c159d2c91e61f3568141426b72085e70eda47570e4'),
 'cp_helper_module_unit':(HELPER/'fx3-cp-backup-v5-native101-module-unit.c','8ba37b03b9e2775ae4784a643ec19bc319d4a8eb81dc56b14616940879a3ba13'),
 'cp_helper_ko':(HELPER/'fx3-cp-backup-v5-native101.ko','f4d7a1fa048d3548840fb2b9dd91e9538b19a34e48089a01ee466c02d3c277ca'),
 'cp_helper_source':(HELPER/'fx3-cp-backup-v5-native101.c','b0de532abb5c688f360f46d862abe1c8c1b2114f8448b5e3a91573cd9987b4c0'),
 'cp_helper_sync_header':(HELPER/'fx3-backup-sync101-v1.h','6f2116440d17db50f7c35b57f7ab967ce304318a431649a76885c096bd87ee96'),
}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_cpio_members(path,names):
    found={}
    with path.open('rb') as f:
        while True:
            h=f.read(110)
            if len(h)!=110 or h[:6] not in (b'070701',b'070702'):raise ValueError('invalid CPIO newc header')
            vals=[int(h[6+i*8:14+i*8],16) for i in range(13)]
            size,namelen=vals[6],vals[11]
            if not 1<=namelen<=4096 or size>512*1024*1024:raise ValueError('CPIO bounds')
            name=f.read(namelen).rstrip(b'\0').decode('utf-8')
            f.seek((-110-namelen)%4,1)
            if name=='TRAILER!!!':break
            if name in names:found[name]=f.read(size)
            else:f.seek(size,1)
            f.seek((-size)%4,1)
    if set(found)!=set(names):raise ValueError('selected CPIO members missing')
    return found


def main():
    for key,(path,pin) in PINS.items():
        if sha(path)!=pin:raise ValueError('source changed '+key)
    audit=json.loads(AUDIT.read_text());lines=audit['init_text'].splitlines()
    members={v['path']:v for v in audit['members']}
    review=json.loads(REVIEW.read_text());receipt=json.loads((RUN/'run-receipt.json').read_text())
    observed=serial_observation((RUN/'serial.log').read_bytes())
    if review['init_marker_complete_line']!='FX3_DEVTMPFS_RC=0' or observed['init_boundary_rc']!=0 or receipt['reason']!='guest_init_boundary':
        raise ValueError('init boundary not independently verified')
    if review['candidate_manifest_sha256']!='42cddf844eb37a4712feb59a0c595ab9746eee21b37b210a7f81741bdb16797c':
        raise ValueError('fixed platform candidate changed')
    platform=fixed_platform()
    first_original=[(i,line) for i,line in enumerate(lines,1) if 'insmod "$mod"' in line]
    first_sim=[(i,line) for i,line in enumerate(lines,1) if '/simulation/' in line]
    if first_original[0][0]!=74 or first_sim[0][0]!=89:raise ValueError('original/simulation order changed')
    if any(re.search(r'0x[0-9a-fA-F]{6,}',line) for line in lines[:76]):
        raise ValueError('unexpected absolute hex constant before first insmod receipt')
    original_order=['kmod/devno.ko','usr/kmod/osal_utm.ko','usr/kmod/osal_uipc.ko']
    closure=json.loads((HERE/'liro-closure.json').read_text())
    abi=json.loads((HERE/'fx3-modules-vs-fx6-kernel.json').read_text())
    ordered=[]
    for name in original_order:
        mod=closure['closure_modules']['/'+name]
        if members[name]['sha256']!=mod['sha256'] or name not in members:raise ValueError('module identity mismatch')
        ordered.append({'guest_path':'/'+name,'sha256':mod['sha256'],'fixed_cpio_member':True,'original_init_module_file_offset':mod['init_module']['file_offset'] if mod['init_module'] else None,'FX6_export_name_coverage_for_imports':all(v['symbol'] not in abi['fx6_missing_export_names'] for v in closure['kernel_edges'] if v['consumer']=='/'+name),'runtime_load_on_FX6_kernel':'UNTESTED'})
    helpers={}
    names=('simulation/fx3-ldec-soft103-v1.ko','simulation/fx3-cp-backup-reset-v1.ko','simulation/fx3-file100-observer-v2')
    blobs=selected_cpio_members(Path(platform['unchanged_full_binary_sha256']['software_guest_cpio']['path']),names)
    fx6_exports={v['name'] for v in json.loads((HERE.parents[1]/'kernel-provider-binding/export-crosscheck.json').read_text())}
    original_catalog=json.loads((ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/original-full-module-provider-catalog.json').read_text())
    original_exporters={symbol for module in original_catalog['modules'] for symbol in module['exports']}
    for name in names:
        if hashlib.sha256(blobs[name]).hexdigest()!=members[name]['sha256']:raise ValueError('CPIO helper SHA mismatch')
        helpers[name]={'sha256':members[name]['sha256'],'scheduled_after_first_module_gate':True}
        if name.endswith('.ko'):
            with tempfile.TemporaryDirectory(prefix='elf-check-',dir=HERE) as temp:
                source=Path(temp)/'module.ko';source.write_bytes(blobs[name])
                elf=ELF64(source)
                imports=sorted({s['name'] for s in elf.symbols() if s['name'] and s['shndx']==0 and s['bind']!=0})
                helpers[name].update({'elf_type':elf.etype,'machine':elf.machine,'undefined_symbols':imports,'fx6_kernel_export_name_missing':sorted(n for n in imports if n not in fx6_exports and n not in original_exporters),'module_export_candidates':sorted(n for n in imports if n in original_exporters),'has___versions':'__versions' in elf.byname})
                if elf.etype!=1 or elf.machine!=183:raise ValueError('synthetic module ELF type')
    helpers['simulation/fx3-ldec-soft103-v1.ko']['local_build_output_byte_match']=members['simulation/fx3-ldec-soft103-v1.ko']['sha256']=='dec6285407341319bfe6239a47e434f08b920ec23c6af960d2653c1d061c02df'
    helpers['simulation/fx3-cp-backup-reset-v1.ko']['local_v1_build_output_byte_match']=members['simulation/fx3-cp-backup-reset-v1.ko']['sha256']=='7e756a4e9a2edb9770baf92c07cb88f342690b1636d6c258f0ec2e1d6a98abd2'
    helpers['simulation/fx3-file100-observer-v2']['local_binary_byte_match']=members['simulation/fx3-file100-observer-v2']['sha256']=='044d08549217523c645035e02ae74b1e76b73db17a61d13b0ff4ecd05a3987e0'
    cp_name='simulation/fx3-cp-backup-reset-v1.ko'
    build=json.loads((HELPER/'fx3-cp-backup-v5-native101-build.json').read_text())
    unit=(HELPER/'fx3-cp-backup-v5-native101-module-unit.c').read_text()
    source=(HELPER/'fx3-cp-backup-v5-native101.c').read_text()
    header=(HELPER/'fx3-backup-sync101-v1.h').read_text()
    if build['exit']!=0 or build['source_sha256']!=PINS['cp_helper_source'][1] or build['output_sha256']!=members[cp_name]['sha256'] or sha(HELPER/'fx3-cp-backup-v5-native101.ko')!=members[cp_name]['sha256']:
        raise ValueError('CP helper build/CPIO identity mismatch')
    if '#include "fx3-cp-backup-v5-native101.c"' not in unit or '#include "fx3-backup-sync101-v1.h"' not in source or 'int init_module(void){int rc=sync100_start();if(rc)return rc;' not in source:
        raise ValueError('CP helper compilation/entry chain changed')
    if 'insmod /simulation/fx3-cp-backup-reset-v1.ko' not in lines[114] or 'FX3_BACKUP_CP_INSMOD_RC=$backup_cp_rc' not in lines[116]:
        raise ValueError('CP helper guest init path changed')
    fx3_api=abi['critical_export_code_prefixes']['pcidma_transfer_async']['fx3']['address']
    fx6_api=abi['critical_export_code_prefixes']['pcidma_transfer_async']['fx6']['address']
    assert fx3_api=='0xffffff80083220c8' and fx6_api=='0xffffff8008322f70'
    if f'if((U)sync100_api!={fx3_api}UL||' not in header or 'sync100_api=(void*)kallsyms_lookup_name("pcidma_transfer_async")' not in header:
        raise ValueError('CP helper address guard changed')
    fallback=('0xffffff8008322228','0xffffff80083220d8')
    if any(f'.quad {a}' not in header for a in fallback):raise ValueError('CP helper native fallback changed')
    # The compiled CPIO-identical ET_REL module independently carries this
    # address comparison and a relocation for its symbol-name lookup.
    cp_elf=ELF64(HELPER/'fx3-cp-backup-v5-native101.ko')
    text_sec=cp_elf.byname['.text']
    guard_bytes=cp_elf.section_bytes('.text')[0x46c:0x4d0]
    guard_sha='f6300113b90b236b0c8417f8d6cc257e7de448d24f8db6c9f889a590e5bad4cb'
    if hashlib.sha256(guard_bytes).hexdigest()!=guard_sha:
        raise ValueError('compiled CP helper guard instructions changed')
    if cp_elf.section_bytes('.text')[0x7a8:0x7ac].hex()!='c0008012':
        raise ValueError('compiled CP helper -7 return changed')
    if cp_elf.section_bytes('.rodata.str1.1')[0x55:0x55+len(b'pcidma_transfer_async')+1]!=b'pcidma_transfer_async\0':
        raise ValueError('compiled CP helper lookup name changed')
    rela=cp_elf.byname['.rela.text'];symtab=cp_elf.sections[rela['link']]
    symstr=cp_elf.section_bytes(symtab['link'])
    call_ok=False
    for r_off in range(rela['offset'],rela['offset']+rela['size'],rela['entsize']):
        offset,info,addend=struct.unpack_from('<QQq',cp_elf.data,r_off)
        if offset!=0x484:continue
        sym_idx,kind=info>>32,info&0xffffffff
        sym_off=symtab['offset']+sym_idx*symtab['entsize']
        name_off=struct.unpack_from('<I',cp_elf.data,sym_off)[0]
        call_ok=kind==283 and addend==0 and cp_elf.cstr(symstr,name_off)=='kallsyms_lookup_name'
    if not call_ok:raise ValueError('compiled CP helper lookup call relocation changed')
    helpers[cp_name]['local_v5_build_output_byte_match']=True
    proven={'status':'PROVEN_CONDITIONAL_SOFTWARE_REFUSAL_IF_INIT_REACHES_LINE_115_AND_LOOKUP_RETURNS_FX6_LINK_ADDRESS','guest_init_line':115,'guest_module_path':'/'+cp_name,'module_sha256':members[cp_name]['sha256'],'module_matches_compiled_local_v5':True,'compiled_source_includes_sync_header':True,'init_module_calls_sync100_start_and_returns_error':True,'compiled_et_rel_guard':{'text_section_file_offset':text_sec['offset'],'text_offset_interval':['0x46c','0x4d0'],'file_offset_interval':[hex(text_sec['offset']+0x46c),hex(text_sec['offset']+0x4d0)],'raw_sha256':guard_sha,'lookup_call_relocation':'R_AARCH64_CALL26 kallsyms_lookup_name at .text+0x484','compare_instruction':'.text+0x4c0 cmp x8,x20','failure_branch_instruction':'.text+0x4cc b.ne .text+0x748','return_minus_7_instruction':'.text+0x7a8 mov w0,#-7'},'lookup_symbol':'pcidma_transfer_async','hardcoded_fx3_address':fx3_api,'fx6_image_linked_export_address':fx6_api,'source_guard_line':92,'source_fail_return':-7,'source_native_fallback_hardcoded_fx3_targets':list(fallback),'runtime_reached':False,'runtime_lookup_address_observed':False,'scope':'static original-CPIO-member byte identity plus pinned build/source, compiled guard and FX6 original linked export; runtime still stopped before first insmod'}
    return {'status':'PASS_FIXED_INIT_ORDER_AND_CONDITIONAL_HELPER_BLOCK_STATIC_ONLY','sources':{k:{'path':str(v[0]),'sha256':v[1]} for k,v in PINS.items()},'actual_fx6_image_with_fixed_fx3_init':{'line':observed['init_boundary_line'],'rc':observed['init_boundary_rc'],'first_module_rc_observed':observed['first_module_line'],'scope':'unchanged FX3 CPIO /init only'},'reviewed_init_line_interval':[1,88],'reviewed_later_init_line_interval':[114,118],'first_original_insmod_script_line':74,'first_simulation_insmod_script_line':89,'absolute_hex_literals_in_init_lines_1_to_76':0,'first_module_sequence':ordered,'later_simulation_helpers':helpers,'first_proven_conditional_software_block_if_reached':proven,'first_unverified_compatibility_boundary':'original /kmod/devno.ko insmod return under FX6 kernel; next original osal_utm/osal_uipc before line89 synthetic ldec','first_module_stop_condition':'complete FX3_INSMOD_RC_/kmod/devno.ko=<integer> line; kernel fault or CPUSET_NOT_READY first; AP/simulation guard fallback','new_guest_or_platform_changes':0,'host_polling_is_exact_CPU_breakpoint':False}


if __name__=='__main__':
    output=main();(HERE/'software-first-gate.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'status':output['status'],'init_boundary':output['actual_fx6_image_with_fixed_fx3_init']['line'],'first_original_insmod_line':output['first_original_insmod_script_line'],'first_simulation_line':output['first_simulation_insmod_script_line']},indent=2))
