#!/usr/bin/env python3
"""Recover the current AP XML library from pinned ext2 with a read-only parser."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
PROJECT=TASK.parents[1]
FS=PROJECT/'work/sony-firmware-20261024/stage2/extraction'
sys.path.insert(0,str(FS))
from read_filesystems import Ext2
sys.path.insert(0,str(TASK/'entry-20261029'))
from inspect_entry_chain import View,listing
IMAGE=FS/'nflasha15.img'
IMAGE_PIN='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'

def main():
    with IMAGE.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==IMAGE_PIN
    fs=Ext2(IMAGE);entry=next(r for r in fs.walk() if r['path']=='/lib/libul_xml.so')
    assert entry['type']==0x8000
    raw=fs.data(entry['inode']);assert len(raw)==entry['size']
    out=HERE/'original-members';out.mkdir(exist_ok=True);p=out/'libul_xml.so';assert not p.exists();p.write_bytes(raw)
    pin=hashlib.sha256(raw).hexdigest();v=View(p,pin)
    symbols=[]
    for s in v.symbols:
        if s['st_value']:symbols.append(dict(symbol=s.name,label=v.names.get(s.name,s.name),va=hex(s['st_value']),bytes=s['st_size']))
    imports=[dict(symbol=s.name,label=v.names.get(s.name,s.name)) for s in v.symbols if s['st_shndx']=='SHN_UNDEF']
    (HERE/'xml-source.json').write_text(json.dumps(dict(image=str(IMAGE),image_sha256=IMAGE_PIN,original_path=entry['path'],inode=entry['inode'],bytes=len(raw),sha256=pin,output=str(p.relative_to(HERE)),symbols=symbols,imports=imports,scope='Read-only ext2 member extraction and ELF metadata, no mount/native execution/device operation.'),indent=2)+'\n')
    targets=['Updater::Xml::DomDocument::DomDocument()','Updater::Xml::DomDocument::loadFile(char const*, Updater::Xml::TiXmlEncoding)',
             'Updater::Xml::TiXmlDocument::Parse(char const*, Updater::Xml::TiXmlParsingData*, Updater::Xml::TiXmlEncoding)']
    dest=HERE/'xml-fragments';dest.mkdir(exist_ok=True);rows=[]
    for label in targets:
        match=next((s for s in symbols if s['label']==label),None)
        if match is None:continue
        va=int(match['va'],16);raw=v.function(va);text,literals,calls=listing(v,va,len(raw));p=dest/f'{va:x}.txt';p.write_text(text)
        rows.append(dict(**match,sha256=hashlib.sha256(raw).hexdigest(),literals=literals,calls=calls,disassembly=str(p.relative_to(HERE))))
    (HERE/'xml-static-results.json').write_text(json.dumps(dict(source_sha256=pin,functions=rows,scope='Original symbol/FDE bounded functions, no XML input or loading executed.'),indent=2)+'\n')
    print(json.dumps(dict(bytes=len(v.raw),sha256=pin,defined_symbols=len(symbols),imports=len(imports),static_functions=len(rows))))

if __name__=='__main__':main()
