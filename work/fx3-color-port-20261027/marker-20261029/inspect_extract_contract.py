#!/usr/bin/env python3
"""Pin extraction/optional XML contracts, without interpreting shell or mounting data."""
import hashlib,json
from inspect_body_policy import HERE,PATH,PIN,View,listing

def main():
    body=View(PATH,PIN);out=HERE/'extract-contract-fragments';out.mkdir(exist_ok=True);rows=[]
    for address in [0x13100,0x163b8,0x15b80,0x16880,0x17468,0x175c8,0x179e0,0x17c74]:
        raw=body.function(address);text,literals,calls=listing(body,address,len(raw));p=out/f'{address:x}.txt';p.write_text(text)
        rows.append(dict(va=hex(address),label=body.labels[address],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),literals=literals,calls=calls,disassembly=str(p.relative_to(HERE)),bounds='original symbol/FDE function'))
    for address,size in [(0x1235c,0x20),(0x12590,0xf0),(0x13850,0x34)]:
        raw=body.read(address,size);text,literals,calls=listing(body,address,size);p=out/f'window-{address:x}.txt';p.write_text(text)
        rows.append(dict(va=hex(address),bytes=size,sha256=hashlib.sha256(raw).hexdigest(),literals=literals,calls=calls,disassembly=str(p.relative_to(HERE)),bounds='bounded controller window, not whole function'))
    symbol=next(s for s in body.symbols if body.names.get(s.name)=='vtable for Updater::XmlConfigHandler')
    slots=[]
    for rel in body.elf.get_section_by_name('.rela.dyn').iter_relocations():
        if symbol['st_value']+16<=rel['r_offset']<symbol['st_value']+symbol['st_size']:
            s=body.symbols[rel['r_info_sym']]
            slots.append(dict(slot=hex(rel['r_offset']-symbol['st_value']-16),symbol=s.name,label=body.names.get(s.name,s.name),relocation_type=rel['r_info_type'],addend=rel['r_addend']))
    assert next(r for r in slots if r['slot']=='0x20')['label']=='Updater::XmlConfigHandler::LoadUserConfig(Updater::StringHandler const&)'
    ap=HERE.parent/'ap-input-20261029'
    source=next(r for r in json.loads((ap/'additional-source-members.json').read_text()) if r['original_path']=='/lib/libupdatercommon.so')
    current=View(ap/source['output'],source['sha256'])
    inventory=json.loads((HERE.parent/'package-20261028/updater-inventory.json').read_text())
    embedded=next(r for r in inventory['entries'] if r['path']=='/usr/lib/libupdatercommon.so')
    other=View(HERE.parent/'package-20261028'/embedded['output'],embedded['sha256'])
    other_symbols={s.name:s for s in other.symbols if s['st_value']};eq=[]
    for s in current.symbols:
        if s['st_value'] and s['st_size'] and 'StringHandler::' in current.names.get(s.name,''):
            t=other_symbols[s.name];a=current.read(s['st_value'],s['st_size']);b=other.read(t['st_value'],t['st_size'])
            eq.append(dict(symbol=s.name,label=current.names[s.name],current_va=hex(s['st_value']),embedded_va=hex(t['st_value']),bytes=len(a),identical=a==b,sha256=hashlib.sha256(a).hexdigest()))
    assert len(eq)==20 and all(r['identical'] for r in eq)
    original_files=[]
    for name in ['/config/config.xml','/bin/body_common.sh','/bin/startupdate.sh','/bin/us_crc32sum.sh']:
        item=next(r for r in inventory['entries'] if r['path']==name)
        p=HERE.parent/'package-20261028'/item['output'];raw=p.read_bytes();assert len(raw)==item['size'] and hashlib.sha256(raw).hexdigest()==item['sha256']
        original_files.append(dict(path=str(p),bytes=len(raw),sha256=item['sha256']))
    result=dict(body_sha256=PIN,fragments=rows,xml_vtable_va=hex(symbol['st_value']),xml_vtable_slots=slots,
                current_common_sha256=source['sha256'],embedded_common_sha256=embedded['sha256'],string_handler_symbol_comparisons=eq,original_files=original_files,
                scope='Source instruction slices, original relocation targets, hashes and byte comparisons only. Current AP and updater-embedded common libraries differ as whole files, while these 20 exported StringHandler symbol bodies (18 unique addresses) match byte for byte. This is not proof of actual runtime library choice, complete ABI identity, real marker state, XML acceptance, scripts or normal update admission.')
    (HERE/'extract-contract-static-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(fragments=len(rows),xml_slot20='LoadUserConfig',string_symbol_bodies=len(eq),all_equal=True,camera_actions=0)))

if __name__=='__main__':main()
