#!/usr/bin/env python3
"""Read the bounded official update-only SquashFS; no mounts, firmware or USB execution."""
from pathlib import Path,PurePosixPath
from hashlib import sha256
import json,sys,io,re,plistlib,subprocess,urllib.request
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FW=ROOT/'work/sony-firmware-20261024'


def main():
    v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    meta=json.loads((FW/'fx3-7.02-offline-manifest.json').read_bytes())
    original=FW/'fx3-7.02-decrypted.fdat'
    with original.open('rb') as f:assert __import__('hashlib').file_digest(f,'sha256').hexdigest()==meta['decrypted_fdat_sha256']
    with original.open('rb') as f:f.seek(512);region=f.read(1253376)
    assert region[:4]==b'hsqs' and len(region)==1253376
    receipt=json.loads((HERE/'parser-source-receipt.json').read_bytes())
    wheel=ROOT/receipt['wheel'];assert not wheel.is_symlink()
    if not wheel.exists():
        data=urllib.request.urlopen(receipt['url'],timeout=20).read()
        assert sha256(data).hexdigest()==receipt['sha256']
        wheel.parent.mkdir(exist_ok=True);wheel.write_bytes(data)
    assert sha256(wheel.read_bytes()).hexdigest()==receipt['sha256']
    sys.path.insert(0,str(wheel))
    from PySquashfsImage import SquashFsImage
    rows=[];total=0;out=HERE/'updaterfs';out.mkdir(exist_ok=True)
    with SquashFsImage.from_bytes(region) as image:
        for entry in image:
            path=PurePosixPath(entry.path);assert '..' not in path.parts
            row=dict(path=str(path),size=entry.size,mode=entry.filemode)
            if entry.is_symlink:row.update(type='symlink',target=entry.readlink())
            elif entry.is_dir:row.update(type='directory')
            elif entry.is_file:
                assert 0<=entry.size<=8*1024*1024
                data=entry.read_bytes();assert len(data)==entry.size
                total+=len(data);assert total<=32*1024*1024
                dest=out/str(path).lstrip('/');assert dest.resolve().is_relative_to(out.resolve())
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
                row.update(type='file',sha256=sha256(data).hexdigest(),output=str(dest.relative_to(HERE)))
                row['interesting_strings']=[dict(offset=hex(m.start()),value=m.group().decode('ascii'))
                    for m in re.finditer(rb'[\x20-\x7e]{5,}',data)
                    if re.search(rb'RSA|[Ss]ignature|[Vv]erif|[Dd]ecrypt|[Ee]ncrypt|BODYDATA|FDAT|[Pp]ublic[Kk]ey|[Ss]ecure',m.group())]
                if data[:4]==b'\x7fELF':
                    elf=ELFFile(io.BytesIO(data));row['elf_machine']=elf['e_machine']
                    row['relevant_symbols']=[]
                    for section in elf.iter_sections():
                        if isinstance(section,SymbolTableSection):
                            for s in section.iter_symbols():
                                if re.search(r'RSA|[Ss]ign|[Vv]erif|[Dd]ecrypt|[Ee]ncrypt|[Pp]ublic|FDAT|fdat|SHA|MD5',s.name):
                                    row['relevant_symbols'].append(dict(name=s.name,va=hex(s['st_value']),bytes=s['st_size'],section=s['st_shndx']))
            else:row.update(type='special_record_only')
            rows.append(row)
    result=dict(status='PASS_BOUNDED_OFFICIAL_UPDATER_FILESYSTEM_EXTRACTED',source=str(original.relative_to(ROOT)),
                source_sha256=meta['decrypted_fdat_sha256'],filesystem_offset=512,filesystem_bytes=len(region),
                filesystem_sha256=sha256(region).hexdigest(),entries=rows,total_regular_file_bytes=total,
                scope='Offline decompression and static ELF/string inventory only. No symlinks/devices created, no extracted code executed, no updater acceptance or signature validation proved.')
    (HERE/'updater-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'entries',len(rows),'file bytes',total)
    for row in rows:
        if row['type']=='file':print(row['path'],row['size'],row.get('elf_machine',''),len(row['interesting_strings']),len(row.get('relevant_symbols',[])))
    assert sha256(wheel.read_bytes()).hexdigest()==receipt['sha256']
    wheel.unlink() # Only this task's verified 43 KiB downloaded parser wheel; URL/digest retained.


if __name__=='__main__':main()
