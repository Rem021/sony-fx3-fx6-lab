#!/usr/bin/env python3
"""Static pinned OSAL ELF dependencies; no module relocation or execution."""
import collections
import datetime
import io
import json
import re
import struct
from elftools.elf.elffile import ELFFile
import resource_message as f


def string(blob,off):
    if not 0<off<len(blob) or blob[off-1]!=0:return None
    end=blob.find(b'\0',off,min(off+128,len(blob)))
    if end<0:return None
    raw=blob[off:end]
    if not re.fullmatch(rb'[A-Za-z_][A-Za-z_0-9]*',raw):return None
    return raw.decode()


def export_candidates(kernel,name):
    # Search exact symbol-name starts, then paired value/name records and
    # sorted valid neighbors. This is static provenance, not live exports.
    result=[];cursor=0;needle=b'\0'+name.encode()+b'\0'
    while True:
        at=kernel.find(needle,cursor)
        if at<0:break
        off=at+1;cursor=off+len(name)
        ptr=f.n.K+off;cursor2=0
        while True:
            ref=kernel.find(struct.pack('<Q',ptr),cursor2)
            if ref<0:break
            cursor2=ref+1;entry=ref-8
            if entry<16 or entry%8 or ref+24>len(kernel):continue
            neighbors=[]
            for row in (entry-16,entry,entry+16):
                value,pointer=struct.unpack_from('<QQ',kernel,row)
                label=string(kernel,pointer-f.n.K)
                if label is None or not f.n.K<=value<f.n.K+0x10000000:break
                neighbors.append({'entry_offset':hex(row),'name':label,'value':hex(value),
                  'value_within_kernel_file':0<=value-f.n.K<len(kernel)})
            if len(neighbors)!=3:continue
            if [x['name'] for x in neighbors]!=sorted(x['name'] for x in neighbors):continue
            if neighbors[1]['name']!=name:continue
            result.append({'entry_offset':hex(entry),'value':neighbors[1]['value'],
              'value_within_kernel_file':neighbors[1]['value_within_kernel_file'],
              'valid_sorted_name_neighbors':neighbors})
    return result


def function(elf,syms,name):
    matches=[s for s in syms.iter_symbols() if s.name==name and s['st_info']['type']=='STT_FUNC'
      and isinstance(s['st_shndx'],int)]
    assert len(matches)==1,name
    sym=matches[0];sec=elf.get_section(sym['st_shndx']);start=sym['st_value'];end=start+sym['st_size']
    reloc=[]
    for relsec in elf.iter_sections():
        if relsec['sh_type']!='SHT_RELA' or relsec['sh_info']!=sym['st_shndx']:continue
        for r in relsec.iter_relocations():
            if not start<=r['r_offset']<end:continue
            target=syms.get_symbol(r['r_info_sym'])
            reloc.append({'section_offset':hex(r['r_offset']),'type':r['r_info_type'],
              'target_symbol':target.name,'target_section':target['st_shndx'],
              'target_value':hex(target['st_value']),'addend':r['r_addend']})
    return {'symbol':name,'section':sec.name,'start':hex(start),'size':sym['st_size'],
      'instructions_unrelocated_section_relative':f.im.dump(sec.data(),start,end,0),
      'relocations_in_function':reloc,'not_loaded_or_executed':True}


def main():
    f.im.volume();out=f.STAGE/'osal-dependency-audit.json';assert not out.exists()
    module=f.n.STAGE/'official-files/nflasha15/kmod/osal_uipc.ko'
    old=json.loads((f.n.STAGE/'final-receipt.json').read_text())
    files={x['path']:x['sha256'] for x in old['files']}
    assert f.im.sha(module.read_bytes())==files[str(module.relative_to(f.ROOT))]
    elf=ELFFile(io.BytesIO(module.read_bytes()));syms=elf.get_section_by_name('.symtab')
    assert elf['e_type']=='ET_REL' and elf['e_machine']=='EM_AARCH64' and elf.little_endian
    undefined=sorted(s.name for s in syms.iter_symbols() if s.name and s['st_shndx']=='SHN_UNDEF')
    assert len(undefined)==len(set(undefined))
    kernelpath=f.n.STAGE/'official-files/nflasha3/vmlinux.bin';kernel=kernelpath.read_bytes()
    assert f.im.sha(kernel)==files[str(kernelpath.relative_to(f.ROOT))]
    facts=[];other_modules=[]
    for path in sorted(module.parent.glob('*.ko')):
        if path==module:continue
        digest=f.im.sha(path.read_bytes());assert digest==files[str(path.relative_to(f.ROOT))]
        e=ELFFile(io.BytesIO(path.read_bytes()));symbols=e.get_section_by_name('.symtab')
        defs=[]
        for s in symbols.iter_symbols():
            if s.name in undefined and isinstance(s['st_shndx'],int):
                defs.append({'symbol':s.name,'section':e.get_section(s['st_shndx']).name,
                  'section_value':hex(s['st_value']),'size':s['st_size']})
        other_modules.append({'path':str(path.relative_to(f.ROOT)),'sha256':digest,'definitions':defs})
    for name in undefined:
        kernel_candidates=export_candidates(kernel,name)
        module_candidates=[{'module':m['path'],**d} for m in other_modules for d in m['definitions'] if d['symbol']==name]
        facts.append({'symbol':name,'static_kernel_export_candidates':kernel_candidates,
          'already_extracted_module_definitions':module_candidates,
          'resolution_status':'unique_kernel_candidate' if len(kernel_candidates)==1 and not module_candidates
            else 'module_definition_requires_export_and_relocation_check' if not kernel_candidates and module_candidates
            else 'missing_in_current_assets' if not kernel_candidates and not module_candidates else 'ambiguous_static_candidates',
          'runtime_mapping_initialization_and_effect_verified':False})
    relocs=collections.Counter(r['r_info_type'] for sec in elf.iter_sections()
      if sec['sh_type']=='SHT_RELA' for r in sec.iter_relocations())
    assert set(relocs)=={257,261,283}
    modinfo=[x for x in elf.get_section_by_name('.modinfo').data().decode().split('\0') if x]
    banner=re.search(rb'Linux version ([^ ]+) ',kernel);assert banner
    functions=[function(elf,syms,name) for name in ('init_module','osal_valloc_msg_wait',
      'osal_snd_sync_msg','__osal_snd_sync_msg','osal_free_msg','osal_set_msg_src')]
    all_names={s.name for s in syms.iter_symbols()}
    exported={name:'__ksymtab_'+name in all_names for name in (
      'osal_valloc_msg_wait','osal_snd_sync_msg','osal_free_msg','osal_set_msg_src')}
    assert all(exported.values())
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'STATIC_OSAL_DEPENDENCIES_IDENTIFIED_NOT_LINKED_OR_INITIALIZED',
      'module_path':str(module.relative_to(f.ROOT)),'module_sha256':f.im.sha(module.read_bytes()),
      'kernel_sha256':f.im.sha(kernel),'kernel_banner_version_only':banner.group(1).decode(),
      'modinfo':modinfo,'undefined_symbol_count':len(undefined),'undefined_symbols':undefined,
      'relocation_counts_all_sections':dict(relocs),
      'relocation_ABI_names':{'257':'R_AARCH64_ABS64','261':'R_AARCH64_PREL32','283':'R_AARCH64_CALL26'},
      'four_public_message_symbols_have_ksymtab_entries':exported,
      'static_provider_resolution':facts,'resolution_counts':dict(collections.Counter(x['resolution_status'] for x in facts)),
      'other_pinned_modules_consulted':other_modules,'functions':functions,
      'scan_scope':'Exact names and paired kernel values/names plus two valid sorted neighbors; module definitions from pinned extracted files. No runtime binding, whole-kernel state, missing-provider inference beyond these assets, or indirect call graph completeness.',
      'init_module_scope':'Original entry has relocation to udif_driver_register. Registration/callback initialization and all runtime service state remain unexecuted.',
      'execution_module_load_host_driver_camera_or_persistent_operation':False,
      'next_scope':'Validate remaining provider exports and original AArch64 relocations before any bounded module execution. Stop at uninitialized pool/thread/scheduler/device dependencies; never invent returned buffers or synchronous replies.'}
    f.im.write_json(out,result)
    print(json.dumps({'status':result['status'],'undefined':len(undefined),'relocations':dict(relocs),
      'resolution_counts':result['resolution_counts']}))


if __name__=='__main__':main()
