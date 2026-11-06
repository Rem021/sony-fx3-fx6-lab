#!/usr/bin/env python3
"""Pinned bounded windows around two observed marker references in libObj."""
import hashlib,json,sys
from assemble_body_guest import HERE,AP,View
sys.path.insert(0,str(HERE.parent/'entry-20261029'))
from inspect_entry_chain import listing

def main():
    source=json.loads((HERE/'obj-source.json').read_text());view=View(HERE/source['output'],source['sha256']);rows=[]
    for site in [0xecce0,0xee0b8]:
        start=site-64;size=512;raw=view.read(start,size);text,literals,calls=listing(view,start,size)
        assert any(l['text']=='/root/IAMUPDATER' and int(l['site'],16)==site for l in literals)
        output=HERE/'fragments'/f'libObj.so-{start:x}.txt';output.write_text(text)
        rows.append(dict(reference_site=hex(site),range_start=hex(start),bytes=size,sha256=hashlib.sha256(raw).hexdigest(),literals=literals,calls=calls,disassembly=str(output.relative_to(HERE))))
    (HERE/'obj-marker-reference-results.json').write_text(json.dumps(dict(source_sha256=source['sha256'],windows=rows,scope='Two bounded static instruction windows with literal references. There are no matching unwind/symbol function bounds at these sites, so these are not full functions or a whole-program writer audit. No runtime rootfs status or vendor code execution.'),indent=2)+'\n')
    print(json.dumps(dict(windows=len(rows),native_execution=0)))

if __name__=='__main__':main()
