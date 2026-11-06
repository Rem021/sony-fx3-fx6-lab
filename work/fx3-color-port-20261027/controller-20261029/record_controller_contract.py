#!/usr/bin/env python3
"""Pin controller, CLI and conditional verifyFile instruction contracts."""
import hashlib,json,sys
from pathlib import Path
from controller_guest import HERE,sources
sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View,sources as ap_sources
sys.path.insert(0,str(HERE.parent/'entry-20261029'))
from inspect_entry_chain import listing

def main():
    views=sources();cases=json.loads((HERE/'controller-guest-results.json').read_text())['cases']
    names={name for r in cases for name in r['original_function_entries']};entered=[]
    for base,v in views:
        seen=set()
        for s in v.symbols:
            name=v.names.get(s.name,s.name);va=s['st_value']
            if name not in names or not va or va in seen:continue
            assert s['st_info']['type']=='STT_FUNC';raw=v.function(va);seen.add(va)
            entered.append(dict(source=str(v.path),source_sha256=hashlib.sha256(v.raw).hexdigest(),label=name,va=hex(va),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    selected=[];out=HERE/'contract-fragments';out.mkdir(exist_ok=True)
    def save(v,va,count=None,label=None):
        raw=v.function(va) if count is None else v.read(va,count)
        text,literals,calls=listing(v,va,len(raw));p=out/f'{v.path.name}-{va:x}.txt';p.write_text(text)
        selected.append(dict(source=str(v.path),source_sha256=hashlib.sha256(v.raw).hexdigest(),va=hex(va),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),label=label or v.labels.get(va),bounds='original symbol/FDE function' if count is None else 'explicit instruction window',disassembly=str(p.relative_to(HERE)),literals=literals,calls=calls))
    body=views[0][1]
    for va in [0x121d8,0x122a4,0x132e8,0x1335c,0x1371c,0x15d64,0x16880,0x17224,0x172c4,0x172d4,0x17320,0x19430,0x194dc]:save(body,va)
    source=next(r for r in ap_sources() if Path(r['path']).name=='crypter.elf');cli=View(source['path'],source['sha256'])
    save(cli,0x400bc0)
    for va,n in [(0x400a98,20),(0x400f68,20),(0x400fb8,64),(0x401028,56)]:save(cli,va,n)
    s=next(r for r in ap_sources() if Path(r['path']).name=='libcryptfileinputupdaterapi.so');crypt=View(s['path'],s['sha256'])
    for va in [0x3fcc,0x3ec8]:save(crypt,va)
    conditional=dict(initialize_parameter_store=dict(source_sha256=s['sha256'],site='0x40c4',instruction='str w23, [x19, #0x48]',condition='normal completion of original Initialize; complete initialization is not executed by the CLI guest'),
                     verify_file_branch=dict(source_sha256=s['sha256'],entry='0x3ec8',field_offset='0x48',crc_branch_only_for_value=1,other_values_return_true_in_this_function=True,scope='This skips only this verifyFile function CRC branch. Header/block checks, actual file reads, full manager startup, external admission, cryptographic signature and real execution are not thereby proven or removed.'))
    result=dict(original_controller_unique_function_bodies=entered,selected_fragments=selected,conditional_input_mode_contract=conditional,
                scope='Original file-backed code hashes and selected disassembly. CLI mode arguments and controller flow come from separate synthetic executions, not one complete external encrypted/signed update. The initializer and verifyFile contract is static and conditional, not a claimed successful real loader/admission.')
    (HERE/'controller-contract-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(controller_function_bodies=len(entered),selected_fragments=len(selected),mode_contract='conditional only')))

if __name__=='__main__':main()
