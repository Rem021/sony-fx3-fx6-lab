#!/usr/bin/env python3
"""Pin original stream decoder and lens preparation source ranges."""
import hashlib,json,sys
from decrypt_stream_guest import HERE,View
sys.path.insert(0,str(HERE.parent/'entry-20261029'))
from inspect_entry_chain import listing

def main():
    result=json.loads((HERE/'decrypt-stream-results.json').read_text());lens=json.loads((HERE/'lens-header-gate-results.json').read_text())
    views={r['path']:View(r['path'],r['sha256']) for r in result['sources']+lens['sources']}
    names={name for r in result['cases'] for name in r['original_function_entries']};bodies=[]
    for path,v in views.items():
        seen=set()
        for s in v.symbols:
            va=s['st_value'];label=v.names.get(s.name,s.name)
            if not va or va in seen or label not in names or s['st_info']['type']!='STT_FUNC':continue
            raw=v.function(va);seen.add(va)
            bodies.append(dict(source=path,source_sha256=hashlib.sha256(v.raw).hexdigest(),va=hex(va),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),label=label))
    fragments=[];out=HERE/'contract-fragments';out.mkdir(exist_ok=True)
    for path,v in views.items():
        name=v.path.name
        targets=([0xa514,0xa1f8,0xa244,0xa208,0xa840,0xa780,0xa8a0,0xa8c8,0xa8d4,0xa8e0,0xa8e8,0xa9c0,0xa9f8,0xaa54,0x8a74,0x8e38,0x95a0] if name=='libupdatercorecommon.so' else
                 [0x8c0,0x8d8] if name=='libupdatertalk.so' else [0x423c,0x41f8] if name=='libcryptfileinputupdaterapi.so' else [0x95e4,0x9630] if name=='libupdatercommon.so' else [0x3a00,0x3afc,0x3bcc])
        for va in targets:
            raw=v.function(va);text,literals,calls=listing(v,va,len(raw));p=out/f'{name}-{va:x}.txt';p.write_text(text)
            fragments.append(dict(source=path,source_sha256=hashlib.sha256(v.raw).hexdigest(),va=hex(va),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),label=v.labels.get(va),disassembly=str(p.relative_to(HERE)),literals=literals,calls=calls,bounds='original symbol/FDE function'))
        windows=[(0xa0bc,8)] if name=='libupdatercorecommon.so' else [(0x2f48,0xec),(0x1928,0xd0)] if name=='libupdaterufp.so' else [(0x956c,8)] if name=='libupdatercommon.so' else []
        for va,n in windows:
            raw=v.read(va,n);text,literals,calls=listing(v,va,n);p=out/f'{name}-window-{va:x}.txt';p.write_text(text)
            fragments.append(dict(source=path,source_sha256=hashlib.sha256(v.raw).hexdigest(),va=hex(va),bytes=n,sha256=hashlib.sha256(raw).hexdigest(),disassembly=str(p.relative_to(HERE)),literals=literals,calls=calls,bounds='explicit bounded instruction window'))
    output=dict(decoder_unique_function_bodies=bodies,selected_fragments=fragments,
                lens_class_contract=dict(field_in_unpacked_header='0x24',field_in_raw_block_with_4_byte_prefix='0x28',mask='0x00ff0000',required_value='0x00a00000',camera_model_word='0x91030080',next_service='0x912503d0',next_request_command=3,next_reply_proven=False),
                scope='Source file pins and original function/window bytes only. A decoder return with unread ciphertext is not complete input acceptance. Lens-class comparison and next IPC request do not establish reply, session, native execution, model-compatible functionality or flashing.')
    (HERE/'stream-contract-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(decoder_function_bodies=len(bodies),selected_fragments=len(fragments),lens_reply_proven=False)))

if __name__=='__main__':main()
