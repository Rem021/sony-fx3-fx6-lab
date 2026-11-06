#!/usr/bin/env python3
"""Original preinstalled updater policy slices, without scripts or native I/O."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'entry-20261029'))
from inspect_entry_chain import View,listing

PATH=HERE.parent/'package-20261028/updaterfs/bodylib/libupdaterbody.so'
PIN='6582eba530025d17fab81420050433cd998714c922aa4c16fd4d5cdc5a378ee9'

def main():
    view=View(PATH,PIN);out=HERE/'body-policy-fragments';out.mkdir(exist_ok=True);rows=[]
    targets=[0x13138,0x1444c,0x14234,0x1371c,0x194dc,0x173e8,0x17a3c,0x177cc,0x187a4,0x19194,0x19430,0x19470,0x19bdc,0x13c8c]
    for va in targets:
        raw=view.function(va);text,literals,calls=listing(view,va,len(raw));dest=out/f'{va:x}.txt';dest.write_text(text)
        rows.append(dict(va=hex(va),label=view.labels[va],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),literals=literals,calls=calls,disassembly=str(dest.relative_to(HERE))))
    (HERE/'body-policy-static-results.json').write_text(json.dumps(dict(source=str(PATH),source_sha256=PIN,functions=rows,scope='Original symbol/unwind bounded functions and read-only literal references only. Config tags and shell command generation are not permission to run scripts; no write/mount/backup/shell/device or native target loading is executed.'),indent=2)+'\n')
    print(json.dumps(dict(functions=len(rows),source_sha256=PIN,native_execution=0)))

if __name__=='__main__':main()
