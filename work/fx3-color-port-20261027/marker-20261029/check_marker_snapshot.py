#!/usr/bin/env python3
"""Read only the original WBI libObj marker cache and matching code pages.

No code is executed; absent mappings stay absent. This is an official stored
boot snapshot, never a readback of the user's current camera.
"""
from pathlib import Path
import hashlib,json,struct,sys
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'ap-input-20261029'))
from current_static import View
sys.path.insert(0,str(TASK/'tail-20261028'))
from wbi_page_table_candidates import Snapshot

def main():
    card=json.loads((TASK/'body-load-20261029/obj-source.json').read_text())
    view=View(TASK/'body-load-20261029'/card['output'],card['sha256'])
    relocation=next(r for r in view.elf.get_section_by_name('.rela.dyn').iter_relocations() if r['r_offset']==0x262dc0)
    assert relocation['r_info_type']==1027;cache_va=relocation['r_addend'];assert cache_va==0x2d2c2c
    cache_section=next(s for s in view.elf.iter_sections() if s['sh_addr']<=cache_va<s['sh_addr']+s['sh_size'])
    snapshot=Snapshot();source=HERE.parents[2]/snapshot.meta['source']
    with source.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==snapshot.meta['source_sha256']
    mapping=json.loads((TASK/'tail-20261028/snapshot-link-map-inventory.json').read_text());root=int(mapping['root_physical_address'],16)
    module=next(m for m in mapping['modules'] if m['name']=='/usr/lib/libObj.so');base=int(module['base'],16);checks=[]
    for label,va,n in [('ELF_header',0,64),('initializer_code',0xee0b0,76),('run_version_code',0xeccc8,288),('marker_literal',0x1dc5be,16),('cache_GOT',0x262dc0,8),('cached_stat_result',cache_va,4)]:
        row=dict(label=label,relative_va=hex(va),bytes=n)
        try:
            raw=snapshot.virtual(root,base+va,n);row['snapshot_sha256']=hashlib.sha256(raw).hexdigest()
            if label=='cache_GOT':
                pointer=struct.unpack('<Q',raw)[0];row.update(pointer=hex(pointer),expected_pointer=hex(base+cache_va),pointer_matches=pointer==base+cache_va);assert row['pointer_matches']
            elif label=='cached_stat_result':row.update(unsigned_value=struct.unpack('<I',raw)[0],signed_value=struct.unpack('<i',raw)[0])
            else:
                original=view.read(va,n);row.update(original_sha256=hashlib.sha256(original).hexdigest(),matches_original=raw==original)
        except ValueError as error:row['unreadable']=str(error)
        checks.append(row)
    pages=[]
    for name in ['.plt','.text']:
        section=view.elf.get_section_by_name(name);begin=section['sh_addr'];end=begin+section['sh_size']
        for va in range(begin&-4096,end,4096):
            lo=max(begin,va);n=min(end,va+4096)-lo;row=dict(section=name,va=hex(lo),bytes=n)
            try:
                raw=snapshot.virtual(root,base+lo,n);original=view.read(lo,n)
                row.update(matches_original=raw==original,snapshot_sha256=hashlib.sha256(raw).hexdigest(),original_sha256=hashlib.sha256(original).hexdigest())
            except ValueError as error:row['unreadable']=str(error)
            pages.append(row)
    snapshot.close();readable=[r for r in pages if 'unreadable' not in r];matched=[r for r in readable if r['matches_original']]
    result=dict(source_library_sha256=card['sha256'],snapshot_source_sha256=snapshot.meta['source_sha256'],root_physical_address=hex(root),link_map_module=module,
                cache_relative_va=hex(cache_va),cache_section=cache_section.name,cache_section_type=cache_section['sh_type'],selected_checks=checks,code_page_checks=pages,
                code_page_summary=dict(total=len(pages),readable=len(readable),matching=len(matched),unreadable=len(pages)-len(readable),contradicting=len(readable)-len(matched)),
                scope='Original stored WBI page-table translation only. The cache GOT pointer and four-byte word are read separately from code identity. Missing initializer/version code or ELF headers are not reconstructed. Other matching pages support only their own identity, not execution of the unreadable initializer, a fresh stat result, complete runtime rootfs state, future bodyExecute behavior or the user camera. No zero fill, live device I/O, vendor native execution, mounts or changed firmware.')
    (HERE/'marker-snapshot-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(selected_checks=checks,code_page_summary=result['code_page_summary'])))

if __name__=='__main__':main()
