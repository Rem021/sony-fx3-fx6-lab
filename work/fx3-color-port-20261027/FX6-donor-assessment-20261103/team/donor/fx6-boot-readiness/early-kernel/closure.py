#!/usr/bin/env python3
"""Recheck original FX3 LIRO recursive import closure against bytes and kernel exports."""
from __future__ import annotations
import hashlib
import json
import struct
import sys
from collections import defaultdict,deque
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[6]
sys.path.insert(0,str(HERE.parent))
from elf64 import ELF64
from fdt import parse_fdt

CAT=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/original-full-module-provider-catalog.json'
KCAT=ROOT/'work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/work/kernel-symbol-catalog.json'
EXPORTS=ROOT/'work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/run-symbol-verification/export-crosscheck.json'
AUDIT=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/cpio-audit.json'
BASE=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json'
NATIVE_DTB=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/setting/cxd90057.dtb'
SRC_SHA={
 'elf_parser':(HERE.parent/'elf64.py','38f49a8142e582e11903288f7103e36d2079e26891b6cc8c8fe3971246dfa32b'),
 'fdt_parser':(HERE.parent/'fdt.py','0ab6f0d51b4d18c755f54f0bade9a0eb4e0c8a4bde56dc95d4753dcdb8511db4'),
 'module_catalog':(CAT,'6dc947431322367c3db93b877cceb9c7afeb3a0a4589c1747ab9982a5207b43c'),
 'kernel_symbol_catalog':(KCAT,'b37c6b7d4315f65234cd6b64c3be4a3d7c6e0d2cca66204e27cb5c575000a51e'),
 'kernel_export_crosscheck':(EXPORTS,'c3e33ad1d45276727dc7ee9c287bdbd3e440e32b1724816c74ba897641aae6f6'),
 'cpio_audit':(AUDIT,'cc0b3c5b1925aa4bb0cb14aab275f2831833c7378490ca5408789f3824eb4847'),
 'owner_baseline':(BASE,'854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669'),
 'fx3_native_dtb':(NATIVE_DTB,'c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280'),
}
ROOT_MODULE='/usr/kmod/liro.ko'
TARGETS={'dma330_mem_transfer_async','pciatu_map','pciatu_unmap','interchip_transfer_async'}
HW_WORDS=('irq','pci','dma','phys','memstart','ioremap','ioread','iowrite','udif_driver')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def relocs(e,section_name):
    section=e.byname.get('.rela'+section_name)
    if not section:return []
    symtab=e.sections[section['link']]
    if symtab['type']!=2 or section['entsize']!=24 or section['info']!=e.byname[section_name]['index']:
        raise ValueError('relocation section bounds/link')
    syms=list(e.symbols())
    if len(syms)!=symtab['size']//symtab['entsize']:raise ValueError('multiple symtables not supported')
    data=e.section_bytes(section['name']);out=[]
    for off in range(0,len(data),24):
        place,info,addend=struct.unpack_from('<QQq',data,off)
        symbol=syms[info>>32]
        out.append({'section_offset':place,'type':info&0xffffffff,'symbol':symbol['name'],'symbol_section':e.sections[symbol['shndx']]['name'] if 0<symbol['shndx']<len(e.sections) else None,'addend':addend,'rela_file_offset':section['offset']+off})
    return out


def main():
    for name,(path,want) in SRC_SHA.items():
        if sha(path)!=want:raise ValueError('source changed: '+name)
    catalog=json.loads(CAT.read_text());modules={m['guest_path']:m for m in catalog['modules']}
    symbol_catalog=json.loads(KCAT.read_text());ks_names={s['name']:s for s in symbol_catalog}
    cross=json.loads(EXPORTS.read_text())
    if len(cross)!=6089 or any('__ksymtab_'+v['name'] not in ks_names for v in cross):
        raise ValueError('kernel export crosscheck mismatch')
    kernel={s['name']:s for s in cross}
    cpio_audit=json.loads(AUDIT.read_text())
    cpio={m['path']:m for m in cpio_audit['members']}
    baseline=json.loads(BASE.read_text())
    if baseline['sha256']['fx3_kernel']['sha256']!='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c':
        raise ValueError('FX3 kernel pin mismatch')
    all_exporters=defaultdict(list)
    for m in catalog['modules']:
        for name in m['exports']:all_exporters[name].append(m['guest_path'])
    todo=deque([ROOT_MODULE]);visited={};edges=[];kernel_edges=[];ambiguous=[];unresolved=[]
    while todo:
        name=todo.popleft()
        if name in visited:continue
        m=modules[name]
        path=Path(m['payload'])
        if sha(path)!=m['sha256'] or cpio[name.lstrip('/')]['sha256']!=m['sha256']:
            raise ValueError('module source/CPIO SHA mismatch '+name)
        e=ELF64(path)
        if e.machine!=183 or e.etype!=1:raise ValueError('module ELF type')
        all_syms=list(e.symbols())
        elf_undefined={s['name'] for s in all_syms if s['name'] and s['shndx']==0 and s['bind']!=0}
        if elf_undefined!={v['name'] for v in m['undefined']}:raise ValueError('catalog undefined set mismatch '+name)
        defined={s['name']:s for s in all_syms if s['name'] and s['shndx']!=0}
        for symbol in m['exports']:
            if symbol not in defined or not e.exported_name(symbol):raise ValueError('catalog export not ELF verified '+symbol)
        init=defined.get('init_module')
        init_info=None
        if init:
            sec=e.sections[init['shndx']]
            body=e.data[sec['offset']+init['value']:sec['offset']+init['value']+init['size']]
            references=[r for r in relocs(e,sec['name']) if init['value']<=r['section_offset']<init['value']+init['size']]
            init_info={'section':sec['name'],'section_offset':init['value'],'file_offset':sec['offset']+init['value'],'bytes':init['size'],'body_sha256':hashlib.sha256(body).hexdigest(),'relocations':references}
        hard=[]
        for imp in m['undefined']:
            symbol=imp['name']
            if imp['binding']=='STB_WEAK':continue
            if symbol in kernel:
                kernel_edges.append({'consumer':name,'symbol':symbol,'kernel_export_entry_file_offset':kernel[symbol]['entry_offset'],'kernel_export_target_address':hex(kernel[symbol]['address']),'ksymtab_symbol_file_offset':ks_names['__ksymtab_'+symbol]['file_offset']})
                continue
            providers=all_exporters[symbol]
            if len(providers)==1:
                provider=providers[0]
                edges.append({'consumer':name,'symbol':symbol,'provider':provider})
                hard.append(provider);todo.append(provider)
            elif providers:ambiguous.append({'consumer':name,'symbol':symbol,'providers':providers})
            else:unresolved.append({'consumer':name,'symbol':symbol})
        expected=set(m['static_module_dependencies'])
        if set(hard)!=expected:raise ValueError('computed dependency set differs from pinned catalog '+name)
        visited[name]={'path':str(path),'sha256':m['sha256'],'bytes':m['bytes'],'present_in_frozen_cpio':True,'undefined_total':len(m['undefined']),'kernel_imports':sum(v['name'] in kernel for v in m['undefined']),'module_imports':len(hard),'direct_module_dependencies':sorted(set(hard)),'init_module':init_info,'hardware_relevant_import_names':[v['name'] for v in m['undefined'] if any(w in v['name'].lower() for w in HW_WORDS)]}
    if ambiguous or unresolved or len(visited)!=9:raise ValueError('closure not exact/complete')
    liro_edges={e['symbol']:e['provider'] for e in edges if e['consumer']==ROOT_MODULE and e['symbol'] in TARGETS}
    if set(liro_edges)!=TARGETS:raise ValueError('four LIRO provider edges missing')
    pcie=ELF64(Path(modules['/usr/kmod/pcieatu.ko']['payload']))
    d=pcie.byname['.data'];pcie_ctrl=struct.unpack_from('<I',pcie.data,d['offset'])[0]
    if pcie_ctrl!=3 or pcie.data[pcie.byname['.init.text']['offset']+0xd4:pcie.byname['.init.text']['offset']+0xd8]!=bytes.fromhex('000040b9'):
        raise ValueError('pcieatu default/read instruction changed')
    data_refs=relocs(pcie,'.data');init_refs=relocs(pcie,'.init.text')
    if not any(r['section_offset']==0x40 and r['symbol_section']=='.data' and r['addend']==0x88 for r in data_refs):raise ValueError('pcieatu descriptor callback-table pointer not found')
    if not any(r['section_offset']==0x88 and r['symbol_section']=='.init.text' and r['addend']==0 for r in data_refs):raise ValueError('pcieatu callback-table init pointer not found')
    if not any(r['section_offset']==0x39c and r['symbol']=='udif_driver_register' for r in init_refs):raise ValueError('pcieatu register call not found')
    read_va=0xfffffffff0000000 | (0x300004+((pcie_ctrl+0x3d9)<<22))
    native=parse_fdt(NATIVE_DTB.read_bytes())
    virt=parse_fdt(Path(baseline['sha256']['fx3_dtb_full_binary']['path']).read_bytes())
    native_pcie=next(v for v in native['selected_nodes'] if v['path']=='/soc/pcie_i')
    native_dma=next(v for v in native['selected_nodes'] if v['path']=='/soc/mdma@F1057000')
    virt_pcie=next(v for v in virt['selected_nodes'] if v['path']=='/pcie@10000000')
    init=cpio_audit['init_text'].splitlines()
    init_refs={n:[i for i,line in enumerate(init,1) if n.split('/')[-1] in line] for n in visited}
    return {'status':'PASS_STATIC_CLOSURE_ONLY','sources':{n:{'path':str(p),'sha256':h} for n,(p,h) in SRC_SHA.items()},'fx3_kernel_sha256':baseline['sha256']['fx3_kernel']['sha256'],'kernel_export_crosscheck_count':len(kernel),'closure_modules':visited,'closure_count':len(visited),'module_edges':edges,'module_edge_count':len(edges),'kernel_edges':kernel_edges,'kernel_edge_count':len(kernel_edges),'ambiguous':ambiguous,'unresolved_strong':unresolved,'four_liro_provider_edges':liro_edges,'guest_init_explicit_module_references':init_refs,'device_tree_comparison':{'native_root_compatible':native['root_compatible'],'native_pcie_i':native_pcie,'native_dma330':native_dma,'fixed_guest_root_compatible':virt['root_compatible'],'fixed_guest_generic_pcie':virt_pcie,'fixed_guest_has_native_pcie_i_or_pl330':any('pcie_i' in x['path'] or 'pl330' in x['compatible'] for x in virt['selected_nodes'])},'pcieatu_first_hw_read_candidate':{'module_sha256':modules['/usr/kmod/pcieatu.ko']['sha256'],'pcie_ctrl_default_value':pcie_ctrl,'pcie_ctrl_file_offset':d['offset'],'init_module_section_offset':0x380,'udif_driver_register_call_section_offset':0x39c,'descriptor_to_callback_table_relocation_data_offset':0x40,'callback_table_data_offset':0x88,'callback_to_init_relocation_data_offset':0x88,'callback_section':'.init.text','callback_read_section_offset':0xd4,'callback_read_file_offset':pcie.byname['.init.text']['offset']+0xd4,'instruction_le_hex':'000040b9','calculated_virtual_address':hex(read_va),'calculated_physical_low32':hex(read_va&0xffffffff),'execution_proven':False},'runtime_module_initialization_tested':False,'MMIO_or_IRQ_model_passed':False}


if __name__=='__main__':
    output=main();(HERE/'liro-closure.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'status':output['status'],'closure_count':output['closure_count'],'module_edges':output['module_edge_count'],'kernel_edges':output['kernel_edge_count'],'unresolved':len(output['unresolved_strong'])},indent=2))
