#!/usr/bin/env python3
"""Persist full FX6 original compressed kallsyms catalog and provenance."""
from hashlib import sha256
import json
from pathlib import Path

from kernel_symbols import HERE, IMAGE, PIN, KernelSymbols


def main():
    image=KernelSymbols()
    chosen=('kallsyms_expand_symbol.constprop.1','kallsyms_lookup_name',
            'SyS_init_module','sys_init_module','load_module','do_init_module',
            'apply_relocate_add','module_finalize','find_symbol','get_ksymbol')
    selected={name:image.by_name.get(name,[]) for name in chosen}
    spans={}
    for name in chosen:
        if name=='sys_init_module':continue  # alias of SyS_init_module
        try:a,z=image.span(name)
        except ValueError:continue
        spans[name]={'start_file_offset':hex(a),'next_symbol_offset_exclusive':hex(z),
                     'sha256':sha256(image.raw[a:z]).hexdigest(),
                     'size_is_next_symbol_gap_not_ELF_function_size':True}
    catalog=HERE/'fx6-kernel-symbol-catalog.json'
    catalog.write_text(json.dumps(image.rows,separators=(',',':'))+'\n')
    output={'kernel_sha256':PIN,'kernel_bytes':len(image.raw),
            'old_FX3_code_signature_used_only_to_locate_FX6_code':True,
            'fx6_original_lookup_signature_file_offset':hex(image.lookup_start),
            'fx6_base_derived_from_original_token_index_and_literal':hex(image.base),
            'tables':image.tables,'symbol_count':image.count,'names_end_file_offset':hex(image.names_end),
            'selected_symbols':selected,'selected_next_symbol_spans':spans,
            'catalog_sha256':sha256(catalog.read_bytes()).hexdigest(),
            'parser_sha256':sha256((HERE/'kernel_symbols.py').read_bytes()).hexdigest(),
            'scope':'static FX6 original Image decoding only; no kernel boot'}
    (HERE/'symbol-recovery.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'symbol_count':image.count,'fx6_code_offset':hex(image.lookup_start),
                      'fx6_base':hex(image.base),'catalog_sha256':output['catalog_sha256']}))


if __name__=='__main__':main()
