#!/usr/bin/env python3
"""Close static provider-name gap using real paired module export records."""
import datetime
import io
import json
from elftools.elf.elffile import ELFFile
import osal_dependency_audit as audit
f=audit.f


def main():
    f.im.volume();out=f.STAGE/'additional-provider-audit.json';assert not out.exists()
    old=json.loads((f.STAGE/'osal-dependency-audit.json').read_text())
    extraction=json.loads((f.STAGE/'devno-extraction.json').read_text())
    files=[f.n.STAGE/'official-files/nflasha15/kmod/osal_utm.ko',f.ROOT/extraction['output']]
    targets={'osal_create_waitable_thread','osal_wait_thread_exit','udif_devnodes'};definitions=[]
    for path in files:
        raw=path.read_bytes();elf=ELFFile(io.BytesIO(raw));syms=elf.get_section_by_name('.symtab')
        table=audit.exports(elf,syms)
        if path.name=='devno.ko':assert f.im.sha(raw)==extraction['sha256']
        else:
            assert f.im.sha(raw)==next(m['sha256'] for m in old['other_pinned_modules_consulted'] if m['path']==str(path.relative_to(f.ROOT)))
        for name in sorted(targets&table.keys()):
            sym=[x for x in syms.iter_symbols() if x.name==name and isinstance(x['st_shndx'],int)]
            assert len(sym)==1
            definitions.append({'symbol':name,'provider':str(path.relative_to(f.ROOT)),
              'sha256':f.im.sha(raw),'export_record':table[name],'symbol_type':sym[0]['st_info']['type'],
              'size':sym[0]['st_size'],'runtime_mapping_or_initialization':False})
    assert {x['symbol'] for x in definitions}==targets and len(definitions)==3
    missing=[x['symbol'] for x in old['static_provider_resolution'] if x['resolution_status']=='missing_in_current_assets']
    assert missing==['udif_devnodes']
    candidates=[x for x in old['static_provider_resolution'] if x['resolution_status']=='unique_kernel_candidate']
    assert len(candidates)==44
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'ALL47_OSAL_IMPORT_NAMES_HAVE_STATIC_ORIGINAL_PROVIDER_EVIDENCE',
      'prior_audit_initially_missing_in_assets':missing,'kernel_unique_neighbor_validated_candidates':44,
      'additional_actual_module_export_records':definitions,'total_original_import_names':47,
      'module_data_export_is_not_live_initialized_device_nodes':True,
      'candidate_export_values_outside_kernel_file':[x['symbol'] for x in candidates if not x['static_kernel_export_candidates'][0]['value_within_kernel_file']],
      'relocation_runtime_mapping_kernel_state_module_init_callbacks_threads_or_hardware_executed':False,
      'next_scope':'Use these static sources to verify precise AArch64 relocations and mapping ranges; exported symbols or matching vermagic do not establish Linux runtime state or a successful message allocation/reply.'}
    f.im.write_json(out,result)
    print(json.dumps({'status':result['status'],'imports':47,'kernel_candidates':44,'module_export_records':3,
      'kernel_candidates_outside_file':result['candidate_export_values_outside_kernel_file']}))


if __name__=='__main__':main()
