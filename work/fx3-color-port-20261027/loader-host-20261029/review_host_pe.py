#!/usr/bin/env python3
"""Static public host-tool interface inventory; neither loading nor executing DLLs."""
import hashlib,json,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
from pe_reader import PE
HERE=Path(__file__).resolve().parent
NAMES=['sncverup_tool.dll','snccore_tool.dll','snccgiw_tool.dll','sonynetworkcamera6_tool.dll','snctoolbox.exe']
def main():
    out=HERE/'host-PE-interfaces.json';assert not out.exists()
    inv=json.loads((HERE/'host-component-review.json').read_text());rows=[]
    for name in NAMES:
        r=next(r for r in inv['files'] if r['name']==name);b=(HERE/r['output']).read_bytes()
        assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];pe=PE(b)
        exports=pe.exports();imports=pe.imports();strings=[]
        for m in re.finditer(rb'[ -~]{7,}',b):
            s=m.group().decode('ascii')
            if re.search(r'firmware|BinaryPack|ProductCode|DATA232|\.svu|\.pkg|\.bin|Decrypt|VersionUp|Verup|VerUp',s,re.I):strings.append(dict(file_offset=m.start(),text=s[:500]))
        rows.append(dict(name=name,bytes=len(b),sha256=r['sha256'],machine=hex(pe.machine),image_base=pe.base,entry_RVA=pe.entry,
            sections=pe.sections,exports=exports,imports=imports,related_ASCII_strings=strings))
    out.write_text(json.dumps(dict(files=rows,scope='Static PE file metadata and strings only; original DLL instructions, entry points, native loaders, network services and devices are not run.'),indent=2)+'\n')
    print(json.dumps([dict(name=r['name'],exports=r['exports'],import_DLLs=[x['DLL'] for x in r['imports']],related_strings=r['related_ASCII_strings'][:30]) for r in rows if r['name']=='sncverup_tool.dll'],ensure_ascii=False))
if __name__=='__main__':main()
