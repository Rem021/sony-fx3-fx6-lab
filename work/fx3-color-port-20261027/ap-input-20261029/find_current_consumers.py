#!/usr/bin/env python3
"""Read-only consumer discovery in the pinned original FX3 7.02 AP ext2."""
from pathlib import Path
import hashlib,io,json,sys
from elftools.elf.elffile import ELFFile

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
FS=PROJECT/'work/sony-firmware-20261024/stage2/extraction'
TOKENS=[b'GetCryptFileInputModeUpdater',b'GetFileInputModeUpdater',b'GetFileInputProductModeUpdater',b'libcryptfileinputupdaterapi.so',b'libfileinputupdaterapi.so',b'crypter',b'libupdaterufp.so',b'udtr_ufp_init']

def main():
    HERE.mkdir(exist_ok=True)
    meta=json.loads((FS/'partition-carve-manifest.json').read_text())
    pin=next(r['sha256'] for r in meta if r['source_member']=='0700_part_image/dev/nflasha15')
    image=FS/'nflasha15.img'
    with image.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==pin
    sys.path.insert(0,str(FS));from read_filesystems import Ext2
    fs=Ext2(image);inventory=[];hits=[];regular=0;total=0
    for entry in fs.walk():
        if entry['type']!=0x8000:continue
        data=fs.data(entry['inode']);regular+=1;total+=len(data)
        found=[]
        for token in TOKENS:
            offsets=[];pos=0
            while True:
                off=data.find(token,pos)
                if off<0:break
                offsets.append(off);pos=off+len(token)
            if offsets:found.append(dict(token=token.decode(),offsets=offsets))
        if data[:4]!=b'\x7fELF':
            if found:hits.append(dict(path=entry['path'],inode=entry['inode'],bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),hits=found,format='non-ELF'))
            continue
        elf=ELFFile(io.BytesIO(data));dyn=elf.get_section_by_name('.dynamic');sym=elf.get_section_by_name('.dynsym')
        needed=[t.needed for t in dyn.iter_tags() if t.entry.d_tag=='DT_NEEDED'] if dyn else []
        names=[dict(name=s.name,va=hex(s['st_value']),bytes=s['st_size'],section=s['st_shndx']) for s in sym.iter_symbols() if any(t.decode() in s.name for t in TOKENS)] if sym else []
        row=dict(path=entry['path'],inode=entry['inode'],bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),machine=elf['e_machine'],needed=needed)
        inventory.append(row)
        if found or names:hits.append(dict(**row,hits=found,symbols=names,format='ELF'))
    result=dict(partition=str(image),partition_sha256=pin,regular_files_read=regular,bytes_read=total,elf_count=len(inventory),tokens=[t.decode() for t in TOKENS],hits=hits,elf_inventory=inventory,
                scope='Exact marker, DT_NEEDED and dynamic-symbol discovery in all regular files of the original AP image. No mounting, vendor execution or device access. Absence of exact symbols/strings does not rule out dynamic composition, other partitions or runtime code.')
    (HERE/'current-consumer-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'regular':regular,'bytes':total,'elf':len(inventory),'hits':[{'path':r['path'],'symbols':r.get('symbols',[])} for r in hits]}))

if __name__=='__main__':main()
