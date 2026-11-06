#!/usr/bin/env python3
"""Pin the current AP module registry and offline WBI library code identity."""
from pathlib import Path
import hashlib,json,struct,sys
from current_static import View,sources,HERE
PROJECT=HERE.parents[2]

def main():
    member=next(s for s in json.loads((HERE/'additional-source-members.json').read_text()) if s['original_path']=='/lib/libIMDB.so')
    registry=View(HERE/member['output'],member['sha256']);targets={}
    for text in [b'libupdaterufp.so\0',b'udtr_ufp_init\0',b'udtr_ufp_exit\0']:
        off=registry.raw.find(text);assert off>=0 and registry.raw.find(text,off+1)<0
        seg=next(s for s in registry.elf.iter_segments() if s['p_type']=='PT_LOAD' and s['p_offset']<=off< s['p_offset']+s['p_filesz'])
        va=off-seg['p_offset']+seg['p_vaddr'];assert registry.read(va,len(text))==text
        targets[va]=text[:-1].decode()
    pointers=[]
    for r in registry.elf.get_section_by_name('.rela.dyn').iter_relocations():
        if r['r_info_type']==1027 and r['r_addend'] in targets:
            pointers.append(dict(slot=hex(r['r_offset']),target=hex(r['r_addend']),text=targets[r['r_addend']]))
    assert len(pointers)==3
    tail=HERE.parent/'tail-20261028';sys.path.insert(0,str(tail))
    from wbi_page_table_candidates import Snapshot
    snapshot=Snapshot();src=PROJECT/snapshot.meta['source']
    with src.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==snapshot.meta['source_sha256']
    mapping=json.loads((tail/'snapshot-link-map-inventory.json').read_text())
    # The inventory schema is a list nested in an object; use only its module list.
    modules=mapping.get('modules',mapping.get('link_map',[]))
    assert modules,'missing previously sealed link-map module list'
    module=next(m for m in modules if m.get('name')=='/usr/lib/libupdaterufp.so')
    source=next(s for s in sources() if Path(s['path']).name=='libupdaterufp.so')
    lib=View(source['path'],source['sha256']);base=int(module['base'],16);root=0x40867a000
    tests=[('ELF_header',0,64)]
    for name in ['.dynsym','.dynstr','.text','.rodata']:
        sec=lib.elf.get_section_by_name(name);tests.append((name,sec['sh_addr'],sec['sh_size']))
    checks=[]
    for label,va,n in tests:
        original=lib.read(va,n)
        try:
            got=snapshot.virtual(root,base+va,n)
            checks.append(dict(label=label,relative_va=hex(va),bytes=n,match=got==original,original_sha256=hashlib.sha256(original).hexdigest(),snapshot_sha256=hashlib.sha256(got).hexdigest()))
        except ValueError as error:checks.append(dict(label=label,relative_va=hex(va),bytes=n,match=False,error=str(error)))
    snapshot.close()
    status='PASS_REGISTRY_AND_SNAPSHOT_CODE_IDENTITY' if all(c['match'] for c in checks) else 'PARTIAL_REGISTRY_ONLY_WBI_CODE_UNREADABLE'
    result=dict(status=status,registry_sha256=member['sha256'],registry_pointers=pointers,
                snapshot_source_sha256=snapshot.meta['source_sha256'],root_physical_address=hex(root),link_map_module=module,library_sha256=source['sha256'],checks=checks,
                scope='Read-only original AP registry and original stored WBI page-table translation. Only ELF metadata, original code and literal strings read; no key derivation, snapshot execution, live body state or proof that a request was dispatched.')
    (HERE/'registry-and-snapshot-results.json').write_text(json.dumps(result,indent=2)+'\n')
    assert all(c['match'] or 'error' in c for c in checks),'readable snapshot bytes contradict original source'
    print(json.dumps({'status':status,'registry_pointers':len(pointers),'snapshot_identity_checks':len(checks),'all_match':all(c['match'] for c in checks),'camera_actions':0}))

if __name__=='__main__':main()
