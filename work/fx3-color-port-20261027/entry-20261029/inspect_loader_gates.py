#!/usr/bin/env python3
"""Pinned original loader and upload callback fragments, without native loading."""
from pathlib import Path
import hashlib,json,struct
from inspect_entry_chain import View,sources,listing,HERE

def main():
    targets={'libupdatercorecommon.so':[0x9ae8],
             'libupdatercommon.so':[0x9e38],
             'libupdaterufp.so':[0x1b40,0x22e0,0x27c4,0x3a00,0x3bcc]}
    # Private UFP spans are closed by the next independently selected entry;
    # these are bounded code fragments, not asserted ELF function symbols.
    private_sizes={0x1b40:0x10c,0x22e0:0x1b8,0x27c4:0x6a8}
    rows=[];bss=None
    for source in sources():
        view=View(source['path'],source['sha256'])
        if view.path.name=='crypter.elf':
            section=next(s for s in view.elf.iter_sections() if s['sh_addr']<=0x412094<s['sh_addr']+s['sh_size'])
            assert section['sh_type']=='SHT_NOBITS'
            init=view.elf.get_section_by_name('.init_array')
            bss=dict(source_sha256=source['sha256'],file_chunk_global_va='0x412094',section=section.name,section_type=section['sh_type'],
                     init_array_pointers=[hex(x[0]) for x in struct.iter_unpack('<Q',init.data())],
                     scope='This global has no file-backed value. ELF zero-fill applies on a fresh load, but runtime initialization and main argument parsing are not executed in this static observation. Do not substitute this for actual FILE_CHUNK call arguments.')
        for va in targets.get(view.path.name,[]):
            size=private_sizes[va] if va in private_sizes else len(view.function(va))
            text,literals,calls=listing(view,va,size)
            output=HERE/'entry-fragments'/f'{view.path.name}-{va:x}-loader-gate.txt';output.write_text(text)
            rows.append(dict(library=view.path.name,label=view.labels.get(va,'bounded private fragment'),va=hex(va),source_sha256=source['sha256'],bytes=size,
                             sha256=hashlib.sha256(view.read(va,size)).hexdigest(),literals=literals,calls=calls,disassembly=str(output.relative_to(HERE))))
    result=dict(fragments=rows,crypter_global=bss,scope='Static original slices only. DllHandler calls dlopen directly at this helper layer; underlying dynamic loader/kernel policy remains unverified. Chassis filename comparison is not cryptographic authenticity. MSC completion reaches a crypter process request, but external reachability, command sequencing and whole container admission are not established.')
    (HERE/'loader-gates-selected-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(fragments=len(rows),native_loader_calls=0,camera_actions=0)))

if __name__=='__main__':main()
