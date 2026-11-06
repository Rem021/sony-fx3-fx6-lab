#!/usr/bin/env python3
"""Extract selected original updater/crypto libraries from the verified read-only ext2 image."""
from pathlib import Path
from hashlib import sha256,file_digest
import sys,json,io,re
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FS=ROOT/'work/sony-firmware-20261024/stage2/extraction'
SELECT=['/lib/libcryptfileinputupdaterapi.so','/lib/libfileinputupdaterapi.so','/lib/libupdatercorecommon.so',
        '/lib/libupdaterufunc.so','/lib/libupdaterufp.so','/lib/libupdatertalk.so','/lib/libupdatermedia.so',
        '/lib/libInfraCrypt.so','/lib/libInfraCryptCore.so','/lib/libCryptoController.so','/lib/libcrypto.so.3']


def main():
    sys.path.insert(0,str(HERE.parent/'binding-20261028'))
    from resource_binding_guest import image
    image() # Existing volume UUID and pinned original CP guard; no original main is run.
    meta=json.loads((FS/'partition-carve-manifest.json').read_bytes())
    pin=next(x['sha256'] for x in meta if x['source_member']=='0700_part_image/dev/nflasha15')
    source=FS/'nflasha15.img'
    with source.open('rb') as f:assert file_digest(f,'sha256').hexdigest()==pin
    sys.path.insert(0,str(FS));from read_filesystems import Ext2
    fs=Ext2(source);entries={e['path']:e for e in fs.walk()};rows=[]
    for name in SELECT:
        e=entries[name];assert e['type']==0x8000
        b=fs.data(e['inode']);assert len(b)==e['size']
        out=HERE/'libraries'/Path(name).name;out.parent.mkdir(exist_ok=True);out.write_bytes(b)
        elf=ELFFile(io.BytesIO(b));symbols=[]
        for sec in elf.iter_sections():
            if isinstance(sec,SymbolTableSection):
                for s in sec.iter_symbols():
                    if s.name:symbols.append(dict(name=s.name,va=hex(s['st_value']),bytes=s['st_size'],section=s['st_shndx'],type=s['st_info']['type']))
        strings=[dict(offset=hex(m.start()),value=m.group().decode()) for m in re.finditer(rb'[\x20-\x7e]{5,}',b)
                 if re.search(rb'RSA|[Ss]ignature|[Vv]erif|[Dd]ecrypt|[Ee]ncrypt|FDAT|BODYDATA|[Pp]ublic[Kk]ey|[Cc]heck[Ss]um|[Ss]ecure',m.group())]
        rows.append(dict(source_path=name,inode=e['inode'],bytes=len(b),sha256=sha256(b).hexdigest(),
                         output=str(out.relative_to(HERE)),symbols=symbols,interesting_strings=strings))
    result=dict(status='PASS_ORIGINAL_VERIFIER_LIBRARIES_EXTRACTED',partition_sha256=pin,libraries=rows,
                scope='Read-only ext2 extraction and static symbol/string inventory. No library loaded or executed on macOS, no camera access.')
    (HERE/'verifier-library-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'libraries',len(rows))
    for x in rows:
        print(x['source_path'],x['bytes'],'symbols',len(x['symbols']),'interesting strings',len(x['interesting_strings']))


if __name__=='__main__':main()
