#!/usr/bin/env python3
"""Original engine dependency graph and preverification virtual slots."""
from pathlib import Path
import hashlib,json,struct
from elftools.elf.elffile import ELFFile

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'input-20261028/engine-rootfs/2.05'

def main():
    rows=[]
    for folder in ['usr/bin','usr/lib']:
        for p in sorted((SOURCE/folder).iterdir()):
            if not p.is_file():continue
            raw=p.read_bytes()
            if not raw.startswith(b'\x7fELF'):continue
            with p.open('rb') as f:
                e=ELFFile(f);dynamic=e.get_section_by_name('.dynamic');needed=[]
                if dynamic:
                    needed=[tag.needed for tag in dynamic.iter_tags() if tag.entry.d_tag=='DT_NEEDED']
                syms=e.get_section_by_name('.dynsym')
                input_names=[s.name for s in syms.iter_symbols() if s.name=='GetUpdater' or any(x in s.name for x in ['GetFileInputMode','GetCryptFileInputMode','GetUUDFileInputMode','GetSDFileInputMode'])] if syms else []
                rows.append(dict(path=str(p.relative_to(SOURCE)),name=p.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),needed=needed,input_api_symbols=input_names))
    lookup={r['name']:r for r in rows};graph=[]
    for seed in ['sauu','sdfileinput.elf','uudfileinput.elf']:
        queue=[seed];seen=set();missing=set()
        while queue:
            name=queue.pop()
            if name in seen:continue
            if name not in lookup:missing.add(name);continue
            seen.add(name);queue.extend(lookup[name]['needed'])
        graph.append(dict(entry=seed,reachable_libraries=sorted(seen-{seed}),unresolved_needed=sorted(missing),
                          fileinput_library_reachable='libfileinputupdaterapi.so' in seen,
                          cryptfileinput_library_reachable='libcryptfileinputupdaterapi.so' in seen))
    slots=[]
    for filename,table_name,key_va,got,constructor_sequence in [('libupdaterapi.so','_ZTVN7Updater18UFPDecryptorModuleE',0x148e2,0x28f28,0x12c98),('libuudfileinputupdaterapi.so','_ZTVN7Updater22UUDFileDecryptorModuleE',0x9d42,0x1bf70,0x8714)]:
        p=SOURCE/'usr/lib'/filename
        with p.open('rb') as f:
            e=ELFFile(f);dyn=e.get_section_by_name('.dynsym');symbols=list(dyn.iter_symbols());byname={s.name:s for s in symbols}
            relocations={r['r_offset']:r for r in e.get_section_by_name('.rela.dyn').iter_relocations()}
            def read(va,n):
                for seg in e.iter_segments():
                    if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=va and va+n<=seg['p_vaddr']+seg['p_filesz']:
                        f.seek(seg['p_offset']+va-seg['p_vaddr']);data=f.read(n);assert len(data)==n;return data
                raise AssertionError((filename,hex(va),'not file-backed'))
            table=byname[table_name];slot=table['st_value']+16+0xa0;assert slot+8<=table['st_value']+table['st_size']
            gotrel=relocations[got];assert gotrel['r_info_type']==1025
            assert symbols[gotrel['r_info_sym']].name==table_name
            from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
            ins=list(Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN).disasm(read(constructor_sequence,16),constructor_sequence))
            assert ins[0].mnemonic=='ldr' and ins[0].op_str==f'x0, [x0, #{hex(got&4095)}]'
            expected_add_index=1 if filename=='libupdaterapi.so' else 2
            assert ins[expected_add_index].mnemonic=='add' and ins[expected_add_index].op_str=='x0, x0, #0x10'
            assert ins[expected_add_index+1].mnemonic=='str' and ins[expected_add_index+1].op_str=='x0, [x19]'
            raw_ptr=struct.unpack('<Q',read(slot,8))[0]
            r=relocations[slot];typ=r['r_info_type'];symbol=symbols[r['r_info_sym']]
            assert typ in [257,1027]
            ptr=(r['r_addend'] if typ==1027 else symbol['st_value']+r['r_addend'])
            matches=[s for s in symbols if s['st_value']==ptr and s['st_size']]
            assert matches and all('WaitForFirmwareCopyCompletion' in s.name for s in matches)
            key=read(key_va,64).split(b'\0',1)[0].decode();assert key=='/etc/VerificationKey.pem'
            slots.append(dict(library=filename,vtable=table_name,vtable_va=hex(table['st_value']),constructor_vptr_proven=True,constructor_sequence_va=hex(constructor_sequence),constructor_got=hex(got),vptr_offset=16,virtual_offset='0xa0',slot_va=hex(slot),raw_file_pointer=hex(raw_ptr),relocation_type=typ,resolved_va=hex(ptr),symbol=matches[0].name,key_path_va=hex(key_va),key_path=key))
    result=dict(files=rows,dependencies=graph,preverification_slots=slots,
                limits=['Only DT_NEEDED graph; dlopen, alternate search paths and optional runtime modules are not ruled out.',
                        'Original engine is historical 2.05, not a readback of the user camera running 7.02.',
                        'No API, mode switch, USB or filesystem write was sent to a camera.'])
    (HERE/'input-dependency-and-vtable-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'elf_files':len(rows),'graph':[{k:r[k] for k in ['entry','fileinput_library_reachable','cryptfileinput_library_reachable']} for r in graph],'wait_slots':len(slots)}))

if __name__=='__main__':main()
