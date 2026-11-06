#!/usr/bin/env python3
"""Validate ZIP/MD5/tar and extract regular donor members, never execute them."""
import hashlib,io,json,re,stat,tarfile,zipfile
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    target=HERE/'package-unpack.json';assert not target.exists()
    receipt=json.loads((HERE/'download-receipt.json').read_text());p=HERE/receipt['output']
    raw=p.read_bytes();assert len(raw)==receipt['bytes'] and sha(raw)==receipt['sha256']
    selected={};ziprows=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert len(z.infolist())<100 and sum(e.file_size for e in z.infolist())<500*1024*1024
        assert z.testzip() is None
        for e in z.infolist():
            path=PurePosixPath(e.filename);assert not path.is_absolute() and '..' not in path.parts
            assert not stat.S_ISLNK(e.external_attr>>16)
            ziprows.append(dict(path=e.filename,bytes=e.file_size,compressed_bytes=e.compress_size,CRC32=hex(e.CRC),CRC_checked=True))
            if not e.is_dir() and path.suffix.lower() in ['.bin','.md5','.txt']:
                b=z.read(e);out=HERE/'originals'/path.name;assert not out.exists();out.write_bytes(b)
                selected[path.suffix.lower()]=dict(path=str(out.relative_to(HERE)),bytes=len(b),sha256=sha(b))
    assert set(selected)=={'.bin','.md5','.txt'}
    firmware=(HERE/selected['.bin']['path']).read_bytes();md5=(HERE/selected['.md5']['path']).read_text()
    expected=re.findall(r'(?i)\b[0-9a-f]{32}\b',md5);assert len(expected)==1 and hashlib.md5(firmware).hexdigest()==expected[0].lower()
    dest=HERE/'outer-members';dest.mkdir(exist_ok=True);members=[];xmls=[]
    with tarfile.open(fileobj=io.BytesIO(firmware),mode='r:') as tar:
        rows=tar.getmembers();assert len(rows)<100 and sum(r.size for r in rows)<len(firmware)
        for row in rows:
            path=PurePosixPath(row.name);assert not path.is_absolute() and '..' not in path.parts
            assert row.isdir() or row.isfile(),row.name
            item=dict(path=row.name,bytes=row.size,type='directory' if row.isdir() else 'regular',header_offset=row.offset,data_offset=row.offset_data)
            if row.isfile():
                stream=tar.extractfile(row);assert stream is not None;b=stream.read(row.size+1);assert len(b)==row.size
                output=dest/path;output.parent.mkdir(parents=True,exist_ok=True);assert not output.exists();output.write_bytes(b)
                item.update(output=str(output.relative_to(HERE)),sha256=sha(b),first64_hex=b[:64].hex())
                if path.suffix.lower()=='.xml':xmls.append(dict(path=row.name,text=b.decode('utf-8')))
            members.append(item)
    out=dict(download_sha256=receipt['sha256'],zip_entries=ziprows,selected_originals=selected,
        firmware_md5_expected=expected[0].lower(),firmware_md5_matches=True,outer_format='uncompressed tar',outer_members=members,XML=xmls,
        scope='ZIP CRC and same-package MD5 plus regular tar-member extraction only. No decrypted inner format, executable, full ISP, foreign-model compatibility or flashing is implied.')
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(zip_entries=len(ziprows),firmware_bytes=len(firmware),firmware_sha256=sha(firmware),MD5_valid=True,outer_members=members,XML=xmls)))
if __name__=='__main__':main()
