#!/usr/bin/env python3
"""Source hashes for functions actually entered; selected full disassembly only."""
import hashlib,json
from xml_guest import sources,HERE
from inspect_xml_source import listing

def main():
    views=sources();names=set();case_counts={}
    for name in ['xml-guest-results.json','dispatch-guest-results.json','post-config-guest-results.json']:
        rows=json.loads((HERE/name).read_text())['cases'];case_counts[name]=len(rows)
        for row in rows:names.update(row['original_function_entries'])
    functions=[]
    for base,view in views:
        seen=set()
        for symbol in view.symbols:
            label=view.names.get(symbol.name,symbol.name);va=symbol['st_value']
            if label not in names or not va or va in seen:continue
            assert symbol['st_info']['type']=='STT_FUNC';raw=view.function(va);seen.add(va)
            functions.append(dict(source=str(view.path),source_sha256=hashlib.sha256(view.raw).hexdigest(),va=hex(va),runtime_va=hex(base+va),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),label=label))
    fragments=[];out=HERE/'contract-fragments';out.mkdir(exist_ok=True)
    for base,view in views:
        targets=([0x1371c,0x17468,0x174e8,0x175c8,0x176c0,0x177cc,0x179e0,0x17a3c,0x17c74,0x17c94,0x1847c,0x184bc,0x185cc,0x187a4,0x18e28] if base==0x10000000 else
                 [0x8c90,0x8dd0,0x9078,0xa64c,0xa6b0,0xbaa0,0xc4f4] if base==0x30000000 else [])
        for va in targets:
            raw=view.function(va);text,literals,calls=listing(view,va,len(raw));p=out/f'{base:x}-{va:x}.txt';p.write_text(text)
            fragments.append(dict(source=str(view.path),source_sha256=hashlib.sha256(view.raw).hexdigest(),va=hex(va),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),label=view.labels.get(va),disassembly=str(p.relative_to(HERE)),literals=literals,calls=calls,bounds='original symbol/FDE function'))
    body=views[0][1];raw=body.read(0x1b4c8,16);text,literals,calls=listing(body,0x1b4c8,16);p=out/'stat-wrapper-window.txt';p.write_text(text)
    fragments.append(dict(source=str(body.path),source_sha256=hashlib.sha256(body.raw).hexdigest(),va='0x1b4c8',bytes=16,sha256=hashlib.sha256(raw).hexdigest(),disassembly=str(p.relative_to(HERE)),literals=literals,calls=calls,bounds='exact 16-byte stat wrapper window, not symbol/FDE identity'))
    result=dict(case_counts=case_counts,unique_function_bodies_entered=functions,selected_fragments=fragments,
                scope='Original file-backed bytes, source pins, symbol/FDE function bounds, recorded guest entry names and selected disassembly only. This records which sources supplied interpreted instructions; it does not attest real native loader selection or camera execution.')
    (HERE/'xml-contract-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=sum(case_counts.values()),unique_function_bodies=len(functions),selected_fragments=len(fragments))))

if __name__=='__main__':main()
